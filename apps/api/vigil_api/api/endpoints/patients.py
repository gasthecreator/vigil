"""API Endpoints for Patient Management, Pathology Intake, Labs & Surveillance."""

import hashlib
import json
import math
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event
from vigil_api.auth import get_current_user, require_roles
from vigil_api.config import settings
from vigil_api.consent import has_active_consent, verify_patient_consent
from vigil_api.crypto import compute_blind_index
from vigil_api.database import get_db
from vigil_api.ml.detector_helpers import detector_from_dict, detector_to_dict
from vigil_api.ml.inference import SentinelEngine
from vigil_api.models.patient import BaselineProfile, LabResult, Patient, RiskInference
from vigil_api.models.v2 import (
    Alert,
    AlertSeverity,
    AlertStatus,
    CaregiverShare,
    ConsentRecord,
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskType,
    Observation,
    RiskAssessment,
    Symptom,
    User,
    UserRole,
)
from vigil_api.schemas.baseline import BaselineCreate, BaselineResponse
from vigil_api.schemas.inference import (
    RiskInferenceResponse,
    SimulationRequest,
    SimulationResponse,
    TrajectoryPoint,
    TriageQueueItem,
)
from vigil_api.schemas.lab import LabResultCreate
from vigil_api.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from vigil_api.schemas.v2 import (
    AlertSummary,
    CaregiverShareCreateRequest,
    CaregiverShareResponse,
    ConsentCreateRequest,
    DisclosureLockRequest,
    DisclosureLockResponse,
    DisclosureReleaseRequest,
    DisclosureReleaseRequestResponse,
    DisclosureUnlockRequest,
    DisclosureUnlockResponse,
    FollowUpTaskSummary,
    ObservationCreateRequest,
    ObservationCreateResponse,
    PlainLanguageExplainerResponse,
    RiskAssessmentSummary,
    SecondLookCreateRequest,
    SecondLookResponse,
    SymptomCreateRequest,
    SymptomResponse,
)
from vigil_core.analytes import check_plausibility, get_analyte
from vigil_core.units import IncompatibleUnitsError, InvalidUnitError, UnitConversionError
from vigil_ml.m3 import adjudicate
from vigil_ml.m5 import (
    render_clinician_note,
    render_plain_language_explainer,
    verify_narrative,
)

router = APIRouter()

DISCLOSURE_LOCKED_DETAIL = {
    "code": "disclosure_locked",
    "message": "Your care team has this result and will talk it through with you. Please ask them when you are ready.",
}


def mask_identifier(val: Optional[str]) -> Optional[str]:
    """Masks an identifier returning only the last two characters."""
    if not val:
        return None
    val_str = str(val)
    return f"***{val_str[-2:]}" if len(val_str) >= 2 else "***"


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registers a new patient into the oncology surveillance roster."""
    now = datetime.now(timezone.utc)

    # Enforce ADR 0011: Prohibit duplicate MRN or external_id registration
    mrn_bidx = compute_blind_index(payload.mrn) if payload.mrn else None
    if mrn_bidx:
        existing_mrn = db.query(Patient).filter(Patient.mrn_bidx == mrn_bidx).first()
        if existing_mrn:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with MRN already registered in surveillance database (ID: {existing_mrn.id}). Duplicate MRNs are prohibited by policy.",
            )

    ext_bidx = compute_blind_index(payload.external_id) if payload.external_id else None
    if ext_bidx:
        existing_ext = db.query(Patient).filter(Patient.external_id_bidx == ext_bidx).first()
        if existing_ext:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with external_id already registered in surveillance database (ID: {existing_ext.id}).",
            )

    patient = Patient(
        age=payload.age,
        status=payload.status,
        mrn=payload.mrn,
        external_id=payload.external_id,
        mrn_bidx=mrn_bidx,
        external_id_bidx=ext_bidx,
        synthetic=True,
        created_at=now,
        updated_at=now,
    )
    db.add(patient)
    db.flush()

    # Record audit event for patient creation (Condition S5-3)
    record_audit_event(
        db=db,
        actor_id=current_user.id if current_user else "unknown",
        actor_role=current_user.role if current_user else "clinician",
        action="patient.created",
        resource_type="Patient",
        resource_id=patient.id,
        details={"age": patient.age, "status": patient.status, "has_mrn": bool(patient.mrn)},
        timestamp=now,
    )

    db.commit()
    db.refresh(patient)
    return patient


@router.get("/", response_model=List[PatientResponse])
def list_patients(
    skip: int = 0,
    limit: int = 100,
    mrn: Optional[str] = None,
    external_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all registered patients, optionally filtering by blind-indexed MRN or external_id.

    Redacts identifiers (MRN, external_id) unless active patient consent exists.
    Blocks searching by MRN/external_id if active consent is not present (Condition P9-D).
    """
    query = db.query(Patient)
    if mrn:
        bidx = compute_blind_index(mrn)
        query = query.filter(Patient.mrn_bidx == bidx)
    if external_id:
        bidx = compute_blind_index(external_id)
        query = query.filter(Patient.external_id_bidx == bidx)

    patients = query.offset(skip).limit(limit).all()

    # If caller specifically queries by MRN or external_id:
    # Block MRN search without consent (prevent existence confirmation / enumeration)
    if mrn or external_id:
        consented_results: List[PatientResponse] = []
        for p in patients:
            if has_active_consent(p.id, db, current_user):
                consented_results.append(
                    PatientResponse(
                        id=p.id,
                        age=p.age,
                        created_at=p.created_at,
                        status=p.status,
                        mrn=p.mrn,
                        external_id=p.external_id,
                        is_masked=False,
                    )
                )
        return consented_results

    # General list: return all patients, but strip/mask identifiers unless consent is active
    results: List[PatientResponse] = []
    for p in patients:
        consented = has_active_consent(p.id, db, current_user)
        results.append(
            PatientResponse(
                id=p.id,
                age=p.age,
                created_at=p.created_at,
                status=p.status,
                mrn=p.mrn if consented else mask_identifier(p.mrn),
                external_id=p.external_id if consented else mask_identifier(p.external_id),
                is_masked=not consented,
            )
        )
    return results


