"""API Endpoints for Radiotherapy Treatment Continuity & Triage (M7).

Implements:
- Linear Accelerator (LINAC) machine status and downtime tracking
- Radiotherapy course intake and monitoring
- Google OR-Tools CP-SAT constrained schedule solving with fairness & contiguity bounds
- Clinician schedule confirmation with transparent delay ledger creation
- Patient & caregiver plain-language delay notices with marginal harm tracking
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event
from vigil_api.auth import get_current_user, require_roles
from vigil_api.consent import has_active_consent, verify_patient_consent
from vigil_api.database import get_db
from vigil_api.models.v2 import (
    CourseStatus,
    DelayLedgerEntry,
    LinacMachine,
    MachineStatus,
    RadiotherapyCourse,
    User,
    UserRole,
)
from vigil_api.schemas.v2 import (
    DelayLedgerEntryResponse,
    LinacMachineResponse,
    LinacMachineStatusUpdate,
    PatientDelayNoticeResponse,
    RadiotherapyCourseCreate,
    RadiotherapyCourseResponse,
    ScheduleAssignment,
    ScheduleConfirmRequest,
    ScheduleConfirmResponse,
    ScheduleSolveRequest,
    ScheduleSolveResponse,
)
from vigil_ml.continuity import ContinuityHarmModel
from vigil_ml.scheduler import MachineConfig, PatientCourse, RadiotherapyScheduler

router = APIRouter()
_HARM_MODEL = ContinuityHarmModel()


# ==============================================================================
# 1. LINAC Machines
# ==============================================================================


@router.get("/machines", response_model=List[LinacMachineResponse])
def list_linac_machines(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN, UserRole.QUALITY_LEAD
        )
    ),
):
    """Lists all linear accelerators with their operational and downtime status."""
    machines = db.execute(select(LinacMachine).order_by(LinacMachine.machine_name)).scalars().all()
    return [
        LinacMachineResponse(
            id=m.id,
            facility_id=m.facility_id,
            machine_name=m.machine_name,
            daily_slot_capacity=m.daily_slot_capacity,
            status=m.status,
            downtime_started_at=m.downtime_started_at,
            expected_return_at=m.expected_return_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
            synthetic=True,
        )
        for m in machines
    ]


@router.post("/machines/{id}/status", response_model=LinacMachineResponse)
def update_machine_status(
    id: str,
    payload: LinacMachineStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Updates operational status of a LINAC machine (e.g. down, maintenance, operational)."""
    machine = db.execute(select(LinacMachine).where(LinacMachine.id == id)).scalar_one_or_none()
    if machine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LINAC machine '{id}' not found.",
        )

    now = datetime.now(timezone.utc)
    old_status = machine.status
    machine.status = payload.status
    if payload.status in (MachineStatus.DOWN.value, MachineStatus.MAINTENANCE.value):
        if not machine.downtime_started_at:
            machine.downtime_started_at = now
        machine.expected_return_at = payload.expected_return_at
    else:
        machine.downtime_started_at = None
        machine.expected_return_at = None

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="continuity.machine_status_updated",
        resource_type="LinacMachine",
        resource_id=machine.id,
        details={
            "machine_name": machine.machine_name,
            "old_status": old_status,
            "new_status": machine.status,
            "reason": payload.reason,
            "expected_return_at": payload.expected_return_at.isoformat()
            if payload.expected_return_at
            else None,
        },
    )
    db.commit()
    db.refresh(machine)

    return LinacMachineResponse(
        id=machine.id,
        facility_id=machine.facility_id,
        machine_name=machine.machine_name,
        daily_slot_capacity=machine.daily_slot_capacity,
        status=machine.status,
        downtime_started_at=machine.downtime_started_at,
        expected_return_at=machine.expected_return_at,
        created_at=machine.created_at,
        updated_at=machine.updated_at,
        synthetic=True,
    )


# ==============================================================================
# 2. Radiotherapy Courses
# ==============================================================================


