"""
Sentinel Synthetic Data Generator
Generates realistic cohorts of breast cancer patients with baseline pathology
and multi-year longitudinal biomarker surveillance trajectories, including
biologically grounded metastatic recurrence anomaly cascades.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd


def generate_patient_baseline(patient_id: str | None = None) -> Dict[str, Any]:
    """Generates a realistic clinical baseline for a breast cancer patient."""
    if patient_id is None:
        patient_id = str(uuid.uuid4())

    age = int(np.clip(np.random.normal(57.5, 10.5), 29, 86))

    # Tumor stage distribution: Stage 1 (30%), 2 (40%), 3 (22%), 4 (8%)
    stage_choice = np.random.choice([1, 2, 3, 4], p=[0.30, 0.40, 0.22, 0.08])

    # Breast cancer molecular subtypes
    # Luminal A (ER+, PR+, HER2-): 60%
    # Luminal B (ER+, HER2+): 10%
    # HER2-Enriched (ER-, PR-, HER2+): 15%
    # Triple Negative (ER-, PR-, HER2-): 15%
    subtype_rand = np.random.random()
    if subtype_rand < 0.60:
        er, pr, her2 = True, True, False
    elif subtype_rand < 0.70:
        er, pr, her2 = True, True, True
    elif subtype_rand < 0.85:
        er, pr, her2 = False, False, True
    else:
        er, pr, her2 = False, False, False

    # Comorbidities
    has_hypertension = bool(np.random.random() < (0.32 + 0.005 * (age - 50)))
    renal_history = bool(np.random.random() < (0.10 + (0.08 if has_hypertension else 0.0)))

    # Ground-truth biological organ tropism vector based on clinical oncology literature
    # Bone, Liver, Lung, Brain
    if er and not her2:  # Luminal A -> high bone tropism
        raw_tropism = [
            np.random.normal(0.60, 0.06),  # Bone
            np.random.normal(0.18, 0.04),  # Liver
            np.random.normal(0.14, 0.03),  # Lung
            np.random.normal(0.08, 0.02),  # Brain
        ]
    elif her2:  # HER2+ -> visceral hepatic and CNS predilection
        raw_tropism = [
            np.random.normal(0.25, 0.05),  # Bone
            np.random.normal(0.42, 0.07),  # Liver
            np.random.normal(0.15, 0.04),  # Lung
            np.random.normal(0.18, 0.05),  # Brain
        ]
    else:  # Triple Negative -> aggressive visceral (Lung, Liver, Brain)
        raw_tropism = [
            np.random.normal(0.18, 0.04),  # Bone
            np.random.normal(0.35, 0.06),  # Liver
            np.random.normal(0.32, 0.06),  # Lung
            np.random.normal(0.15, 0.04),  # Brain
        ]

    # Stage modifier: later stages elevate liver & brain systemic risk
    if stage_choice >= 3:
        raw_tropism[1] *= 1.2
        raw_tropism[3] *= 1.25

    # Softmax normalization
    raw_arr = np.maximum(np.array(raw_tropism), 0.01)
    norm_vector = raw_arr / np.sum(raw_arr)

    organ_vector = {
        "bone": float(round(norm_vector[0], 4)),
        "liver": float(round(norm_vector[1], 4)),
        "lung": float(round(norm_vector[2], 4)),
        "brain": float(round(norm_vector[3], 4)),
    }

    return {
        "patient_id": patient_id,
        "age": age,
        "tumor_stage": int(stage_choice),
        "er_status": bool(er),
        "pr_status": bool(pr),
        "her2_status": bool(her2),
        "has_hypertension": has_hypertension,
        "renal_history": renal_history,
        "target_organ_susceptibility_vector": organ_vector,
        "created_at": datetime.now() - timedelta(days=random.randint(400, 1800)),
        "status": "active",
    }


def generate_longitudinal_labs(
    baseline: Dict[str, Any],
    metastasis_occurred: bool = False,
    num_visits: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Generates a sequence of routine longitudinal lab visits over 1 to 5 years.
    If metastasis_occurred is True, injects progressive biomarker acceleration anomalies
    aligned with the primary organ susceptibility.
    """
    if num_visits is None:
        num_visits = random.randint(4, 18)

    patient_id = baseline["patient_id"]
    renal_hist = baseline["renal_history"]
    organ_vec = baseline["target_organ_susceptibility_vector"]

    # Start date 1-4 years ago
    start_date = baseline["created_at"] + timedelta(days=random.randint(14, 45))
    current_date = start_date

    labs = []
    # Base physiological levels for this patient
    base_alt = np.random.normal(21.0, 4.0)
    base_ast = base_alt * np.random.normal(0.92, 0.08)
    base_cr = np.random.normal(1.45, 0.2) if renal_hist else np.random.normal(0.82, 0.12)
    base_ca153 = np.random.normal(17.5, 3.2)
    base_wbc = np.random.normal(6.6, 1.1)

    # Determine inflection visit for recurring patients (last 2 to 4 visits)
    anomaly_onset_idx = num_visits - random.randint(2, min(4, num_visits - 1)) if metastasis_occurred else 999

    for visit_idx in range(num_visits):
        # Time gap between draws: 60 to 120 days
        current_date += timedelta(days=random.randint(65, 115))

        # Baseline noise
        alt = np.clip(base_alt + np.random.normal(0, 2.8), 8.0, 50.0)
        ast = np.clip(base_ast + np.random.normal(0, 2.5), 8.0, 50.0)
        cr = np.clip(base_cr + np.random.normal(0, 0.08), 0.45, 3.5)
        ca153 = np.clip(base_ca153 + np.random.normal(0, 1.8), 8.0, 32.0)
        wbc = np.clip(base_wbc + np.random.normal(0, 0.6), 3.5, 12.0)

        # Recurrence progression injection
        is_anomaly_step = visit_idx >= anomaly_onset_idx
        anomaly_severity = 0.0

        if is_anomaly_step:
            step_into_anomaly = visit_idx - anomaly_onset_idx + 1
            anomaly_severity = step_into_anomaly / (num_visits - anomaly_onset_idx)

            # Progressive tumor marker doubling
            ca153 += 25.0 * (step_into_anomaly ** 1.6) + np.random.normal(0, 3.0)

            # Hepatic involvement
            if organ_vec["liver"] >= 0.28:
                alt += 45.0 * (step_into_anomaly ** 1.4) + np.random.normal(0, 6.0)
                ast += 38.0 * (step_into_anomaly ** 1.4) + np.random.normal(0, 5.0)

            # Systemic inflammatory response
            wbc += 2.2 * step_into_anomaly + np.random.normal(0, 0.5)

        labs.append({
            "id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "date_drawn": current_date,
            "alt_level": float(round(alt, 1)),
            "ast_level": float(round(ast, 1)),
            "creatinine": float(round(cr, 2)),
            "ca_15_3": float(round(ca153, 1)),
            "wbc_count": float(round(wbc, 1)),
            "is_anomaly": is_anomaly_step,
            "anomaly_severity": float(round(anomaly_severity, 2)),
        })

    return labs