@router.get("/triage", response_model=List[TriageQueueItem])
def get_triage_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN, UserRole.QUALITY_LEAD
        )
    ),
):
    """
    View 1: Triage Queue.
    Returns the complete roster of patients dynamically ordered by composite Action Urgency
    (combining risk, uncertainty/abstention, overdue follow-ups, and treatment delay).
    Master Plan §6.9 (M9) / Phase 5b.
    """
    now = datetime.now(timezone.utc)
    patients = db.query(Patient).all()
    triage_roster: List[TriageQueueItem] = []

    for patient in patients:
        # Find latest risk inference
        latest_inference = (
            db.query(RiskInference)
            .filter(RiskInference.patient_id == patient.id)
            .order_by(desc(RiskInference.created_at))
            .first()
        )

        baseline = patient.baseline_profile
        subtype = "Unknown"
        organ_vector = None
        tumor_stage = None

        if baseline:
            tumor_stage = baseline.tumor_stage
            organ_vector = baseline.target_organ_susceptibility_vector
            if baseline.er_status and not baseline.her2_status:
                subtype = "Luminal A (ER+/PR+)"
            elif baseline.her2_status and (baseline.er_status or baseline.pr_status):
                subtype = "Luminal B (HER2+)"
            elif baseline.her2_status:
                subtype = "HER2-Enriched"
            else:
                subtype = "Triple Negative (TNBC)"

        last_lab = (
            db.query(LabResult)
            .filter(LabResult.patient_id == patient.id)
            .order_by(desc(LabResult.date_drawn))
            .first()
        )
        total_labs = db.query(LabResult).filter(LabResult.patient_id == patient.id).count()

        latest_risk = latest_inference.calculated_metastasis_risk if latest_inference else 0.0
        triage_flag = latest_inference.triage_flag if latest_inference else False
        justification = (
            latest_inference.justification_text
            if latest_inference
            else "Awaiting initial surveillance lab draw."
        )

        # 1. Risk component (weight 0.40)
        s_risk = float(latest_risk)

        # 2. Uncertainty / Abstention component (weight 0.25)
        latest_assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.patient_id == patient.id)
            .order_by(desc(RiskAssessment.created_at))
            .first()
        )
        if latest_assessment:
            if latest_assessment.abstention:
                s_unc = 1.0
            else:
                p_err = (latest_assessment.uncertainty or {}).get("p_error", 0.0)
                margin = 0.04 * (1.0 - abs(latest_assessment.score - 0.5))
                s_unc = min(1.0, max(float(p_err), float(2.0 * margin)))
        else:
            margin = 0.04 * (1.0 - abs(latest_risk - 0.5))
            s_unc = min(1.0, float(2.0 * margin))

        # 3. Overdue follow-up tasks component (weight 0.20)
        active_tasks = (
            db.query(FollowUpTask)
            .filter(
                FollowUpTask.patient_id == patient.id,
                FollowUpTask.status.in_(["pending", "in_progress", "escalated"]),
            )
            .all()
        )
        max_overdue_days = 0.0
        max_escalation = 0
        for task in active_tasks:
            due = (
                task.due_date
                if task.due_date.tzinfo
                else task.due_date.replace(tzinfo=timezone.utc)
            )
            overdue_days = max(0.0, (now - due).total_seconds() / 86400.0)
            if overdue_days > max_overdue_days:
                max_overdue_days = overdue_days
            if task.escalation_level > max_escalation:
                max_escalation = task.escalation_level

        if active_tasks:
            s_overdue = min(1.0, max(max_overdue_days / 14.0, max_escalation / 3.0))
        else:
            s_overdue = 0.0

        # 4. Treatment / surveillance delay component (weight 0.15)
        if last_lab and last_lab.date_drawn:
            lab_date = (
                last_lab.date_drawn
                if last_lab.date_drawn.tzinfo
                else last_lab.date_drawn.replace(tzinfo=timezone.utc)
            )
            days_since = max(0.0, (now - lab_date).total_seconds() / 86400.0)
            if days_since > 90.0:
                s_delay = min(1.0, (days_since - 90.0) / 90.0)
            else:
                s_delay = 0.0
        else:
            s_delay = 0.5

        # Composite Action Urgency
        action_urgency = round(
            0.40 * s_risk + 0.25 * s_unc + 0.20 * s_overdue + 0.15 * s_delay,
            4,
        )
        urgency_breakdown = {
            "risk_component": round(0.40 * s_risk, 4),
            "uncertainty_component": round(0.25 * s_unc, 4),
            "overdue_component": round(0.20 * s_overdue, 4),
            "delay_component": round(0.15 * s_delay, 4),
        }

        triage_roster.append(
            TriageQueueItem(
                patient_id=patient.id,
                age=patient.age,
                status=patient.status,
                tumor_stage=tumor_stage,
                subtype=subtype,
                latest_risk=latest_risk,
                triage_flag=triage_flag,
                latest_justification=justification,
                target_organ_susceptibility_vector=organ_vector,
                last_lab_date=last_lab.date_drawn if last_lab else None,
                total_labs=total_labs,
                action_urgency=action_urgency,
                urgency_breakdown=urgency_breakdown,
            )
        )

    # Sort strictly descending by action_urgency, breaking ties by latest_risk and recency
    triage_roster.sort(
        key=lambda x: (
            x.action_urgency,
            x.latest_risk,
            x.last_lab_date.timestamp() if x.last_lab_date else 0.0,
        ),
        reverse=True,
    )
    return triage_roster


@router.get("/{id}", response_model=dict)
def get_patient_detail(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves single patient details, baseline profile, and latest risk inference."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)

    baseline = patient.baseline_profile
    latest_inference = (
        db.query(RiskInference)
        .filter(RiskInference.patient_id == id)
        .order_by(desc(RiskInference.created_at))
        .first()
    )

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="patient.read",
        resource_type="Patient",
        resource_id=patient.id,
        details={},
    )
    db.commit()

    return {
        "id": patient.id,
        "mrn": patient.mrn,
        "external_id": patient.external_id,
        "age": patient.age,
        "status": patient.status,
        "synthetic": patient.synthetic,
        "created_at": patient.created_at,
        "baseline_profile": {
            "id": baseline.id,
            "tumor_stage": baseline.tumor_stage,
            "er_status": baseline.er_status,
            "pr_status": baseline.pr_status,
            "her2_status": baseline.her2_status,
            "has_hypertension": baseline.has_hypertension,
            "renal_history": baseline.renal_history,
            "target_organ_susceptibility_vector": baseline.target_organ_susceptibility_vector,
        }
        if baseline
        else None,
        "latest_risk": latest_inference.calculated_metastasis_risk if latest_inference else None,
        "triage_flag": latest_inference.triage_flag if latest_inference else False,
        "latest_justification": latest_inference.justification_text if latest_inference else None,
    }


