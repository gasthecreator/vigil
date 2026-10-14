"""API Endpoints for Population Analytics and Demo Cohort Seeding."""

from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from sentinel.database import get_db
from sentinel.models.patient import Patient, BaselineProfile, LabResult, RiskInference
from sentinel.ml.synthetic_generator import generate_patient_baseline, generate_longitudinal_labs
from sentinel.ml.inference import SentinelEngine

router = APIRouter()


@router.get("/cohort")
def get_cohort_analytics(db: Session = Depends(get_db)):
    """Provides population-level surveillance KPIs and organ tropism distribution."""
    total_patients = db.query(Patient).count()

    patients = db.query(Patient).all()
    critical_alerts = 0
    watch_cases = 0
    stable_cases = 0
    total_risk = 0.0
    scored_count = 0

    organ_aggregates = {"bone": 0.0, "liver": 0.0, "lung": 0.0, "brain": 0.0}
    baseline_count = 0

    for p in patients:
        latest = (
            db.query(RiskInference)
            .filter(RiskInference.patient_id == p.id)
            .order_by(desc(RiskInference.created_at))
            .first()
        )
        if latest:
            scored_count += 1
            risk = latest.calculated_metastasis_risk
            total_risk += risk
            if risk >= 0.75:
                critical_alerts += 1
            elif risk >= 0.40:
                watch_cases += 1
            else:
                stable_cases += 1

        if p.baseline_profile and p.baseline_profile.target_organ_susceptibility_vector:
            baseline_count += 1
            vec = p.baseline_profile.target_organ_susceptibility_vector
            for k in organ_aggregates:
                organ_aggregates[k] += vec.get(k, 0.0)

    avg_risk = round(total_risk / max(scored_count, 1), 3)
    avg_organs = {
        k: round(v / max(baseline_count, 1), 3) for k, v in organ_aggregates.items()
    }

    return {
        "total_patients": total_patients,
        "scored_patients": scored_count,
        "critical_alerts": critical_alerts,
        "watch_cases": watch_cases,
        "stable_cases": stable_cases,
        "average_cohort_risk": avg_risk,
        "organ_tropism_distribution": avg_organs,
    }


@router.post("/seed-demo-cohort", status_code=status.HTTP_201_CREATED)
def seed_demo_cohort(num_patients: int = 12, db: Session = Depends(get_db)):
    """
    Seeds a rich clinical demo cohort with diverse risk profiles:
    normal surveillance trajectories, moderate velocity rises, and critical recurrence anomalies.
    """
    engine = SentinelEngine.get_instance()
    created_ids = []

    for i in range(num_patients):
        # 30% recurrences
        will_recur = i in [0, 1, 4]  # First couple patients are critical alerts for high visibility

        raw_patient = generate_patient_baseline()
        patient = Patient(
            age=raw_patient["age"],
            status="active",
            created_at=raw_patient["created_at"],
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        created_ids.append(patient.id)

        # Baseline Model A execution
        model_a_in = {
            "age": patient.age,
            "tumor_stage": raw_patient["tumor_stage"],
            "er_status": raw_patient["er_status"],
            "pr_status": raw_patient["pr_status"],
            "her2_status": raw_patient["her2_status"],
            "has_hypertension": raw_patient["has_hypertension"],
            "renal_history": raw_patient["renal_history"],
        }
        organ_vector = engine.predict_baseline_susceptibility(model_a_in)

        baseline = BaselineProfile(
            patient_id=patient.id,
            tumor_stage=raw_patient["tumor_stage"],
            er_status=raw_patient["er_status"],
            pr_status=raw_patient["pr_status"],
            her2_status=raw_patient["her2_status"],
            has_hypertension=raw_patient["has_hypertension"],
            renal_history=raw_patient["renal_history"],
            target_organ_susceptibility_vector=organ_vector,
        )
        db.add(baseline)
        db.commit()

        # Generate 4-8 longitudinal labs
        synthetic_labs = generate_longitudinal_labs(
            raw_patient,
            metastasis_occurred=will_recur,
            num_visits=random.randint(4, 7),
        )

        hist_dicts = []
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
            db.refresh(lab_record)

            new_dict = {
                "date_drawn": lab_record.date_drawn.isoformat(),
                "alt_level": lab_record.alt_level,
                "ast_level": lab_record.ast_level,
                "creatinine": lab_record.creatinine,
                "ca_15_3": lab_record.ca_15_3,
                "wbc_count": lab_record.wbc_count,
            }

            risk, flag, justification = engine.predict_risk(
                patient_id=patient.id,
                new_lab_result=new_dict,
                historical_labs=hist_dicts,
                baseline_profile={"target_organ_susceptibility_vector": organ_vector},
            )

            risk_record = RiskInference(
                patient_id=patient.id,
                lab_result_id=lab_record.id,
                calculated_metastasis_risk=risk,
                triage_flag=flag,
                justification_text=justification,
                created_at=lab_record.date_drawn + timedelta(hours=2),
            )
            db.add(risk_record)
            db.commit()

            hist_dicts.append(new_dict)

    return {"message": f"Successfully seeded {len(created_ids)} patients with full trajectories.", "patient_ids": created_ids}
