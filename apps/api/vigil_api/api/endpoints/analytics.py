"""API endpoints for population facts and synthetic demo data.

Remediates Defect A6: Gated demo seeding endpoint for local environment only.
"""

import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from vigil_api import silent_mode
from vigil_api.auth import require_roles
from vigil_api.config import settings
from vigil_api.consent import has_active_consent
from vigil_api.database import get_db
from vigil_api.ml.synthetic_generator import generate_longitudinal_labs, generate_patient_baseline
from vigil_api.models.patient import BaselineProfile, LabResult, Patient
from vigil_api.models.v2 import User, UserRole

router = APIRouter()


@router.get("/cohort")
def get_cohort_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CLINICIAN, UserRole.QUALITY_LEAD, UserRole.ADMIN)
    ),
):
    """Provides cohort size and explicit unavailable model-metric status.

    Restricted to clinical/quality roles and computed only over patients with active consent.
    """
    patients = [p for p in db.query(Patient).all() if has_active_consent(p.id, db, current_user)]
    total_patients = len(patients)
    return {
        "is_synthetic": settings.IS_SYNTHETIC_DATA,
        "disclaimer": settings.DISCLAIMER,
        "total_patients": total_patients,
        "risk_metrics_status": "unavailable",
        "risk_metrics_message": "No validated recurrence-risk model or supported M1 organ prior is enabled.",
        "scored_patients": None,
        "critical_alerts": None,
        "watch_cases": None,
        "stable_cases": None,
        "average_cohort_risk": None,
        "organ_tropism_distribution": None,
    }


@router.post("/seed-demo-cohort", status_code=status.HTTP_201_CREATED)
def seed_demo_cohort(
    num_patients: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Seeds explicitly synthetic demo patients and lab trajectories.

    Gated strictly to local development environments and admin role per Condition S5-2.
    """
    if settings.ENVIRONMENT != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seeding endpoint is disabled outside the local development environment.",
        )
    silent_mode.block_in_silent_mode("Demo cohort seeding")

    created_ids = []

    for i in range(num_patients):
        will_recur = i in [0, 1, 4]

        raw_patient = generate_patient_baseline()
        patient = Patient(
            age=raw_patient["age"],
            status="active",
            synthetic=True,
            created_at=raw_patient["created_at"],
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        created_ids.append(patient.id)

        baseline = BaselineProfile(
            patient_id=patient.id,
            tumor_stage=raw_patient["tumor_stage"],
            er_status=raw_patient["er_status"],
            pr_status=raw_patient["pr_status"],
            her2_status=raw_patient["her2_status"],
            has_hypertension=raw_patient["has_hypertension"],
            renal_history=raw_patient["renal_history"],
            target_organ_susceptibility_vector=None,
        )
        db.add(baseline)
        db.commit()

        synthetic_labs = generate_longitudinal_labs(
            raw_patient,
            metastasis_occurred=will_recur,
            num_visits=random.randint(4, 7),
        )

        for lab_data in synthetic_labs:
            lab_record = LabResult(
                patient_id=patient.id,
                date_drawn=lab_data["date_drawn"],
                alt_level=lab_data["alt_level"],
                ast_level=lab_data["ast_level"],
                creatinine=lab_data["creatinine"],
                ca_15_3=lab_data["ca_15_3"],
                wbc_count=lab_data["wbc_count"],
            )
            db.add(lab_record)
            db.commit()
        db.commit()

    return {
        "is_synthetic": True,
        "message": f"Recorded synthetic demo data for {len(created_ids)} patients; no recurrence-risk estimates were generated.",
        "patient_ids": created_ids,
    }