@router.get("/courses", response_model=List[RadiotherapyCourseResponse])
def list_radiotherapy_courses(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    course_status: Optional[str] = Query(
        None, description="Filter by status (pending, in_progress, completed)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN, UserRole.QUALITY_LEAD
        )
    ),
):
    """Lists radiotherapy courses with current delay days and calculated excess harm."""
    stmt = select(RadiotherapyCourse)
    if patient_id:
        stmt = stmt.where(RadiotherapyCourse.patient_id == patient_id)
    if course_status:
        stmt = stmt.where(RadiotherapyCourse.status == course_status)
    stmt = stmt.order_by(RadiotherapyCourse.prescribed_start_date)

    courses = db.execute(stmt).scalars().all()
    # Every read of patient data requires active consent (MASTER_PLAN section 6.0): drop the rest
    consent_cache: dict[str, bool] = {}
    courses = [
        c
        for c in courses
        if consent_cache.setdefault(
            c.patient_id, has_active_consent(c.patient_id, db, current_user)
        )
    ]
    now = datetime.now(timezone.utc)

    results = []
    for c in courses:
        # Calculate current delay days
        ref_date = c.scheduled_start_date or now
        prescribed_dt = (
            c.prescribed_start_date
            if c.prescribed_start_date.tzinfo
            else c.prescribed_start_date.replace(tzinfo=timezone.utc)
        )
        ref_dt = ref_date if ref_date.tzinfo else ref_date.replace(tzinfo=timezone.utc)
        delay_days = max(0, (ref_dt.date() - prescribed_dt.date()).days)

        try:
            excess_harm = _HARM_MODEL.compute_harm(c.clinical_context, delay_days).expected_harm
        except (ValueError, KeyError):
            excess_harm = 0.0

        results.append(
            RadiotherapyCourseResponse(
                id=c.id,
                patient_id=c.patient_id,
                assigned_machine_id=c.assigned_machine_id,
                clinical_context=c.clinical_context,
                total_fractions=c.total_fractions,
                fractions_delivered=c.fractions_delivered,
                prescribed_start_date=c.prescribed_start_date,
                scheduled_start_date=c.scheduled_start_date,
                actual_start_date=c.actual_start_date,
                urgency_tier=c.urgency_tier,
                status=c.status,
                baseline_subgroup=c.baseline_subgroup,
                current_delay_days=delay_days,
                expected_excess_harm=round(excess_harm, 5),
                created_at=c.created_at,
                updated_at=c.updated_at,
                synthetic=True,
            )
        )
    return results