@router.patch("/{id}", response_model=PatientResponse)
def update_patient(
    id: str,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Updates patient demographics or encrypted identifiers."""
    now = datetime.now(timezone.utc)
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)

    if payload.age is not None:
        patient.age = payload.age
    if payload.status is not None:
        patient.status = payload.status
    if payload.mrn is not None:
        bidx = compute_blind_index(payload.mrn)
        existing = db.query(Patient).filter(Patient.mrn_bidx == bidx, Patient.id != id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with MRN already registered in surveillance database (ID: {existing.id}). Duplicate MRNs are prohibited by policy.",
            )
        patient.mrn = payload.mrn
        patient.mrn_bidx = bidx
    if payload.external_id is not None:
        ext_bidx = compute_blind_index(payload.external_id)
        existing_ext = (
            db.query(Patient).filter(Patient.external_id_bidx == ext_bidx, Patient.id != id).first()
        )
        if existing_ext:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with external_id already registered in surveillance database (ID: {existing_ext.id}).",
            )
        patient.external_id = payload.external_id
        patient.external_id_bidx = ext_bidx
    patient.updated_at = now

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="patient.updated",
        resource_type="Patient",
        resource_id=patient.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        timestamp=now,
    )
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/rotate-keys", status_code=status.HTTP_200_OK)
def rotate_patient_keys_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Triggers re-encryption of all patient MRN and external_id ciphertexts to the latest primary key.

    Admin-only global operation. Master Plan §11 / Condition P9-E.
    """
    from vigil_api.keyrotation import rotate_patient_keys

    scanned, rotated = rotate_patient_keys(db, dry_run=False)
    now = datetime.now(timezone.utc)
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="security.keys_rotated",
        resource_type="PatientEncryption",
        resource_id="all",
        details={"scanned": scanned, "rotated": rotated},
        timestamp=now,
    )
    db.commit()
    return {"status": "success", "scanned": scanned, "rotated": rotated}


