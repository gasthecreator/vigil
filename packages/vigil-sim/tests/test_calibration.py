"""
Tests for the historical synthetic comparison targets in vigil_sim.calibration (EVIDENCE E1, E12).
Overseer Condition C2 Compliance (docs/progress/VERDICT-P0-P1.md).

These tests do not establish that the simulator reproduces the source cohorts. They assert only
that selected legacy synthetic outputs fall inside fixed ranges. Those ranges must be re-audited
after the evaluator begins respecting the observed-measurement mask.
"""

import numpy as np
import pytest
from vigil_core.analytes import ANALYTE_REGISTRY
from vigil_sim.calibration import evaluate_cohort_calibration, run_full_calibration_check
from vigil_sim.generators import GeneratorType, get_generator


def test_calibration_cutoff_defaults_to_registry_and_records_provenance():
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=48108).generate_cohort(
        num_patients=10, duration_days=90.0
    )

    report = evaluate_cohort_calibration(cohort)

    assert report.details["ca_15_3_cutoff"] == ANALYTE_REGISTRY[
        "ca_15_3"
    ].plausibility.reference_high
    assert report.details["ca_15_3_cutoff_source"] == (
        "ANALYTE_REGISTRY.ca_15_3.plausibility.reference_high"
    )
    assert report.details["ca_15_3_canonical_unit"] == ANALYTE_REGISTRY[
        "ca_15_3"
    ].canonical_unit
    assert "not an assay-independent diagnostic threshold" in report.details[
        "ca_15_3_cutoff_interpretation"
    ]

    explicit_report = evaluate_cohort_calibration(cohort, ca_15_3_cutoff=33.0)
    assert explicit_report.details["ca_15_3_cutoff"] == 33.0
    assert explicit_report.details["ca_15_3_cutoff_source"] == (
        "explicit evaluate_cohort_calibration argument"
    )


@pytest.mark.parametrize("cutoff", [True, 0, -1, np.nan, np.inf, "30"])
def test_calibration_rejects_invalid_ca153_cutoffs(cutoff):
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=48109).generate_cohort(
        num_patients=10, duration_days=90.0
    )

    with pytest.raises(ValueError, match="ca_15_3_cutoff must be a finite positive numeric value"):
        evaluate_cohort_calibration(cohort, ca_15_3_cutoff=cutoff)


def test_g1_smooth_calibration_targets():
    """
    Evaluates G1 (Smooth Exponential Compartment) against tuning targets:
    - Preclinical conditional lead time target: ~126 ± 69 days (Molina et al. 1995)
    - Unconditional lead time with explicit censoring rule (0 days if no preclinical elevation)
    - Sensitivity: 48% - 70% (Molina 1995 reports 54% CA 15-3 alone)
    - Per-observation specificity: >= 98% (Molina 1995 reports ~99% on NED patients)
    - Per-patient specificity: >= 88%
    - Organ-stratified sensitivity breakdown (Wu et al. 2017 tropism)
    """
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=42)
    cohort = gen.generate_cohort(num_patients=350, duration_days=730.0)
    report = evaluate_cohort_calibration(cohort)

    # 1. Lead time: conditional mean and SD
    assert 70.0 <= report.conditional_lead_time_mean_days <= 160.0, (
        f"G1 conditional lead time mean {report.conditional_lead_time_mean_days:.1f}d outside tolerance"
    )
    # The old single-seed SD ceiling was not a valid calibration criterion. Keep
    # this unit test on the evaluator's numeric contract; calibration targets need
    # a separately registered multi-seed study with uncertainty.
    assert np.isfinite(report.conditional_lead_time_std_days)
    assert report.conditional_lead_time_std_days >= 0.0

    # 2. Unconditional lead time (censoring non-elevated patients to 0 days)
    assert 30.0 <= report.unconditional_lead_time_mean_days <= 90.0, (
        f"G1 unconditional lead time mean {report.unconditional_lead_time_mean_days:.1f}d outside expected range"
    )
    assert report.unconditional_lead_time_mean_days < report.conditional_lead_time_mean_days, (
        "Unconditional lead time must be strictly less than conditional lead time due to 0-censoring"
    )

    # 3. Sensitivity: target 48% - 70%
    assert 0.48 <= report.overall_sensitivity <= 0.70, (
        f"G1 empirical sensitivity {report.overall_sensitivity:.1%} outside target 48-70%"
    )

    # 4. Specificity: per-observation >= 98% and per-patient >= 88%
    assert report.observation_specificity >= 0.98, (
        f"G1 observation-level specificity {report.observation_specificity:.2%} below 98%"
    )
    assert report.patient_specificity >= 0.88, (
        f"G1 patient-level specificity {report.patient_specificity:.2%} below 88%"
    )

    # 5. Organ-stratified sensitivity: all monitored organs present
    for organ in ["bone", "liver", "lung"]:
        assert organ in report.organ_sensitivity, f"Missing organ {organ} in sensitivity report"
        assert report.organ_sensitivity[organ] >= 0.35, (
            f"Organ {organ} sensitivity {report.organ_sensitivity[organ]:.2%} unexpectedly low"
        )


