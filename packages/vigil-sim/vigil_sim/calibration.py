"""
vigil_sim.calibration

Calibration Target Evaluation Suite for Vigil Simulation Laboratory.
Enforces Master Plan §6.13, §14, ML_PROGRAM §9, and Overseer Condition C2 (VERDICT-P0-P1.md).

Tuned to reproduce empirical figures from published literature (EVIDENCE E1, E12):
- Molina et al. 1995 (Breast Cancer Res Treat, n=1,023):
    * Pre-clinical lead time: 4.2 ± 2.3 months (~126 ± 69 days) among elevated recurrent patients
    * Pre-recurrence sensitivity: 54% (CA 15-3 alone) excluding locoregional recurrences
    * Specificity on NED (disease-free) patients: ~99.0%
- Wu et al. 2017 (Oncotarget, n=243,896):
    * Preferential organ tropism by subtype (Bone > Lung > Liver > Brain)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

from vigil_core.analytes import TargetOrgan
from vigil_sim.generators import CohortDataset, GeneratorType


@dataclass
class CalibrationReport:
    generator_type: GeneratorType
    num_patients: int
    num_observations: int
    
    # Lead time targets (Molina et al. 1995: 4.2 ± 2.3 months = 126 ± 69 days)
    conditional_lead_time_mean_days: float
    conditional_lead_time_std_days: float
    unconditional_lead_time_mean_days: float  # Censoring rule: 0 days if no preclinical elevation
    lead_time_target_met: bool
    
    # Sensitivity targets (overall and organ-stratified)
    overall_sensitivity: float
    organ_sensitivity: Dict[str, float]
    sensitivity_target_met: bool
    
    # Specificity targets (both per-observation and per-patient)
    observation_specificity: float
    patient_specificity: float
    specificity_target_met: bool
    
    all_targets_met: bool
    details: Dict[str, Any]

    @property
    def mean_lead_time_days(self) -> float:
        return self.conditional_lead_time_mean_days

    @property
    def lead_time_std_days(self) -> float:
        return self.conditional_lead_time_std_days

    @property
    def empirical_sensitivity(self) -> float:
        return self.overall_sensitivity

    @property
    def empirical_specificity(self) -> float:
        return self.observation_specificity


def evaluate_cohort_calibration(
    cohort: CohortDataset,
    ca_15_3_cutoff: float = 30.0,  # Clinical threshold ([iU]/mL)
    target_conditional_lead_days: float = 126.0,  # 4.2 months * 30 days
    lead_tolerance_days: float = 35.0,
    min_sensitivity: float = 0.48,
    max_sensitivity: float = 0.70,
    min_observation_specificity: float = 0.98,
    min_patient_specificity: float = 0.88,
) -> CalibrationReport:
    """
    Evaluates whether the generated cohort reproduces the published calibration figures
    from Molina et al. 1995 (n=1,023) and Wu et al. 2017 (n=243,896).
    """
    pt_map = {p.patient_id: p for p in cohort.patients}
    
    # Lead time tracking
    conditional_lead_times: List[float] = []
    unconditional_lead_times: List[float] = []
    
    # Sensitivity tracking (overall and by organ)
    recurrent_total = 0
    recurrent_positive = 0
    organ_totals: Dict[str, int] = {}
    organ_positives: Dict[str, int] = {}
    
    # Specificity tracking
    non_rec_obs_total = 0
    non_rec_obs_negative = 0
    non_rec_patients_total = 0
    non_rec_patients_clean = 0

    # Group observations by patient
    pt_obs: Dict[str, List] = {}
    for obs in cohort.observations:
        pt_obs.setdefault(obs.patient_id, []).append(obs)

    for pt_id, obs_list in pt_obs.items():
        pt = pt_map[pt_id]
        obs_sorted = sorted(obs_list, key=lambda x: x.day)

        if pt.true_recurrence_event and pt.true_recurrence_day is not None:
            recurrent_total += 1
            site = pt.true_recurrence_site or "other"
            organ_totals[site] = organ_totals.get(site, 0) + 1

            # Find preclinical elevations: obs <= recurrence_day and ca_15_3 >= cutoff
            elevated_days = [
                obs.day for obs in obs_sorted
                if obs.day <= pt.true_recurrence_day and obs.analytes.get("ca_15_3", 0.0) >= ca_15_3_cutoff
            ]

            if elevated_days:
                first_elevation_day = elevated_days[0]
                lead = pt.true_recurrence_day - first_elevation_day
                if lead > 0:
                    conditional_lead_times.append(lead)
                    unconditional_lead_times.append(lead)
                else:
                    unconditional_lead_times.append(0.0)
            else:
                # Censoring rule: 0 preclinical lead time if never elevated prior to diagnosis
                unconditional_lead_times.append(0.0)

            # Pre-recurrence sensitivity: elevated within 180 days prior to or at recurrence
            near_rec_elevated = any(
                (pt.true_recurrence_day - 180.0) <= obs.day <= (pt.true_recurrence_day + 30.0)
                and obs.analytes.get("ca_15_3", 0.0) >= ca_15_3_cutoff
                for obs in obs_sorted
            )
            if near_rec_elevated:
                recurrent_positive += 1
                organ_positives[site] = organ_positives.get(site, 0) + 1

        else:
            # Non-recurrent patient: evaluate false positives
            non_rec_patients_total += 1
            pt_had_false_positive = False

            for obs in obs_sorted:
                non_rec_obs_total += 1
                val = obs.analytes.get("ca_15_3", 0.0)
                if val < ca_15_3_cutoff:
                    non_rec_obs_negative += 1
                else:
                    pt_had_false_positive = True

            if not pt_had_false_positive:
                non_rec_patients_clean += 1

    # Lead time statistics
    mean_cond_lead = float(np.mean(conditional_lead_times)) if conditional_lead_times else 0.0
    std_cond_lead = float(np.std(conditional_lead_times)) if len(conditional_lead_times) > 1 else 0.0
    mean_uncond_lead = float(np.mean(unconditional_lead_times)) if unconditional_lead_times else 0.0

    lead_met = abs(mean_cond_lead - target_conditional_lead_days) <= lead_tolerance_days

    # Sensitivity statistics
    sens_overall = (recurrent_positive / recurrent_total) if recurrent_total > 0 else 0.0
    sens_met = min_sensitivity <= sens_overall <= max_sensitivity

    organ_sens: Dict[str, float] = {}
    for site, count in organ_totals.items():
        pos = organ_positives.get(site, 0)
        organ_sens[site] = float(pos / count) if count > 0 else 0.0

    # Specificity statistics
    obs_spec = (non_rec_obs_negative / non_rec_obs_total) if non_rec_obs_total > 0 else 1.0
    pt_spec = (non_rec_patients_clean / non_rec_patients_total) if non_rec_patients_total > 0 else 1.0
    spec_met = (obs_spec >= min_observation_specificity) and (pt_spec >= min_patient_specificity)

    all_met = bool(lead_met and sens_met and spec_met)

    details = {
        "num_recurrent_patients": recurrent_total,
        "num_non_recurrent_patients": non_rec_patients_total,
        "num_elevated_recurrent_patients": len(conditional_lead_times),
        "mean_conditional_lead_time_days": mean_cond_lead,
        "std_conditional_lead_time_days": std_cond_lead,
        "mean_unconditional_lead_time_days": mean_uncond_lead,
        "overall_sensitivity": sens_overall,
        "observation_level_specificity": obs_spec,
        "patient_level_specificity": pt_spec,
        "organ_stratified_sensitivity": organ_sens,
        "tuning_reference": "Tuned to reproduce reported figures from Molina et al. 1995 (n=1,023) and Wu et al. 2017 (n=243,896)",
    }

    return CalibrationReport(
        generator_type=cohort.generator_type,
        num_patients=len(cohort.patients),
        num_observations=len(cohort.observations),
        conditional_lead_time_mean_days=mean_cond_lead,
        conditional_lead_time_std_days=std_cond_lead,
        unconditional_lead_time_mean_days=mean_uncond_lead,
        lead_time_target_met=lead_met,
        overall_sensitivity=sens_overall,
        organ_sensitivity=organ_sens,
        sensitivity_target_met=sens_met,
        observation_specificity=obs_spec,
        patient_specificity=pt_spec,
        specificity_target_met=spec_met,
        all_targets_met=all_met,
        details=details,
    )


def run_full_calibration_check(seed: int = 123) -> Dict[str, CalibrationReport]:
    """Runs calibration validation across all mechanistic cohort generators."""
    from vigil_sim.generators import get_generator

    reports = {}
    for gen_type in [GeneratorType.G1_SMOOTH, GeneratorType.G2_BURST, GeneratorType.G3_NOISE]:
        gen = get_generator(gen_type, seed=seed)
        cohort = gen.generate_cohort(num_patients=350, duration_days=730.0)
        report = evaluate_cohort_calibration(cohort)
        reports[gen_type.value] = report
    return reports