@router.post(
    "/courses", response_model=RadiotherapyCourseResponse, status_code=status.HTTP_201_CREATED
)
def create_radiotherapy_course(
    payload: RadiotherapyCourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Enrolls a patient into a prescribed radiotherapy treatment course (M7)."""
    patient = verify_patient_consent(patient_id=payload.patient_id, db=db, user=current_user)

    course = RadiotherapyCourse(
        patient_id=patient.id,
        assigned_machine_id=payload.assigned_machine_id,
        clinical_context=payload.clinical_context,
        total_fractions=payload.total_fractions,
        fractions_delivered=0,
        prescribed_start_date=payload.prescribed_start_date,
        scheduled_start_date=payload.prescribed_start_date,
        urgency_tier=payload.urgency_tier,
        status=CourseStatus.PENDING.value,
        baseline_subgroup=payload.baseline_subgroup,
    )
    db.add(course)
    db.flush()

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="continuity.course_created",
        resource_type="RadiotherapyCourse",
        resource_id=course.id,
        details={
            "patient_id": patient.id,
            "clinical_context": payload.clinical_context,
            "total_fractions": payload.total_fractions,
            "prescribed_start_date": payload.prescribed_start_date.isoformat(),
            "urgency_tier": payload.urgency_tier,
        },
    )
    db.commit()
    db.refresh(course)

    return RadiotherapyCourseResponse(
        id=course.id,
        patient_id=course.patient_id,
        assigned_machine_id=course.assigned_machine_id,
        clinical_context=course.clinical_context,
        total_fractions=course.total_fractions,
        fractions_delivered=0,
        prescribed_start_date=course.prescribed_start_date,
        scheduled_start_date=course.scheduled_start_date,
        actual_start_date=None,
        urgency_tier=course.urgency_tier,
        status=course.status,
        baseline_subgroup=course.baseline_subgroup,
        current_delay_days=0,
        expected_excess_harm=0.0,
        created_at=course.created_at,
        updated_at=course.updated_at,
        synthetic=True,
    )


# ==============================================================================
# 3. CP-SAT Schedule Solver & Clinician Confirmation
# ==============================================================================


@router.post("/schedule/solve", response_model=ScheduleSolveResponse)
def solve_radiotherapy_schedule(
    payload: ScheduleSolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CLINICIAN, UserRole.ADMIN, UserRole.QUALITY_LEAD)
    ),
):
    """Solves the multi-machine radiotherapy scheduling problem via Google OR-Tools CP-SAT.

    Enforces:
    - Hard machine slot capacity limits per day
    - Machine maintenance and breakdown downtime
    - Course contiguity (fractions delivered on consecutive days)
    - Clinical urgency ceilings (emergency ≤ 3d, urgent ≤ 7d)
    - Algorithmic fairness: bounded delay disparity across subgroups (≤ disparity_bound)
    - No-starvation: maximum waiting time bounded by max_wait_days
    """
    now = datetime.now(timezone.utc)

    # 1. Load machines
    db_machines = (
        db.execute(select(LinacMachine).order_by(LinacMachine.machine_name)).scalars().all()
    )
    if not db_machines:
        # Auto-seed standard Nigerian tertiary center machines if none exist
        m1 = LinacMachine(
            machine_name="LINAC-01 (Elekta Synergy)",
            daily_slot_capacity=16,
            status=MachineStatus.OPERATIONAL.value,
        )
        m2 = LinacMachine(
            machine_name="LINAC-02 (Varian Clinac)",
            daily_slot_capacity=16,
            status=MachineStatus.OPERATIONAL.value,
        )
        db.add_all([m1, m2])
        db.commit()
        db_machines = [m1, m2]

    machine_configs: List[MachineConfig] = []
    for m in db_machines:
        down_days: List[int] = []
        if m.status in (MachineStatus.DOWN.value, MachineStatus.MAINTENANCE.value):
            # Calculate offline days within schedule horizon
            if m.expected_return_at:
                ret_dt = (
                    m.expected_return_at
                    if m.expected_return_at.tzinfo
                    else m.expected_return_at.replace(tzinfo=timezone.utc)
                )
                repair_days = min(payload.horizon_days, max(1, (ret_dt.date() - now.date()).days))
                down_days = list(range(repair_days))
            else:
                down_days = list(range(min(payload.horizon_days, 7)))  # default 7 days downtime
        machine_configs.append(
            MachineConfig(
                machine_id=m.id,
                name=m.machine_name,
                daily_capacity=m.daily_slot_capacity,
                status="down" if down_days else "active",
                down_days=down_days,
            )
        )

    # 2. Load active courses
    courses = (
        db.execute(
            select(RadiotherapyCourse)
            .where(
                RadiotherapyCourse.status.in_(
                    [CourseStatus.PENDING.value, CourseStatus.IN_PROGRESS.value]
                )
            )
            .order_by(RadiotherapyCourse.prescribed_start_date)
        )
        .scalars()
        .all()
    )

    patient_courses: List[PatientCourse] = []
    course_map: dict[str, RadiotherapyCourse] = {}
    for c in courses:
        course_map[c.patient_id] = c
        prescribed_dt = (
            c.prescribed_start_date
            if c.prescribed_start_date.tzinfo
            else c.prescribed_start_date.replace(tzinfo=timezone.utc)
        )
        elapsed_days = max(0, (now.date() - prescribed_dt.date()).days)

        urgency_bound = None
        if c.urgency_tier == "emergency":
            urgency_bound = 3
        elif c.urgency_tier == "urgent":
            urgency_bound = 7

        patient_courses.append(
            PatientCourse(
                patient_id=c.patient_id,
                clinical_context=c.clinical_context,
                fractions_total=c.total_fractions,
                fractions_completed=c.fractions_delivered,
                elapsed_delay_days=elapsed_days,
                current_machine_id=c.assigned_machine_id,
                subgroup=c.baseline_subgroup or "general",
                max_wait_days=payload.max_wait_days,
                urgency_bound_days=urgency_bound,
            )
        )

    # 3. Run CP-SAT Scheduler
    scheduler = RadiotherapyScheduler(
        harm_model=_HARM_MODEL,
        switch_penalty=payload.stability_penalty,
        max_fairness_disparity_days=int(payload.fairness_disparity_bound),
    )
    result = scheduler.solve(
        machines=machine_configs,
        patients=patient_courses,
        horizon_days=payload.horizon_days,
    )

    # 4. Map allocations to assignments
    assignments: List[ScheduleAssignment] = []
    unassigned: List[str] = []
    delays: List[int] = []

    # Map allocations per patient to find their machine assignment
    patient_assigned_machine: dict[str, str] = {}
    for alloc in result.allocations:
        if alloc.patient_id not in patient_assigned_machine:
            patient_assigned_machine[alloc.patient_id] = alloc.machine_id

    for pc in patient_courses:
        start_day = result.patient_start_days.get(pc.patient_id)
        if start_day is None:
            unassigned.append(pc.patient_id)
            continue

        assigned_machine_id = patient_assigned_machine.get(
            pc.patient_id, machine_configs[0].machine_id
        )
        sched_date = now + timedelta(days=start_day)
        total_delay = pc.elapsed_delay_days + start_day
        delays.append(total_delay)

        try:
            harm = _HARM_MODEL.compute_harm(pc.clinical_context, total_delay).expected_harm
        except (ValueError, KeyError):
            harm = 0.0
        explanation = result.marginal_explanations.get(
            pc.patient_id, f"Scheduled at day {start_day} with harm {harm:.4f}"
        )

        c = course_map[pc.patient_id]
        is_moved = False
        if c.scheduled_start_date:
            cur_sched_dt = (
                c.scheduled_start_date
                if c.scheduled_start_date.tzinfo
                else c.scheduled_start_date.replace(tzinfo=timezone.utc)
            )
            if cur_sched_dt.date() != sched_date.date():
                is_moved = True

        assignments.append(
            ScheduleAssignment(
                patient_id=pc.patient_id,
                course_id=c.id,
                machine_id=assigned_machine_id,
                start_day=start_day,
                scheduled_date=sched_date,
                fractions=pc.fractions_total - pc.fractions_completed,
                context=pc.clinical_context,
                delay_days=total_delay,
                marginal_harm=round(harm, 5),
                explanation=explanation,
                is_moved=is_moved,
            )
        )

    mean_delay = float(sum(delays) / len(delays)) if delays else 0.0
    max_delay = max(delays) if delays else 0

    return ScheduleSolveResponse(
        status=result.status,
        solver_time_seconds=round(result.solver_wall_time_seconds, 4),
        total_excess_harm=round(result.total_expected_harm, 5),
        mean_delay_days=round(mean_delay, 2),
        max_delay_days=max_delay,
        fairness_disparity=round(result.subgroup_disparity_days, 2),
        assignments=assignments,
        unassigned_patient_ids=unassigned,
        synthetic=True,
    )


@router.post("/schedule/confirm", response_model=ScheduleConfirmResponse)
def confirm_radiotherapy_schedule(
    payload: ScheduleConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Clinician-confirmed schedule re-allocation.

    Enforces:
    - Clinician oversight and authentication
    - Writes immutable DelayLedgerEntry records for moved/delayed treatments
    - Updates scheduled start date and assigned machine on the course
    - Records hash-chained audit event continuity.schedule_confirmed
    """
    now = datetime.now(timezone.utc)

    # Validate every assignment BEFORE writing anything (atomic): the client may only choose
    # course, machine and date; patient identity, delay and harm are derived on the server.
    seen_courses: set[str] = set()
    validated = []
    for a in payload.assignments:
        if a.course_id in seen_courses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate assignment for course '{a.course_id}'.",
            )
        seen_courses.add(a.course_id)

        course = db.execute(
            select(RadiotherapyCourse).where(RadiotherapyCourse.id == a.course_id)
        ).scalar_one_or_none()
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course '{a.course_id}' not found.",
            )
        if a.patient_id != course.patient_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Assignment patient does not match course '{a.course_id}'.",
            )
        verify_patient_consent(patient_id=course.patient_id, db=db, user=current_user)
        machine = db.execute(
            select(LinacMachine).where(LinacMachine.id == a.machine_id)
        ).scalar_one_or_none()
        if machine is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Machine '{a.machine_id}' not found.",
            )
        prescribed = (
            course.prescribed_start_date
            if course.prescribed_start_date.tzinfo
            else course.prescribed_start_date.replace(tzinfo=timezone.utc)
        )
        sched = (
            a.scheduled_date
            if a.scheduled_date.tzinfo
            else a.scheduled_date.replace(tzinfo=timezone.utc)
        )
        delay_days = max(0, (sched.date() - prescribed.date()).days)
        try:
            harm = _HARM_MODEL.compute_harm(course.clinical_context, delay_days).expected_harm
        except (ValueError, KeyError):
            harm = 0.0
        validated.append((a, course, delay_days, harm))

    entries_created = 0
    for a, course, delay_days, harm in validated:
        prev_date = course.scheduled_start_date
        course.scheduled_start_date = a.scheduled_date
        course.assigned_machine_id = a.machine_id

        ledger_entry = DelayLedgerEntry(
            patient_id=course.patient_id,
            course_id=course.id,
            delay_days=delay_days,
            reason=payload.reason or "Clinician confirmed schedule optimization",
            marginal_harm=round(harm, 5),
            moved_from_date=prev_date,
            moved_to_date=a.scheduled_date,
            clinician_overridden=False,
            recorded_by=current_user.username,
        )
        db.add(ledger_entry)
        entries_created += 1

    audit_ev = record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="continuity.schedule_confirmed",
        resource_type="RadiotherapySchedule",
        resource_id="current_schedule",
        details={
            "assignments_count": len(payload.assignments),
            "ledger_entries_created": entries_created,
            "clinician_reason": payload.reason,
            "confirmed_at": now.isoformat(),
        },
    )
    db.commit()

    return ScheduleConfirmResponse(
        confirmed=True,
        ledger_entries_created=entries_created,
        audit_event_id=audit_ev.id,
        message=f"Schedule successfully confirmed. {entries_created} delay ledger entries persisted.",
        synthetic=True,
    )


