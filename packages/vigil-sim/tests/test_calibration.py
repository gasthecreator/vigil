"""
Tests for vigil_sim.calibration: Verification of published clinical targets (EVIDENCE E1, E12).
Overseer Condition C2 Compliance (docs/progress/VERDICT-P0-P1.md).

IMPORTANT: The generators evaluated here were deliberately TUNED to reproduce reported figures from
published landmark literature (Molina et al. 1995, n=1,023; Wu et al. 2017, n=243,896).
Meeting these targets verifies that the generator parameters produce the intended synthetic cohort
behavior; it does NOT constitute independent real-world clinical validation.
"""

from vigil_sim.calibration import evaluate_cohort_calibration, run_full_calibration_check
from vigil_sim.generators import GeneratorType, get_generator


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
    assert 40.0 <= report.conditional_lead_time_std_days <= 110.0, (
        f"G1 conditional lead time SD {report.conditional_lead_time_std_days:.1f}d outside tolerance"
    )

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