@router.post("/{id}/baseline", response_model=BaselineResponse)
def submit_baseline_profile(
    id: str,
    payload: BaselineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits primary tumor pathology and comorbidities."""
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    engine = SentinelEngine.get_instance()
    model_a_input = {
        "age": patient.age,
        "tumor_stage": payload.tumor_stage,
        "er_status": payload.er_status,
        "pr_status": payload.pr_status,
        "her2_status": payload.her2_status,
        "has_hypertension": payload.has_hypertension,
        "renal_history": payload.renal_history,
    }
    organ_vector = engine.predict_baseline_susceptibility(model_a_input)

    # Check if baseline already exists, update or create
    baseline = db.query(BaselineProfile).filter(BaselineProfile.patient_id == id).first()
    if baseline:
        baseline.tumor_stage = payload.tumor_stage
        baseline.er_status = payload.er_status
        baseline.pr_status = payload.pr_status
        baseline.her2_status = payload.her2_status
        baseline.has_hypertension = payload.has_hypertension
        baseline.renal_history = payload.renal_history
        baseline.target_organ_susceptibility_vector = organ_vector
    else:
        baseline = BaselineProfile(
            id=str(uuid.uuid4()),
            patient_id=id,
            tumor_stage=payload.tumor_stage,
            er_status=payload.er_status,
            pr_status=payload.pr_status,
            her2_status=payload.her2_status,
            has_hypertension=payload.has_hypertension,
            renal_history=payload.renal_history,
            target_organ_susceptibility_vector=organ_vector,
        )
        db.add(baseline)

    record_audit_event(
        db=db,
        actor_id=current_user.id if current_user else "unknown",
        actor_role=current_user.role if current_user else "clinician",
        action="baseline.updated",
        resource_type="BaselineProfile",
        resource_id=baseline.id,
        details={"tumor_stage": baseline.tumor_stage, "patient_id": id},
    )

    db.commit()
    db.refresh(baseline)
    return baseline


def ingest_single_observation_internal(
    db: Session,
    patient: Patient,
    current_user: User,
    analyte_code: str,
    value: float,
    unit: str,
    specimen_collected_at: Optional[datetime] = None,
    laboratory_id: Optional[str] = None,
    lab_changed: bool = False,
) -> Tuple[Observation, RiskAssessment, Optional[Alert], Optional[FollowUpTask], Dict[str, Any]]:
    """Canonical single-observation ingestion engine.

    Enforces:
    1. Positive non-NaN value bounds.
    2. Registry lookup & unit conversion with zero silent unit coercion.
    3. Longitudinal history gathering & M3 plausibility adjudication.
    4. K2 sequential e-detector update.
    5. M5 strictly verified narrative rendering.
    6. Input SHA-256 hashing and immutable Observation/RiskAssessment creation.
    7. No-dismissal invariant: creates Alert & FollowUpTask for surprising findings.
    8. Cryptographically chained AuditEvent creation.
    """
    now = datetime.now(timezone.utc)
    if value <= 0.0 or math.isnan(value) or math.isinf(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Observation value must be strictly positive (> 0.0), got {value}.",
        )

    clean_code = analyte_code.strip().lower()
    try:
        analyte = get_analyte(clean_code)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Analyte '{analyte_code}' not found in registry.",
        )

    try:
        plausibility = check_plausibility(analyte.code, value, unit)
    except (InvalidUnitError, IncompatibleUnitsError, UnitConversionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unit validation failed: {str(exc)}. Silent unit coercion is forbidden.",
        )

    specimen_date = specimen_collected_at or now
    if specimen_date.tzinfo is None:
        specimen_date = specimen_date.replace(tzinfo=timezone.utc)

    # 1. Fetch historical observations for this analyte to supply M3
    history_obs = (
        db.execute(
            select(Observation)
            .where(Observation.patient_id == patient.id, Observation.analyte_code == analyte.code)
            .order_by(Observation.specimen_collected_at.asc())
        )
        .scalars()
        .all()
    )

    pt_created = patient.created_at
    if pt_created.tzinfo is None:
        pt_created = pt_created.replace(tzinfo=timezone.utc)

    history: List[Tuple[float, float]] = []
    for obs_item in history_obs:
        obs_dt = obs_item.specimen_collected_at
        if obs_dt.tzinfo is None:
            obs_dt = obs_dt.replace(tzinfo=timezone.utc)
        day_offset = (obs_dt - pt_created).total_seconds() / 86400.0
        history.append((day_offset, obs_item.value))

    current_day = (specimen_date - pt_created).total_seconds() / 86400.0

    # 2. Execute M3 Plausibility Adjudication
    cv_a = analyte.analytical_spec.cv_a_desirable / 100.0
    cv_i = analyte.biological_variation.cv_i / 100.0
    m3_result = adjudicate(
        history=history,
        new_day=current_day,
        new_value=plausibility.canonical_value,
        cv_analytical=cv_a,
        cv_within=cv_i,
        lab_changed=lab_changed,
    )

    # 3. Update & Persist K2 SequentialDetector
    detector = detector_from_dict(patient.detector_state)
    detector.update(day=current_day, value=plausibility.canonical_value)
    patient.detector_state = detector_to_dict(detector)

    # 4. Generate & Verify M5 Clinician Note
    clinical_note = render_clinician_note(m3_result["rationale_facts"])
    verification = verify_narrative(clinical_note, m3_result["rationale_facts"])
    if not verification["ok"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety verification failed on clinical narrative: {verification['violations']}",
        )

    # 5. Compute Input Hash (SHA-256)
    input_payload = {
        "patient_id": patient.id,
        "analyte": analyte.code,
        "raw_value": value,
        "raw_unit": unit,
        "canonical_value": plausibility.canonical_value,
        "canonical_unit": plausibility.canonical_unit,
        "specimen_collected_at": specimen_date.isoformat(),
    }
    input_hash = hashlib.sha256(
        json.dumps(input_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    # 6. Save Observation
    obs = Observation(
        patient_id=patient.id,
        analyte_code=analyte.code,
        value=plausibility.canonical_value,
        unit=plausibility.canonical_unit,
        specimen_collected_at=specimen_date,
        result_received_at=now,
        laboratory_id=laboratory_id,
        lab_changed=lab_changed,
        plausibility_status=plausibility.status.value,
        raw_value=value,
        raw_unit=unit,
        status="valid" if plausibility.is_valid else "flagged_implausible",
        created_at=now,
    )
    db.add(obs)
    db.flush()

    # 7. Save RiskAssessment
    risk_tier = (
        "high"
        if (m3_result["action"] == "escalate" or detector.alert)
        else "medium"
        if m3_result["action"] == "needs_repeat"
        else "low"
    )
    risk = RiskAssessment(
        patient_id=patient.id,
        observation_id=obs.id,
        assessment_date=specimen_date,
        model_versions={"M3": "1.0", "K2": "1.0", "M5": "1.0"},
        input_hash=input_hash,
        score=m3_result["p_real"],
        risk_tier=risk_tier,
        uncertainty={
            "p_error": m3_result["p_error"],
            "p_stable": m3_result["p_stable"],
            "log_e": detector.log_e,
            "k2_tier": detector.tier.value,
            "k2_alert": detector.alert,
        },
        abstention=False,
        adjudicated_action=m3_result["action"],
        clinical_note=clinical_note,
        rationale_facts=m3_result["rationale_facts"],
        k2_state_snapshot=detector_to_dict(detector),
        created_at=now,
    )
    db.add(risk)
    db.flush()

    # 8. No-Dismissal Invariant: Alert & Follow-Up Task for surprising/non-routine findings
    is_surprising = (
        m3_result["action"] in ("escalate", "needs_repeat")
        or detector.alert
        or not plausibility.is_valid
        or plausibility.is_critical
    )
    alert = None
    task = None

    if is_surprising:
        alert_type = (
            "biomarker_spike"
            if m3_result["action"] == "escalate"
            else "lab_error_repeat"
            if m3_result["action"] == "needs_repeat"
            else "sequential_divergence"
            if detector.alert
            else "critical_panic_boundary"
        )
        severity = (
            AlertSeverity.CRITICAL.value
            if (m3_result["action"] == "escalate" or plausibility.is_critical)
            else AlertSeverity.WARNING.value
        )
        alert = Alert(
            patient_id=patient.id,
            risk_assessment_id=risk.id,
            alert_type=alert_type,
            severity=severity,
            trigger_reason=f"{analyte.name}: {clinical_note}",
            status=AlertStatus.OPEN.value,
            created_at=now,
        )
        db.add(alert)
        db.flush()

        task_type = (
            FollowUpTaskType.REPEAT_SPECIMEN.value
            if m3_result["action"] == "needs_repeat"
            else FollowUpTaskType.IMAGING_REFERRAL.value
            if m3_result["action"] == "escalate"
            else FollowUpTaskType.CLINICAL_REVIEW.value
        )
        due_days = 2 if severity == AlertSeverity.CRITICAL.value else 7
        task = FollowUpTask(
            patient_id=patient.id,
            alert_id=alert.id,
            task_type=task_type,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=specimen_date + timedelta(days=due_days),
            escalation_level=0,
            notes=f"Surveillance guardian alert: {alert_type} (action: {m3_result['action']})",
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        db.flush()

    # 9. Cryptographic Audit Log
    record_audit_event(
        db=db,
        actor_id=current_user.id if current_user else "unknown",
        actor_role=current_user.role if current_user else "clinician",
        action="observation.ingest",
        resource_type="Observation",
        resource_id=obs.id,
        details={
            "patient_id": patient.id,
            "analyte": analyte.code,
            "raw_value": value,
            "raw_unit": unit,
            "canonical_value": plausibility.canonical_value,
            "action": m3_result["action"],
            "has_alert": is_surprising,
        },
        timestamp=now,
    )

    return obs, risk, alert, task, m3_result


@router.post("/{id}/labs", response_model=RiskInferenceResponse)
def submit_lab_result(
    id: str,
    payload: LabResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits new lab result draw.

    Condition S5-2 & S5-7: Re-routes all analytes through the canonical observation ingestion
    pipeline (M3 adjudication, K2 sequential detector, M5 clinical narrative, alert/task creation,
    and cryptographic audit logging) to enforce the no-dismissal invariant on all write paths.
    """
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    drawn_date = payload.date_drawn if payload.date_drawn else datetime.now(timezone.utc)
    if drawn_date.tzinfo is None:
        drawn_date = drawn_date.replace(tzinfo=timezone.utc)

    # Ingest each non-null analyte through the no-dismissal pipeline
    analyte_draws = [
        ("ca_15_3", payload.ca_15_3, "U/mL"),
        ("alt", payload.alt_level, "U/L"),
        ("ast", payload.ast_level, "U/L"),
        ("creatinine", payload.creatinine, "mg/dL"),
        ("wbc", payload.wbc_count, "10^3/uL"),
    ]

    last_risk_score = 0.0
    has_alert = False
    justifications = []

    for code, val, unit in analyte_draws:
        if val is not None and val > 0.0:
            obs, risk, alert, task, m3_res = ingest_single_observation_internal(
                db=db,
                patient=patient,
                current_user=current_user,
                analyte_code=code,
                value=float(val),
                unit=unit,
                specimen_collected_at=drawn_date,
            )
            last_risk_score = max(last_risk_score, risk.score)
            if alert is not None:
                has_alert = True
            justifications.append(f"{code}: {m3_res['action']}")

    # Save legacy LabResult record for backward schema compatibility
    lab_record = LabResult(
        patient_id=id,
        date_drawn=drawn_date,
        alt_level=payload.alt_level,
        ast_level=payload.ast_level,
        creatinine=payload.creatinine,
        ca_15_3=payload.ca_15_3,
        wbc_count=payload.wbc_count,
    )
    db.add(lab_record)
    db.flush()

    # Query historical labs for legacy SentinelEngine risk projection
    historical_labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == id, LabResult.id != lab_record.id)
        .order_by(LabResult.date_drawn.asc())
        .all()
    )
    historical_dicts = [
        {
            "date_drawn": h.date_drawn.isoformat(),
            "alt_level": h.alt_level,
            "ast_level": h.ast_level,
            "creatinine": h.creatinine,
            "ca_15_3": h.ca_15_3,
            "wbc_count": h.wbc_count,
        }
        for h in historical_labs
    ]
    baseline_dict = None
    if patient.baseline_profile:
        baseline_dict = {
            "target_organ_susceptibility_vector": patient.baseline_profile.target_organ_susceptibility_vector
        }

    engine = SentinelEngine.get_instance()
    calc_risk, legacy_triage, legacy_justification = engine.predict_risk(
        patient_id=id,
        new_lab_result={
            "date_drawn": lab_record.date_drawn.isoformat(),
            "alt_level": lab_record.alt_level,
            "ast_level": lab_record.ast_level,
            "creatinine": lab_record.creatinine,
            "ca_15_3": lab_record.ca_15_3,
            "wbc_count": lab_record.wbc_count,
        },
        historical_labs=historical_dicts,
        baseline_profile=baseline_dict,
    )

    is_triage = has_alert or last_risk_score >= settings.CLINICAL_ALERT_THRESHOLD or legacy_triage
    final_risk = max(last_risk_score, calc_risk)
    risk_record = RiskInference(
        patient_id=id,
        lab_result_id=lab_record.id,
        calculated_metastasis_risk=final_risk,
        triage_flag=is_triage,
        justification_text=legacy_justification,
        created_at=datetime.now(timezone.utc),
    )
    db.add(risk_record)
    db.commit()
    db.refresh(risk_record)

    return risk_record


