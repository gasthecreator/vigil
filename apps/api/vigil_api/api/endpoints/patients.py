"""API Endpoints for Patient Management, Pathology Intake, Labs & Surveillance."""

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event
from vigil_api.auth import get_current_user, require_roles
from vigil_api.consent import verify_patient_consent
from vigil_api.database import get_db
from vigil_api.ml.detector_helpers import detector_from_dict, detector_to_dict
from vigil_api.ml.inference import SentinelEngine
from vigil_api.models.patient import BaselineProfile, LabResult, Patient, RiskInference
from vigil_api.models.v2 import (
    Alert,
    AlertSeverity,
    AlertStatus,
    ConsentRecord,
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskType,
    Observation,
    RiskAssessment,
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
from vigil_api.schemas.patient import PatientCreate, PatientResponse
from vigil_api.schemas.v2 import (
    AlertSummary,
    FollowUpTaskSummary,
    ObservationCreateRequest,
    ObservationCreateResponse,
    RiskAssessmentSummary,
)
from vigil_core.analytes import check_plausibility, get_analyte
from vigil_core.units import IncompatibleUnitsError, InvalidUnitError, UnitConversionError
from vigil_ml.m3 import adjudicate
from vigil_ml.m5 import render_clinician_note, verify_narrative

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    """Registers a new patient into the oncology surveillance roster with active consent."""
    now = datetime.now(timezone.utc)
    patient = Patient(
        age=payload.age,
        status=payload.status,
        synthetic=True,
        created_at=now,
        updated_at=now,
    )
    db.add(patient)
    db.flush()

    # Automatically create initial surveillance consent record
    consent = ConsentRecord(
        patient_id=patient.id,
        consent_type="surveillance_monitoring",
        granted=True,
        granted_at=now,
        scope="full",
    )
    db.add(consent)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/", response_model=List[PatientResponse])
def list_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lists all registered patients."""
    patients = db.query(Patient).offset(skip).limit(limit).all()
    return patients


@router.get("/triage", response_model=List[TriageQueueItem])
def get_triage_queue(db: Session = Depends(get_db)):
    """
    View 1: Triage Queue.
    Returns the complete roster of patients dynamically ordered by their latest
    calculated_metastasis_risk (highest risk at the top).
    """
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
            )
        )

    # Sort strictly descending by latest_risk, breaking ties by most recent lab date
    triage_roster.sort(
        key=lambda x: (x.latest_risk, x.last_lab_date.timestamp() if x.last_lab_date else 0.0),
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

    return {
        "id": patient.id,
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


@router.post("/{id}/baseline", response_model=BaselineResponse)
def submit_baseline_profile(id: str, payload: BaselineCreate, db: Session = Depends(get_db)):
    """
    Submits primary tumor pathology and comorbidities.
    Executes Model A (XGBoost) inference to compute target organ susceptibility vector,
    and persists the baseline profile to database.
    """
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

    db.commit()
    db.refresh(baseline)
    return baseline


@router.post("/{id}/labs", response_model=RiskInferenceResponse)
def submit_lab_result(id: str, payload: LabResultCreate, db: Session = Depends(get_db)):
    """
    Submits new lab result draw.
    Retrieves longitudinal lab history + baseline susceptibility.
    Triggers Model B (Attention-LSTM) sequence inference.
    Saves RiskInference with calculated_metastasis_risk, triage_flag, and justification_text.
    """
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    drawn_date = payload.date_drawn if payload.date_drawn else datetime.utcnow()

    # Create new LabResult record
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
    db.commit()
    db.refresh(lab_record)

    # Fetch all historical labs including newly inserted, sorted by date
    all_labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == id)
        .order_by(LabResult.date_drawn.asc())
        .all()
    )

    historical_dicts = []
    for lab in all_labs:
        if lab.id != lab_record.id:
            historical_dicts.append(
                {
                    "date_drawn": lab.date_drawn.isoformat(),
                    "alt_level": lab.alt_level,
                    "ast_level": lab.ast_level,
                    "creatinine": lab.creatinine,
                    "ca_15_3": lab.ca_15_3,
                    "wbc_count": lab.wbc_count,
                }
            )

    new_lab_dict = {
        "date_drawn": lab_record.date_drawn.isoformat(),
        "alt_level": lab_record.alt_level,
        "ast_level": lab_record.ast_level,
        "creatinine": lab_record.creatinine,
        "ca_15_3": lab_record.ca_15_3,
        "wbc_count": lab_record.wbc_count,
    }

    baseline_dict = None
    if patient.baseline_profile:
        baseline_dict = {
            "target_organ_susceptibility_vector": patient.baseline_profile.target_organ_susceptibility_vector
        }

    # Execute Model B Sequence Inference via SentinelEngine
    engine = SentinelEngine.get_instance()
    risk_score, triage_flag, justification = engine.predict_risk(
        patient_id=id,
        new_lab_result=new_lab_dict,
        historical_labs=historical_dicts,
        baseline_profile=baseline_dict,
    )

    # Create RiskInference record
    risk_record = RiskInference(
        patient_id=id,
        lab_result_id=lab_record.id,
        calculated_metastasis_risk=risk_score,
        triage_flag=triage_flag,
        justification_text=justification,
        created_at=datetime.utcnow(),
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
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)),
):
    """Unit-safe ingestion validating against Analyte Registry, executing M3 adjudication,
    updating K2 sequential detector, verifying M5 clinical note, and enforcing no-dismissal invariant.
    """
    now = datetime.now(timezone.utc)
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)

    if payload.value <= 0.0 or math.isnan(payload.value) or math.isinf(payload.value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Observation value must be strictly positive (> 0.0), got {payload.value}.",
        )

    clean_code = payload.analyte_code.strip().lower()
    try:
        analyte = get_analyte(clean_code)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Analyte '{payload.analyte_code}' not found in registry.",
        )

    try:
        plausibility = check_plausibility(analyte.code, payload.value, payload.unit)
    except (InvalidUnitError, IncompatibleUnitsError, UnitConversionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unit validation failed: {str(exc)}. Silent unit coercion is forbidden.",
        )

    specimen_date = payload.specimen_collected_at or now
    if specimen_date.tzinfo is None:
        specimen_date = specimen_date.replace(tzinfo=timezone.utc)

    # 1. Fetch historical observations for this analyte to supply M3
    history_obs = db.execute(
        select(Observation)
        .where(Observation.patient_id == patient.id, Observation.analyte_code == analyte.code)
        .order_by(Observation.specimen_collected_at.asc())
    ).scalars().all()

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
        lab_changed=payload.lab_changed,
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
        "raw_value": payload.value,
        "raw_unit": payload.unit,
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
        laboratory_id=payload.laboratory_id,
        plausibility_status=plausibility.status.value,
        raw_value=payload.value,
        raw_unit=payload.unit,
        status="valid" if plausibility.is_valid else "flagged_implausible",
        created_at=now,
    )
    db.add(obs)
    db.flush()

    # 7. Save RiskAssessment
    risk_tier = (
        "high" if (m3_result["action"] == "escalate" or detector.alert)
        else "medium" if m3_result["action"] == "needs_repeat"
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
    alert_summary = None
    follow_up_summary = None

    if is_surprising:
        alert_type = (
            "biomarker_spike" if m3_result["action"] == "escalate"
            else "lab_error_repeat" if m3_result["action"] == "needs_repeat"
            else "sequential_divergence" if detector.alert
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
            FollowUpTaskType.REPEAT_SPECIMEN.value if m3_result["action"] == "needs_repeat"
            else FollowUpTaskType.IMAGING_REFERRAL.value if m3_result["action"] == "escalate"
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

        alert_summary = AlertSummary(
            id=alert.id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            trigger_reason=alert.trigger_reason,
            status=alert.status,
            created_at=alert.created_at,
        )
        follow_up_summary = FollowUpTaskSummary(
            id=task.id,
            task_type=task.task_type,
            status=task.status,
            due_date=task.due_date,
            escalation_level=task.escalation_level,
            notes=task.notes,
        )

    # 9. Cryptographic Audit Log
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="observation.ingest",
        resource_type="observation",
        resource_id=obs.id,
        details={
            "patient_id": patient.id,
            "analyte": analyte.code,
            "raw_value": payload.value,
            "raw_unit": payload.unit,
            "canonical_value": plausibility.canonical_value,
            "action": m3_result["action"],
            "has_alert": is_surprising,
        },
        timestamp=now,
    )

    db.commit()

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
    return [
        {
            "id": o.id,
            "patient_id": o.patient_id,
            "analyte_code": o.analyte_code,
            "value": o.value,
            "unit": o.unit,
            "raw_value": o.raw_value,
            "raw_unit": o.raw_unit,
            "plausibility_status": o.plausibility_status,
            "specimen_collected_at": o.specimen_collected_at.isoformat(),
            "status": o.status,
            "synthetic": patient.synthetic,
        }
        for o in obs_list
    ]


@router.post(
    "/{id}/consent",
    status_code=status.HTTP_201_CREATED,
    summary="Update or grant patient consent record",
)
def record_consent(
    id: str,
    consent_type: str = "surveillance_monitoring",
    granted: bool = True,
    scope: str = "full",
    expires_at: Optional[datetime] = None,
    withdrawn_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.ADMIN, UserRole.NURSE_CLERK)),
):
    """Record, revoke, or expire a patient consent record."""
    patient = db.execute(select(Patient).where(Patient.id == id)).scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient '{id}' not found.")

    now = datetime.now(timezone.utc)
    consent = ConsentRecord(
        patient_id=patient.id,
        consent_type=consent_type,
        granted=granted,
        granted_at=now,
        expires_at=expires_at,
        withdrawn_at=withdrawn_at,
        scope=scope,
    )
    db.add(consent)
    db.commit()
    return {
        "status": "success",
        "consent_id": consent.id,
        "patient_id": patient.id,
        "granted": consent.granted,
        "scope": consent.scope,
    }