# ==============================================================================
# 4. Delay Ledger & Companion Patient Notices
# ==============================================================================


@router.get("/ledger", response_model=List[DelayLedgerEntryResponse])
def get_delay_ledger(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN, UserRole.QUALITY_LEAD
        )
    ),
):
    """Retrieves immutable delay ledger entries tracking delay days, moves, and reasons (M7)."""
    stmt = select(DelayLedgerEntry)
    if patient_id:
        stmt = stmt.where(DelayLedgerEntry.patient_id == patient_id)
    if course_id:
        stmt = stmt.where(DelayLedgerEntry.course_id == course_id)
    stmt = stmt.order_by(desc(DelayLedgerEntry.created_at))

    entries = db.execute(stmt).scalars().all()
    consent_cache: dict[str, bool] = {}
    entries = [
        e
        for e in entries
        if consent_cache.setdefault(
            e.patient_id, has_active_consent(e.patient_id, db, current_user)
        )
    ]
    return [
        DelayLedgerEntryResponse(
            id=e.id,
            patient_id=e.patient_id,
            course_id=e.course_id,
            delay_days=e.delay_days,
            reason=e.reason,
            marginal_harm=e.marginal_harm,
            moved_from_date=e.moved_from_date,
            moved_to_date=e.moved_to_date,
            clinician_overridden=e.clinician_overridden,
            recorded_by=e.recorded_by,
            created_at=e.created_at,
            synthetic=True,
        )
        for e in entries
    ]