@router.get("/{id}/trajectory", response_model=List[TrajectoryPoint])
def get_patient_trajectory(id: str, db: Session = Depends(get_db)):
    """
    Returns full longitudinal surveillance trajectory for a patient, joining
    each lab draw with its corresponding calculated_metastasis_risk, triage_flag,
    and clinical justification_text.
    """
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == id)
        .order_by(LabResult.date_drawn.asc())
        .all()
    )

    trajectory: List[TrajectoryPoint] = []
    prev_ca153 = None
    prev_alt = None

    for lab in labs:
        inference = lab.risk_inference
        risk = inference.calculated_metastasis_risk if inference else 0.0

        # Conformal uncertainty margin
        margin = 0.04 * (1.0 - abs(risk - 0.5))
        ci_lower = max(0.0, round(risk - margin, 4))
        ci_upper = min(1.0, round(risk + margin, 4))

        # Velocity calculations
        ca_vel = 0.0
        alt_vel = 0.0
        if prev_ca153 is not None and prev_ca153 > 0:
            ca_vel = round(((lab.ca_15_3 - prev_ca153) / prev_ca153) * 100.0, 1)
        if prev_alt is not None and prev_alt > 0:
            alt_vel = round(((lab.alt_level - prev_alt) / prev_alt) * 100.0, 1)

        prev_ca153 = lab.ca_15_3
        prev_alt = lab.alt_level

        trajectory.append(
            TrajectoryPoint(
                lab_id=lab.id,
                date_drawn=lab.date_drawn,
                alt_level=lab.alt_level,
                ast_level=lab.ast_level,
                creatinine=lab.creatinine,
                ca_15_3=lab.ca_15_3,
                wbc_count=lab.wbc_count,
                calculated_metastasis_risk=risk,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                ca153_velocity_pct=ca_vel,
                alt_velocity_pct=alt_vel,
                triage_flag=inference.triage_flag if inference else False,
                justification_text=inference.justification_text
                if inference
                else "Pending model evaluation.",
            )
        )

    return trajectory


@router.post("/{id}/simulate", response_model=SimulationResponse)
def simulate_future_lab(id: str, payload: SimulationRequest, db: Session = Depends(get_db)):
    """
    'What-If' Simulation Endpoint.
    Allows oncologists to project the impact of a hypothetical future lab draw
    on the patient's continuous metastasis risk trajectory.
    """
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == id)
        .order_by(LabResult.date_drawn.asc())
        .all()
    )
    historical_dicts = [
        {
            "date_drawn": lab.date_drawn.isoformat(),
            "alt_level": lab.alt_level,
            "ast_level": lab.ast_level,
            "creatinine": lab.creatinine,
            "ca_15_3": lab.ca_15_3,
            "wbc_count": lab.wbc_count,
        }
        for lab in labs
    ]

    baseline_dict = None
    if patient.baseline_profile:
        baseline_dict = {
            "target_organ_susceptibility_vector": patient.baseline_profile.target_organ_susceptibility_vector
        }

    latest_inference = (
        db.query(RiskInference)
        .filter(RiskInference.patient_id == id)
        .order_by(desc(RiskInference.created_at))
        .first()
    )
    current_risk = latest_inference.calculated_metastasis_risk if latest_inference else 0.0

    hypothetical_lab = dict(payload.hypothetical_lab)
    hypothetical_lab.setdefault("date_drawn", datetime.utcnow().isoformat())

    engine = SentinelEngine.get_instance()
    proj_risk, triage_flag, justification = engine.predict_risk(
        patient_id=id,
        new_lab_result=hypothetical_lab,
        historical_labs=historical_dicts,
        baseline_profile=baseline_dict,
    )

    delta = float(round(proj_risk - current_risk, 4))
    return SimulationResponse(
        projected_risk=proj_risk,
        triage_flag=triage_flag,
        justification_text=justification,
        delta_risk=delta,
    )


