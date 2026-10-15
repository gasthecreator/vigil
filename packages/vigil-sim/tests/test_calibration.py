"""
Tests for vigil_sim.calibration: Verification of published clinical targets (EVIDENCE E1).
"""

import pytest

from vigil_sim.calibration import evaluate_cohort_calibration
from vigil_sim.generators import GeneratorType, get_generator


def test_g1_smooth_calibration_targets():
    # Evaluate G1 on 350 patients for stable sample statistics
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=42)
    cohort = gen.generate_cohort(num_patients=350, duration_days=730.0)
    report = evaluate_cohort_calibration(cohort)

    # Lead time target: 4.2 ± 2.3 months (~126 ± 70 days)
    assert report.lead_time_target_met, (
        f"G1 lead time {report.mean_lead_time_days:.1f} days outside acceptable range (126 ± 40)"
    )

    # Sensitivity target: 50% - 75% for distant recurrence (E1)
    assert report.sensitivity_target_met, (
        f"G1 empirical sensitivity {report.empirical_sensitivity:.1%} outside target 50-75%"
    )

    # Specificity target: >= 95% on disease-free patients (E1)
    assert report.specificity_target_met, (
        f"G1 empirical specificity {report.empirical_specificity:.1%} below 95%"
    )


def test_g2_burst_calibration():
    gen = get_generator(GeneratorType.G2_BURST, seed=42)
    cohort = gen.generate_cohort(num_patients=250, duration_days=730.0)
    report = evaluate_cohort_calibration(cohort)

    assert report.empirical_sensitivity >= 0.45
    assert report.empirical_specificity >= 0.90


def test_g3_noise_calibration():
    gen = get_generator(GeneratorType.G3_NOISE, seed=42)
    cohort = gen.generate_cohort(num_patients=250, duration_days=730.0)
    report = evaluate_cohort_calibration(cohort)

    assert report.empirical_sensitivity >= 0.45
    assert report.empirical_specificity >= 0.90
