"""
vigil_eval.lead_time

Preclinical Lead-Time and Overdetection Evaluation Module.
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.1) and docs/ML_PROGRAM.md §4.5, §9.

Measures:
1. Conditional Lead-Time: Preclinical detection lead time among recurrent patients with positive alert.
2. Unconditional Lead-Time: Lead time across all recurrent cases with non-detection censored at 0.
3. Overdetection Fraction: Fraction of alerts generated on indolent or disease-free cases.
4. Surveillance Alert Burden: False alarm rate per 100 patient-years.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd


@dataclass
class LeadTimeOverdetectionReport:
    conditional_mean_days: float
    conditional_std_days: float
    conditional_median_days: float
    unconditional_mean_days: float
    recurrence_detection_rate: float
    overdetection_rate: float
    alert_burden_per_100_pt_years: float
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conditional_lead_time_days": f"{self.conditional_mean_days:.1f} ± {self.conditional_std_days:.1f}",
            "conditional_median_days": round(self.conditional_median_days, 1),
            "unconditional_mean_days": round(self.unconditional_mean_days, 1),
            "recurrence_detection_rate": round(self.recurrence_detection_rate, 4),
            "overdetection_rate": round(self.overdetection_rate, 4),
            "alert_burden_per_100_pt_years": round(self.alert_burden_per_100_pt_years, 2),
        }


def evaluate_lead_time_and_overdetection(
    patient_df: pd.DataFrame,
    observation_df: pd.DataFrame,
    alert_col: str = "alert_triggered",
    patient_id_col: str = "patient_id",
    day_col: str = "day",
) -> LeadTimeOverdetectionReport:
    """
    Evaluates preclinical lead time and overdetection from longitudinal alerts.

    Parameters:
        patient_df: Patient registry containing:
            - patient_id
            - true_recurrence_event (bool)
            - true_recurrence_day (float or None)
            - is_indolent (bool)
        observation_df: Observation rows containing:
            - patient_id
            - day
            - alert_triggered (bool or int)
    """
    pt_map = {row[patient_id_col]: row for _, row in patient_df.iterrows()}

    conditional_leads: List[float] = []
    unconditional_leads: List[float] = []

    total_recurrent = 0
    detected_recurrent = 0

    total_alerted_patients = set()
    overdetected_patients = set()

    total_surveillance_days = 0.0

    # Group observations by patient
    for pt_id, obs_group in observation_df.groupby(patient_id_col):
        obs_sorted = obs_group.sort_values(day_col)
        pt = pt_map.get(pt_id)
        if pt is None:
            continue

        # Follow-up duration for patient
        pt_days = float(obs_sorted[day_col].max() - obs_sorted[day_col].min())
        total_surveillance_days += pt_days

        is_rec = bool(pt.get("true_recurrence_event", False))
        rec_day = pt.get("true_recurrence_day")
        is_indolent = bool(pt.get("is_indolent", False))

        # Check for first alert
        alert_rows = obs_sorted[obs_sorted[alert_col] == 1]
        has_alert = len(alert_rows) > 0
        first_alert_day = float(alert_rows[day_col].iloc[0]) if has_alert else None

        if has_alert:
            total_alerted_patients.add(pt_id)
            if not is_rec or is_indolent:
                overdetected_patients.add(pt_id)

        if is_rec and rec_day is not None and not np.isnan(rec_day):
            total_recurrent += 1
            if first_alert_day is not None and first_alert_day < rec_day:
                lead = rec_day - first_alert_day
                conditional_leads.append(lead)
                unconditional_leads.append(lead)
                detected_recurrent += 1
            else:
                # Censoring rule: 0 days if not detected prior to clinical recurrence
                unconditional_leads.append(0.0)

    cond_mean = float(np.mean(conditional_leads)) if conditional_leads else float("nan")
    cond_std = float(np.std(conditional_leads)) if len(conditional_leads) > 1 else float("nan")
    cond_median = float(np.median(conditional_leads)) if conditional_leads else float("nan")
    uncond_mean = float(np.mean(unconditional_leads)) if unconditional_leads else float("nan")

    detection_rate = (
        float(detected_recurrent / total_recurrent) if total_recurrent > 0 else float("nan")
    )
    overdetection_rate = (
        float(len(overdetected_patients) / len(total_alerted_patients))
        if total_alerted_patients
        else float("nan")
    )

    pt_years = total_surveillance_days / 365.25
    alert_burden = (
        float(len(total_alerted_patients) / (pt_years / 100.0))
        if pt_years > 0
        else float("nan")
    )

    return LeadTimeOverdetectionReport(
        conditional_mean_days=cond_mean,
        conditional_std_days=cond_std,
        conditional_median_days=cond_median,
        unconditional_mean_days=uncond_mean,
        recurrence_detection_rate=detection_rate,
        overdetection_rate=overdetection_rate,
        alert_burden_per_100_pt_years=alert_burden,
        details={
            "n_recurrent_evaluated": total_recurrent,
            "n_recurrent_detected": detected_recurrent,
            "n_alerted_patients": len(total_alerted_patients),
            "n_overdetected_patients": len(overdetected_patients),
            "total_surveillance_patient_years": round(pt_years, 2),
            "metrics_defined": bool(
                np.all(
                    np.isfinite(
                        [cond_mean, cond_std, cond_median, uncond_mean, detection_rate,
                         overdetection_rate, alert_burden]
                    )
                )
            ),
        },
    )