@router.post(
    "/{id}/observations",
    response_model=ObservationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Unit-safe observation ingestion calling M3, K2, and M5",
)
def ingest_observation(
    id: str,
    payload: ObservationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)
    ),
):
    """Unit-safe ingestion validating against Analyte Registry, executing M3 adjudication,
    updating K2 sequential detector, verifying M5 clinical note, and enforcing no-dismissal invariant.
    """
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    obs, risk, alert, task, m3_result = ingest_single_observation_internal(
        db=db,
        patient=patient,
        current_user=current_user,
        analyte_code=payload.analyte_code,
        value=payload.value,
        unit=payload.unit,
        specimen_collected_at=payload.specimen_collected_at,
        laboratory_id=payload.laboratory_id,
        lab_changed=payload.lab_changed,
    )
    db.commit()

    alert_summary = (
        AlertSummary(
            id=alert.id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            trigger_reason=alert.trigger_reason,
            status=alert.status,
            created_at=alert.created_at,
        )
        if alert
        else None
    )
    follow_up_summary = (
        FollowUpTaskSummary(
            id=task.id,
            task_type=task.task_type,
            status=task.status,
            due_date=task.due_date,
            escalation_level=task.escalation_level,
            notes=task.notes,
        )
        if task
        else None
    )

    return ObservationCreateResponse(
        observation_id=obs.id,
        patient_id=patient.id,
        analyte_code=obs.analyte_code,
        canonical_value=obs.value,
        canonical_unit=obs.unit,
        raw_value=obs.raw_value,
        raw_unit=obs.raw_unit,
        specimen_collected_at=obs.specimen_collected_at,
        plausibility_status=obs.plausibility_status,
        adjudicated_action=m3_result["action"],
        risk_assessment=RiskAssessmentSummary(
            id=risk.id,
            assessment_date=risk.assessment_date,
            model_versions=risk.model_versions,
            input_hash=risk.input_hash,
            score=risk.score,
            risk_tier=risk.risk_tier,
            uncertainty=risk.uncertainty,
            adjudicated_action=risk.adjudicated_action,
            clinical_note=risk.clinical_note,
            abstention=risk.abstention,
        ),
        alert=alert_summary,
        follow_up_task=follow_up_summary,
        synthetic=True,
    )


@router.get(
    "/{id}/observations",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List patient clinical observations",
)
def list_patient_observations(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve observations for consented patient."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    obs_list = (
        db.execute(
            select(Observation)
            .where(Observation.patient_id == patient.id)
            .order_by(Observation.specimen_collected_at.asc())
        )
        .scalars()
        .all()
    )
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="observations.read",
        resource_type="Patient",
        resource_id=patient.id,
        details={"observation_count": len(obs_list)},
    )
    db.commit()

    res = []
    for o in obs_list:
        flags = getattr(o, "quality_flags", None)
        if not flags and o.risk_assessment:
            ra = o.risk_assessment
            unc = ra.uncertainty or {}
            flags = {
                "action": ra.adjudicated_action,
                "p_real": ra.score,
                "p_error": unc.get("p_error", 0.0),
                "p_stable": unc.get("p_stable", 0.0),
                "narrative": ra.clinical_note,
            }
        res.append(
            {
                "id": o.id,
                "patient_id": o.patient_id,
                "analyte_code": o.analyte_code,
                "value": o.value,
                "unit": o.unit,
                "raw_value": o.raw_value,
                "raw_unit": o.raw_unit,
                "plausibility_status": o.plausibility_status,
                "quality_flags": flags,
                "specimen_collected_at": o.specimen_collected_at.isoformat(),
                "status": o.status,
                "synthetic": patient.synthetic,
            }
        )
    return res


@router.get(
    "/{id}/risk-history",
    response_model=List[RiskAssessmentSummary],
    status_code=status.HTTP_200_OK,
    summary="List patient serial risk assessments",
)
def list_patient_risk_history(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve risk assessment trajectory for consented patient."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    assessments = (
        db.execute(
            select(RiskAssessment)
            .where(RiskAssessment.patient_id == patient.id)
            .order_by(RiskAssessment.assessment_date.desc())
        )
        .scalars()
        .all()
    )
    return [
        RiskAssessmentSummary(
            id=a.id,
            assessment_date=a.assessment_date,
            model_versions=a.model_versions or {},
            input_hash=a.input_hash,
            score=a.score,
            risk_tier=a.risk_tier,
            uncertainty=a.uncertainty,
            adjudicated_action=a.adjudicated_action,
            clinical_note=a.clinical_note,
            abstention=a.abstention,
        )
        for a in assessments
    ]


@router.post(
    "/{id}/consent",
    status_code=status.HTTP_201_CREATED,
    summary="Update or grant patient consent record",
)
def record_consent(
    id: str,
    payload: Optional[ConsentCreateRequest] = None,
    consent_type: str = "surveillance_monitoring",
    granted: bool = True,
    scope: str = "full",
    expires_at: Optional[datetime] = None,
    withdrawn_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CLINICIAN, UserRole.ADMIN, UserRole.NURSE_CLERK)
    ),
):
    """Record, revoke, or expire a patient consent record."""
    patient = db.execute(select(Patient).where(Patient.id == id)).scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient '{id}' not found.")

    now = datetime.now(timezone.utc)
    c_type = payload.consent_type if payload else consent_type
    c_granted = payload.granted if payload else granted
    c_scope = payload.scope if payload else scope
    c_expires = payload.expires_at if payload else expires_at
    c_withdrawn = payload.withdrawn_at if payload else withdrawn_at

    consent = ConsentRecord(
        patient_id=patient.id,
        consent_type=c_type,
        granted=c_granted,
        granted_at=now,
        expires_at=c_expires,
        withdrawn_at=c_withdrawn,
        scope=c_scope,
    )
    db.add(consent)
    db.flush()

    # Record audit event for consent grant/revocation (Condition S5-3)
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="consent.granted" if c_granted else "consent.revoked",
        resource_type="ConsentRecord",
        resource_id=consent.id,
        details={
            "patient_id": patient.id,
            "scope": c_scope,
            "granted": c_granted,
        },
        timestamp=now,
    )

    db.commit()
    return {
        "status": "success",
        "consent_id": consent.id,
        "patient_id": patient.id,
        "granted": consent.granted,
        "scope": consent.scope,
    }


# ==============================================================================
# Family & Patient Companion (M8) Endpoints: Symptoms, Shares, Second-Look
# ==============================================================================


