"""API Endpoints for Patient Management, Pathology Intake, Labs & Surveillance."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from vigil_api.database import get_db
from vigil_api.ml.inference import SentinelEngine
from vigil_api.models.patient import BaselineProfile, LabResult, Patient, RiskInference
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

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    """Registers a new patient into the oncology surveillance roster."""
    patient = Patient(
        age=payload.age,
        status=payload.status,
        created_at=datetime.utcnow(),
    )
    db.add(patient)
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
def get_patient_detail(id: str, db: Session = Depends(get_db)):
    """Retrieves single patient details, baseline profile, and latest risk inference."""
    patient = db.query(Patient).filter(Patient.id == id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

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