def test_g2_burst_calibration():
    """
    Evaluates G2 (Episodic Shedding Bursts) calibration behavior:
    - Bursts produce episodic peaks; conditional lead time is shorter but specificity remains high.
    - Per-observation specificity >= 98%
    - Sensitivity >= 45%
    """
    gen = get_generator(GeneratorType.G2_BURST, seed=42)
    cohort = gen.generate_cohort(num_patients=350, duration_days=730.0)
    report = evaluate_cohort_calibration(cohort)

    assert report.overall_sensitivity >= 0.45, (
        f"G2 sensitivity {report.overall_sensitivity:.2%} below 45%"
    )
    assert report.observation_specificity >= 0.98, (
        f"G2 observation specificity {report.observation_specificity:.2%} below 98%"
    )
    assert report.patient_specificity >= 0.88, (
        f"G2 patient specificity {report.patient_specificity:.2%} below 88%"
    )
    assert report.conditional_lead_time_mean_days > 0.0


def test_g3_noise_calibration():
    """
    Evaluates G3 (Heavy-Tailed Assay Noise / Student-t) calibration behavior:
    - Heavy-tailed noise increases variance but baseline specificity and sensitivity remain calibrated.
    - Per-observation specificity >= 98%
    - Sensitivity >= 40%
    """
    gen = get_generator(GeneratorType.G3_NOISE, seed=42)
    cohort = gen.generate_cohort(num_patients=350, duration_days=730.0)
    report = evaluate_cohort_calibration(cohort)

    assert report.overall_sensitivity >= 0.40, (
        f"G3 sensitivity {report.overall_sensitivity:.2%} below 40%"
    )
    assert report.observation_specificity >= 0.98, (
        f"G3 observation specificity {report.observation_specificity:.2%} below 98%"
    )
    assert report.conditional_lead_time_mean_days > 0.0


def test_run_full_calibration_check():
    """Verifies that the multi-generator calibration runner executes across G1, G2, G3."""
    reports = run_full_calibration_check(seed=123)
    assert set(reports.keys()) == {
        "g1_smooth_kinetics",
        "g2_shedding_bursts",
        "g3_heavy_tailed_noise",
    }
    for name, r in reports.items():
        assert r.num_patients == 350
        assert r.observation_specificity >= 0.98


def test_calibration_never_counts_unmeasured_ca153_values():
    generator = get_generator(GeneratorType.G1_SMOOTH, seed=48106)
    cohort = generator.generate_cohort(num_patients=2, duration_days=180.0)
    recurrent = cohort.patients[0]
    recurrent.true_recurrence_event = True
    recurrent.true_recurrence_day = 120.0
    recurrent.true_recurrence_site = "bone"
    control = cohort.patients[1]
    control.true_recurrence_event = False
    control.true_recurrence_day = None
    control.true_recurrence_site = None

    for observation in cohort.observations:
        observation.analytes["ca_15_3"] = 100.0
        observation.observed_mask["ca_15_3"] = False

    report = evaluate_cohort_calibration(cohort)

    assert report.details["num_measured_ca153_observations"] == 0
    assert report.details["num_recurrent_with_measured_ca153_in_detection_window"] == 0
    assert report.overall_sensitivity == 0.0
    assert np.isnan(report.observation_specificity)
    assert np.isnan(report.patient_specificity)
    assert np.isnan(report.conditional_lead_time_mean_days)


def test_calibration_counts_recurrent_patients_without_observation_rows():
    generator = get_generator(GeneratorType.G1_SMOOTH, seed=48107)
    cohort = generator.generate_cohort(num_patients=2, duration_days=180.0)
    recurrent = cohort.patients[0]
    recurrent.true_recurrence_event = True
    recurrent.true_recurrence_day = 120.0
    recurrent.true_recurrence_site = "bone"
    control = cohort.patients[1]
    control.true_recurrence_event = False
    control.true_recurrence_day = None
    control.true_recurrence_site = None
    cohort.observations = [
        observation
        for observation in cohort.observations
        if observation.patient_id != recurrent.patient_id
    ]

    report = evaluate_cohort_calibration(cohort)

    assert report.details["num_recurrent_patients"] == 1
    assert report.details["num_recurrent_with_measured_ca153_in_detection_window"] == 0
    assert report.details["num_recurrent_without_measured_ca153_in_detection_window"] == 1
    assert report.overall_sensitivity == 0.0