def generate_synthetic_cohort(
    num_patients: int = 500,
    recurrence_rate: float = 0.28,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates 500 patient records and their longitudinal lab trajectories.
    Returns: (patients_list, all_labs_list)
    """
    patients = []
    all_labs = []

    for i in range(num_patients):
        patient = generate_patient_baseline()
        # Higher stage patients have higher probability of recurrence
        stage_risk = 0.12 * patient["tumor_stage"]
        will_recur = bool(np.random.random() < min(0.65, recurrence_rate + stage_risk - 0.15))
        patient["metastasis_occurred"] = will_recur

        labs = generate_longitudinal_labs(patient, metastasis_occurred=will_recur)
        patient["lab_count"] = len(labs)

        patients.append(patient)
        all_labs.extend(labs)

    return patients, all_labs


if __name__ == "__main__":
    np.random.seed(42)
    random.seed(42)
    print("Generating synthetic cohort of 500 patients...")
    cohort_patients, cohort_labs = generate_synthetic_cohort(num_patients=500)
    print(f"Generated {len(cohort_patients)} patients and {len(cohort_labs)} longitudinal lab draws.")
    recurrences = sum(1 for p in cohort_patients if p["metastasis_occurred"])
    print(f"Metastatic recurrence rate: {recurrences}/{len(cohort_patients)} ({recurrences/len(cohort_patients)*100:.1f}%)")