@router.post("/{id}/symptoms", response_model=SymptomResponse, status_code=status.HTTP_201_CREATED)
def record_patient_symptom(
    id: str,
    payload: SymptomCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Records a structured patient symptom in the diary (Master Plan §6.8)."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    now = datetime.now(timezone.utc)

    symptom = Symptom(
        patient_id=patient.id,
        symptom_name=payload.symptom_name,
        severity=payload.severity,
        notes=payload.notes,
        input_modality=payload.input_modality,
        recorded_at=payload.recorded_at or now,
        created_at=now,
    )
    db.add(symptom)
    db.flush()

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="symptom.create",
        resource_type="Symptom",
        resource_id=symptom.id,
        details={
            "patient_id": patient.id,
            "symptom_name": payload.symptom_name,
            "severity": payload.severity,
            "modality": payload.input_modality,
        },
        timestamp=now,
    )
    db.commit()
    db.refresh(symptom)

    return SymptomResponse(
        id=symptom.id,
        patient_id=symptom.patient_id,
        symptom_name=symptom.symptom_name,
        severity=symptom.severity,
        notes=symptom.notes,
        input_modality=symptom.input_modality,
        recorded_at=symptom.recorded_at,
        created_at=symptom.created_at,
        synthetic=True,
    )


@router.get("/{id}/symptoms", response_model=List[SymptomResponse], status_code=status.HTTP_200_OK)
def list_patient_symptoms(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists symptom history for a consented patient."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    symptoms = (
        db.execute(
            select(Symptom)
            .where(Symptom.patient_id == patient.id)
            .order_by(desc(Symptom.recorded_at))
        )
        .scalars()
        .all()
    )
    return [
        SymptomResponse(
            id=s.id,
            patient_id=s.patient_id,
            symptom_name=s.symptom_name,
            severity=s.severity,
            notes=s.notes,
            input_modality=s.input_modality,
            recorded_at=s.recorded_at,
            created_at=s.created_at,
            synthetic=True,
        )
        for s in symptoms
    ]


@router.post(
    "/{id}/shares", response_model=CaregiverShareResponse, status_code=status.HTTP_201_CREATED
)
def create_caregiver_share(
    id: str,
    payload: CaregiverShareCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates a scoped, revocable caregiver access authorization token."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    now = datetime.now(timezone.utc)
    token = f"cg_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    token_preview = f"{token[:5]}...{token[-4:]}"
    expires_at = now + timedelta(days=payload.expires_in_days)

    share = CaregiverShare(
        patient_id=patient.id,
        token_hash=token_hash,
        token_preview=token_preview,
        caregiver_name=payload.caregiver_name,
        relationship_type=payload.relationship_type,
        scope=payload.scope,
        status="active",
        expires_at=expires_at,
        created_at=now,
    )
    db.add(share)
    db.flush()

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="caregiver_share.create",
        resource_type="CaregiverShare",
        resource_id=share.id,
        details={
            "patient_id": patient.id,
            "caregiver_name": payload.caregiver_name,
            "scope": payload.scope,
            "token_preview": token_preview,
            "expires_at": expires_at.isoformat(),
        },
        timestamp=now,
    )
    db.commit()
    db.refresh(share)

    # Return raw token ONCE upon creation; token_preview for UI display
    return CaregiverShareResponse(
        id=share.id,
        patient_id=share.patient_id,
        share_token=token,
        token_preview=share.token_preview,
        caregiver_name=share.caregiver_name,
        relationship_type=share.relationship_type,
        scope=share.scope,
        status=share.status,
        expires_at=share.expires_at,
        revoked_at=share.revoked_at,
        created_at=share.created_at,
        synthetic=True,
    )


@router.get(
    "/{id}/shares", response_model=List[CaregiverShareResponse], status_code=status.HTTP_200_OK
)
def list_caregiver_shares(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists caregiver shares for a consented patient."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    shares = (
        db.execute(
            select(CaregiverShare)
            .where(CaregiverShare.patient_id == patient.id)
            .order_by(desc(CaregiverShare.created_at))
        )
        .scalars()
        .all()
    )
    return [
        CaregiverShareResponse(
            id=s.id,
            patient_id=s.patient_id,
            share_token=None,  # NEVER reveal raw bearer token on listing
            token_preview=s.token_preview,
            caregiver_name=s.caregiver_name,
            relationship_type=s.relationship_type,
            scope=s.scope,
            status=s.status,
            expires_at=s.expires_at,
            revoked_at=s.revoked_at,
            created_at=s.created_at,
            synthetic=True,
        )
        for s in shares
    ]


@router.delete(
    "/{id}/shares/{share_id}", response_model=CaregiverShareResponse, status_code=status.HTTP_200_OK
)
def revoke_caregiver_share(
    id: str,
    share_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revokes an active caregiver share."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    now = datetime.now(timezone.utc)

    share = db.execute(
        select(CaregiverShare).where(
            CaregiverShare.id == share_id,
            CaregiverShare.patient_id == patient.id,
        )
    ).scalar_one_or_none()

    if share is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share record not found.")

    share.status = "revoked"
    share.revoked_at = now

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="caregiver_share.revoked",
        resource_type="CaregiverShare",
        resource_id=share.id,
        details={"patient_id": patient.id, "share_id": share.id},
        timestamp=now,
    )
    db.commit()
    db.refresh(share)

    return CaregiverShareResponse(
        id=share.id,
        patient_id=share.patient_id,
        share_token=None,
        token_preview=share.token_preview,
        caregiver_name=share.caregiver_name,
        relationship_type=share.relationship_type,
        scope=share.scope,
        status=share.status,
        expires_at=share.expires_at,
        revoked_at=share.revoked_at,
        created_at=share.created_at,
        synthetic=True,
    )


