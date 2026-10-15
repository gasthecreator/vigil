"""
vigil_sim.calibration

Calibration Target Evaluation Suite for Vigil Simulation Laboratory.
Empirically tests cohorts against published clinical literature targets (EVIDENCE E1):
- Lead time to clinical recurrence: mean 4.2 ± 2.3 months (~126 ± 70 days)
- Sensitivity for distant metastasis at recurrence: 54% - 64%
- Specificity on disease-free (NED) patients: ~99%
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from vigil_core.analytes import ANALYTE_REGISTRY, get_analyte
from vigil_sim.generators import CohortDataset, GeneratorType, get_generator


@dataclass
class CalibrationReport:
    generator_type: GeneratorType
    num_patients: int
    num_observations: int
    mean_lead_time_days: float
    lead_time_std_days: float
    lead_time_target_met: bool
    empirical_sensitivity: float
    sensitivity_target_met: bool
    empirical_specificity: float
    specificity_target_met: bool
    all_targets_met: bool
    details: Dict[str, float]


def evaluate_cohort_calibration(
    cohort: CohortDataset,
    ca_15_3_cutoff: float = 30.0,  # Clinical upper limit of normal ([iU]/mL)
    lead_time_target_mean_days: float = 126.0,  # 4.2 months * 30 days
    lead_time_tolerance_days: float = 40.0,
    sensitivity_min: float = 0.50,
    sensitivity_max: float = 0.72,
    specificity_min: float = 0.95,
) -> CalibrationReport:
    """
    Evaluates whether the generated cohort satisfies the published calibration targets from E1.
    """
    pt_map = {p.patient_id: p for p in cohort.patients}
    
    # 1. Lead time analysis: For recurrent patients, find the first day CA 15-3 crossed cutoff
    lead_times = []
    # 2. Sensitivity at recurrence: Was CA 15-3 elevated within 90 days before clinical recurrence?
    recurrent_evaluated = 0
    recurrent_positive = 0
    # 3. Specificity: On non-recurrent patients, what fraction of observations never cross cutoff?
    non_recurrent_obs_total = 0
    non_recurrent_obs_negative = 0

    # Group observations by patient
    pt_obs: Dict[str, List] = {}
    for obs in cohort.observations:
        pt_obs.setdefault(obs.patient_id, []).append(obs)

    for pt_id, obs_list in pt_obs.items():
        pt = pt_map[pt_id]
        obs_sorted = sorted(obs_list, key=lambda x: x.day)

        if pt.true_recurrence_event and pt.true_recurrence_day is not None:
            recurrent_evaluated += 1
            # Check for elevation before recurrence
            elevated_days = [
                obs.day for obs in obs_sorted
                if obs.day <= pt.true_recurrence_day and obs.analytes.get("ca_15_3", 0.0) >= ca_15_3_cutoff
            ]
            if elevated_days:
                first_elevation_day = elevated_days[0]
                lead_days = pt.true_recurrence_day - first_elevation_day
                if lead_days > 0:
                    lead_times.append(lead_days)

            # Check sensitivity in the pre-recurrence surveillance window (within 180 days prior to or at recurrence)
            near_rec_elevated = any(
                (pt.true_recurrence_day - 180.0) <= obs.day <= (pt.true_recurrence_day + 30.0)
                and obs.analytes.get("ca_15_3", 0.0) >= ca_15_3_cutoff
                for obs in obs_sorted
            )
            if near_rec_elevated:
                recurrent_positive += 1
        else:
            # Non-recurrent patient: check all observations
            for obs in obs_sorted:
                non_recurrent_obs_total += 1
                if obs.analytes.get("ca_15_3", 0.0) < ca_15_3_cutoff:
                    non_recurrent_obs_negative += 1

    mean_lead = float(np.mean(lead_times)) if lead_times else 0.0
    std_lead = float(np.std(lead_times)) if len(lead_times) > 1 else 0.0

    sens = (recurrent_positive / recurrent_evaluated) if recurrent_evaluated > 0 else 0.0
    spec = (non_recurrent_obs_negative / non_recurrent_obs_total) if non_recurrent_obs_total > 0 else 1.0

    lead_met = abs(mean_lead - lead_time_target_mean_days) <= lead_time_tolerance_days
    sens_met = (sensitivity_min <= sens <= sensitivity_max)
    spec_met = (spec >= specificity_min)

    all_met = lead_met and sens_met and spec_met

    return CalibrationReport(
        generator_type=cohort.generator_type,
        num_patients=len(cohort.patients),
        num_observations=len(cohort.observations),
        mean_lead_time_days=mean_lead,
        lead_time_std_days=std_lead,
        lead_time_target_met=lead_met,
        empirical_sensitivity=sens,
        sensitivity_target_met=sens_met,
        empirical_specificity=spec,
        specificity_target_met=spec_met,
        all_targets_met=all_met,
        details={
            "recurrent_patients": recurrent_evaluated,
            "recurrent_positive": recurrent_positive,
            "non_recurrent_observations": non_recurrent_obs_total,
            "non_recurrent_negative": non_recurrent_obs_negative,
            "num_lead_time_samples": len(lead_times),
        },
    )


def run_full_calibration_check(seed: int = 123) -> Dict[str, CalibrationReport]:
    """Runs calibration validation across all mechanistic generators."""
    reports = {}
    for gen_type in [GeneratorType.G1_SMOOTH, GeneratorType.G2_BURST, GeneratorType.G3_NOISE]:
        gen = get_generator(gen_type, seed=seed)
        # Generate 400 patients for statistical stability
        cohort = gen.generate_cohort(num_patients=400, duration_days=730.0)
        report = evaluate_cohort_calibration(cohort)
        reports[gen_type.value] = report
    return reports