@router.get("/patients/{id}/delay-notice", response_model=PatientDelayNoticeResponse)
def get_patient_delay_notice(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates an honest, plain-language treatment delay notice for the patient or family caregiver (M7/M8)."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)

    # Find patient's primary active course
    course = db.execute(
        select(RadiotherapyCourse)
        .where(
            RadiotherapyCourse.patient_id == patient.id,
            RadiotherapyCourse.status.in_(
                [CourseStatus.PENDING.value, CourseStatus.IN_PROGRESS.value]
            ),
        )
        .order_by(RadiotherapyCourse.prescribed_start_date)
    ).scalar_one_or_none()

    if not course:
        return PatientDelayNoticeResponse(
            patient_id=patient.id,
            has_active_treatment=False,
            course_id=None,
            clinical_context=None,
            total_delay_days=0,
            machine_name=None,
            machine_status=None,
            expected_start_date=None,
            plain_language_notice="You currently have no active or pending radiotherapy treatment courses scheduled. Please consult your oncology team for further care planning.",
            delay_history=[],
            synthetic=True,
        )

    # Fetch delay ledger history
    ledger_entries = (
        db.execute(
            select(DelayLedgerEntry)
            .where(DelayLedgerEntry.course_id == course.id)
            .order_by(desc(DelayLedgerEntry.created_at))
        )
        .scalars()
        .all()
    )

    now = datetime.now(timezone.utc)
    prescribed_dt = (
        course.prescribed_start_date
        if course.prescribed_start_date.tzinfo
        else course.prescribed_start_date.replace(tzinfo=timezone.utc)
    )
    target_date = course.scheduled_start_date or now
    target_dt = target_date if target_date.tzinfo else target_date.replace(tzinfo=timezone.utc)
    total_delay = max(0, (target_dt.date() - prescribed_dt.date()).days)

    machine_name = None
    machine_status = None
    if course.assigned_machine_id:
        machine = db.execute(
            select(LinacMachine).where(LinacMachine.id == course.assigned_machine_id)
        ).scalar_one_or_none()
        if machine:
            machine_name = machine.machine_name
            machine_status = machine.status

    # Plain language synthesis
    context_readable = course.clinical_context.replace("_", " ")
    if total_delay == 0:
        notice = (
            f"Your radiotherapy course ({context_readable}) is on schedule with no recorded delays. "
            f"Treatment is scheduled to start on {target_dt.strftime('%B %d, %Y')}."
        )
    else:
        reason_text = (
            ledger_entries[0].reason
            if ledger_entries
            else "equipment maintenance and capacity management"
        )
        notice = (
            f"Your radiotherapy treatment ({context_readable}) has experienced an accumulated delay of {total_delay} days "
            f"due to {reason_text}. Your oncology team has prioritized your continuity to ensure safe, effective delivery. "
            f"Your next scheduled session is on {target_dt.strftime('%B %d, %Y')}."
        )

    return PatientDelayNoticeResponse(
        patient_id=patient.id,
        has_active_treatment=True,
        course_id=course.id,
        clinical_context=course.clinical_context,
        total_delay_days=total_delay,
        machine_name=machine_name,
        machine_status=machine_status,
        expected_start_date=course.scheduled_start_date,
        plain_language_notice=notice,
        delay_history=[
            DelayLedgerEntryResponse(
                id=e.id,
                patient_id=e.patient_id,
                course_id=e.course_id,
                delay_days=e.delay_days,
                reason=e.reason,
                marginal_harm=e.marginal_harm,
                moved_from_date=e.moved_from_date,
                moved_to_date=e.moved_to_date,
                clinician_overridden=e.clinician_overridden,
                recorded_by=e.recorded_by,
                created_at=e.created_at,
                synthetic=True,
            )
            for e in ledger_entries
        ],
        synthetic=True,
    )