@router.post(
    "/{id}/second-look", response_model=SecondLookResponse, status_code=status.HTTP_201_CREATED
)
def submit_second_look_request(
    id: str,
    payload: SecondLookCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits a patient-initiated Second-Look Request to the clinical care team."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    now = datetime.now(timezone.utc)

    obs = db.execute(
        select(Observation).where(
            Observation.id == payload.observation_id,
            Observation.patient_id == patient.id,
        )
    ).scalar_one_or_none()

    if obs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation '{payload.observation_id}' not found for patient '{patient.id}'.",
        )

    task_id = str(uuid.uuid4())
    notes_text = (
        f"Second-Look Request initiated by patient/caregiver for {obs.analyte_code.upper()} "
        f"({obs.value} {obs.unit}, collected {obs.specimen_collected_at.strftime('%Y-%m-%d')}). "
        f"Plausibility status: {obs.plausibility_status}. "
        f"Patient Notes: {payload.patient_notes or 'Review requested by patient.'}"
    )

    task = FollowUpTask(
        id=task_id,
        patient_id=patient.id,
        alert_id=None,
        task_type="second_look_request",
        status=FollowUpTaskStatus.PENDING.value,
        due_date=now + timedelta(days=7),
        escalation_level=0,
        notes=notes_text,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.flush()

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="patient.second_look_requested",
        resource_type="FollowUpTask",
        resource_id=task.id,
        details={
            "patient_id": patient.id,
            "observation_id": obs.id,
            "analyte": obs.analyte_code,
            "value": obs.value,
            "unit": obs.unit,
        },
        timestamp=now,
    )
    db.commit()

    return SecondLookResponse(
        task_id=task.id,
        observation_id=obs.id,
        patient_id=patient.id,
        analyte_code=obs.analyte_code,
        value=obs.value,
        unit=obs.unit,
        plausibility_status=obs.plausibility_status,
        status="submitted",
        notes=task.notes,
        created_at=now,
        synthetic=True,
    )


@router.post(
    "/{id}/disclosure/unlock",
    response_model=DisclosureUnlockResponse,
    status_code=status.HTTP_200_OK,
)
def unlock_patient_disclosure(
    id: str,
    payload: DisclosureUnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Clinician-controlled release of sensitive / bad-news results, persisted and audited."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    now = datetime.now(timezone.utc)
    patient.disclosure_unlocked_at = now

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="disclosure.unlocked",
        resource_type="PatientDisclosure",
        resource_id=patient.id,
        details={"reason": payload.reason},
        timestamp=now,
    )
    db.commit()

    return DisclosureUnlockResponse(
        unlocked=True,
        unlocked_at=now,
        message="Sensitive results unlocked for patient/caregiver viewing.",
        synthetic=True,
    )


@router.post(
    "/{id}/disclosure/request-release",
    response_model=DisclosureReleaseRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Patient or caregiver requests clinician release of bad-news diagnostic results",
)
def request_disclosure_release(
    id: str,
    payload: DisclosureReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient-initiated request asking their clinical care team to release withheld sensitive findings."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    now = datetime.now(timezone.utc)
    task_id = str(uuid.uuid4())
    notes_text = (
        f"Patient or caregiver requested clinician release of sensitive/escalate results. "
        f"Patient note: {payload.reason or 'Patient requested release.'}"
    )

    task = FollowUpTask(
        id=task_id,
        patient_id=patient.id,
        alert_id=None,
        task_type="disclosure_release_request",
        status=FollowUpTaskStatus.PENDING.value,
        due_date=now + timedelta(days=1),
        escalation_level=1,
        notes=notes_text,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.flush()

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="disclosure.release_requested",
        resource_type="FollowUpTask",
        resource_id=task.id,
        details={"patient_id": patient.id, "reason": payload.reason},
        timestamp=now,
    )
    db.commit()

    return DisclosureReleaseRequestResponse(
        requested=True,
        task_id=task.id,
        message="Request submitted. A clinician will review and release your results.",
        synthetic=True,
    )


@router.post(
    "/{id}/disclosure/lock",
    response_model=DisclosureLockResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician re-locks disclosure for a patient",
)
def lock_patient_disclosure(
    id: str,
    payload: DisclosureLockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN)),
):
    """Clinician-controlled re-locking of sensitive / bad-news results, persisted and audited."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    now = datetime.now(timezone.utc)
    patient.disclosure_unlocked_at = None

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="disclosure.locked",
        resource_type="PatientDisclosure",
        resource_id=patient.id,
        details={"reason": payload.reason},
        timestamp=now,
    )
    db.commit()

    return DisclosureLockResponse(
        locked=True,
        locked_at=now,
        message="Sensitive results re-locked. Patient and caregivers cannot view without new release.",
        synthetic=True,
    )


@router.get(
    "/{id}/observations/{obs_id}/explainer",
    response_model=PlainLanguageExplainerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verified plain-language result explainer for patient/family",
)
def get_observation_explainer(
    id: str,
    obs_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns an M5-verified plain-language result explainer with FKGL <= 8.0,
    uncertainty verbal band, and questions to ask doctor.
    """
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    obs = db.execute(
        select(Observation).where(Observation.id == obs_id, Observation.patient_id == patient.id)
    ).scalar_one_or_none()

    if obs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation '{obs_id}' not found for patient '{patient.id}'.",
        )

    # Determine verdict based on plausibility status or associated risk assessment
    verdict = "explained"
    if obs.plausibility_status in {"implausible", "extreme_spike"}:
        verdict = "needs_repeat"
    else:
        # Check if an alert or high risk is linked
        risk = (
            db.execute(
                select(RiskAssessment)
                .where(RiskAssessment.patient_id == patient.id)
                .order_by(desc(RiskAssessment.assessment_date))
            )
            .scalars()
            .first()
        )
        if risk and risk.adjudicated_action in {"escalate", "needs_repeat", "explained"}:
            verdict = risk.adjudicated_action
        elif risk and risk.risk_tier == "high":
            verdict = "escalate"

    if verdict == "escalate" and patient.disclosure_unlocked_at is None:
        record_audit_event(
            db=db,
            actor_id=current_user.id,
            actor_role=current_user.role,
            action="observation.explainer_withheld",
            resource_type="Observation",
            resource_id=obs.id,
            details={"patient_id": patient.id, "reason": "disclosure_locked"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=DISCLOSURE_LOCKED_DETAIL,
        )

    explainer = render_plain_language_explainer(verdict=verdict, analyte_code=obs.analyte_code)

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="observation.explainer_read",
        resource_type="Observation",
        resource_id=obs.id,
        details={
            "patient_id": patient.id,
            "verdict": explainer["verdict"],
            "reading_level": explainer["flesch_kincaid_grade_level"],
        },
    )
    db.commit()

    return PlainLanguageExplainerResponse(
        observation_id=obs.id,
        patient_id=patient.id,
        analyte_code=obs.analyte_code,
        verdict=explainer["verdict"],
        verbal_band=explainer["verbal_band"],
        headline=explainer["headline"],
        what_this_means=explainer["what_this_means"],
        recommended_action=explainer["recommended_action"],
        questions_to_ask_your_doctor=explainer["questions_to_ask_your_doctor"],
        flesch_kincaid_grade_level=explainer["flesch_kincaid_grade_level"],
        word_count=explainer["word_count"],
        verified=explainer["verified"],
        synthetic=True,
    )
