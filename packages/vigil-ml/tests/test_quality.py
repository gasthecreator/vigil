"""Unit and Privacy Property Tests for Missed-Signal Quality Audit (M10).

Verifies Master Plan §6.10, §11, and ADR 0016:
1. Strictly neutral descriptive register (no punitive language).
2. Small-cell suppression ($k \\ge 5$) prevents re-identification in rare strata.
3. Ground-truth sensitivity and specificity in detecting missed signals.
4. Specificity under biological noise perturbations.
"""

import numpy as np
from vigil_ml.quality import (
    AuditTrajectory,
    AuditVisit,
    MissedSignalAuditEngine,
    generate_synthetic_audit_cohort,
    verify_neutral_register,
)


def test_neutral_register_validator():
    """Validates that non-accusatory register is enforced and punitive words are detected."""
    # Permitted neutral descriptive phrasing
    assert verify_neutral_register("Signal present, action not recorded within 30 days.")
    assert verify_neutral_register(
        "Audit completed for 120 patients across public oncology clinics."
    )
    assert verify_neutral_register("No recorded imaging order within surveillance interval.")

    # Forbidden punitive terms
    assert not verify_neutral_register("Clinician negligence led to diagnostic delay.")
    assert not verify_neutral_register("Medical error in staging assessment.")
    assert not verify_neutral_register("Staff fault identified in clinic referral.")
    assert not verify_neutral_register("Potential malpractice in breast clinic.")
    assert not verify_neutral_register("Clinician blame assigned for missed appointment.")


def test_small_cell_suppression_k_anonymity():
    """Strata with 1 <= n < 5 must be suppressed to enforce k-anonymity privacy floor."""
    engine = MissedSignalAuditEngine()
    cohort = generate_synthetic_audit_cohort(
        n_missed=20, n_acted=30, n_stable=50, inject_small_cell_strata=True, seed=42
    )

    report = engine.generate_audit_report(cohort)

    # Injected rare stratum: 'isolated_island_clinic' with n=3 patients
    subgroup_metrics = report.subgroup_breakdown
    assert "isolated_island_clinic" in subgroup_metrics
    small_stratum = subgroup_metrics["isolated_island_clinic"]

    assert small_stratum.is_suppressed is True
    assert small_stratum.total_signals == "<5"
    assert small_stratum.action_not_recorded_count == "<5"
    assert small_stratum.action_not_recorded_rate is None

    # Normal strata (n >= 5) must NOT be suppressed
    assert subgroup_metrics["rural_public"].is_suppressed is False
    assert isinstance(subgroup_metrics["rural_public"].total_signals, int)
    assert subgroup_metrics["rural_public"].total_signals >= 5


def test_synthetic_ground_truth_recovery():
    """Engine must accurately recover injected missed signals vs acted-upon and stable cases."""
    engine = MissedSignalAuditEngine()
    cohort = generate_synthetic_audit_cohort(
        n_missed=150, n_acted=250, n_stable=600, inject_small_cell_strata=False, seed=20261017
    )

    report = engine.generate_audit_report(cohort, expose_raw_for_testing=True)

    # 150 missed signals + 250 acted-upon = 400 total signals
    assert report.total_signals_detected == 400
    # 150 missed signals should have action_not_recorded
    assert report.total_action_not_recorded == 150
    assert report.total_action_recorded == 250

    # Sensitivity: true missed signals identified / injected missed signals
    sensitivity = report.total_action_not_recorded / 150
    assert sensitivity >= 0.95

    # Specificity: stable patients must produce 0 false signals
    raw_evals = report.raw_unsuppressed_for_testing["signals"]
    stable_evals = [e for e in raw_evals if e["trajectory"].trajectory_id.startswith("TRJ-STABLE")]
    false_positives = sum(1 for e in stable_evals if e["signal_present"])
    assert false_positives == 0, (
        f"Expected 0 false signals in stable patients, found {false_positives}"
    )


def test_biological_noise_resilience():
    """Benign physiological fluctuations (e.g. transient noise) must not trigger false alarms."""
    engine = MissedSignalAuditEngine()
    rng = np.random.default_rng(999)

    # Generate 100 noisy trajectories with random benign fluctuations
    noisy_trajectories = []
    for i in range(100):
        visits = [
            AuditVisit(day=0, marker_value=float(rng.normal(18.0, 2.0)), alert_level="none"),
            AuditVisit(
                day=90, marker_value=float(rng.normal(19.5, 2.0)), alert_level="watch"
            ),  # isolated watch
            AuditVisit(
                day=180, marker_value=float(rng.normal(17.5, 2.0)), alert_level="none"
            ),  # drops back down
            AuditVisit(day=270, marker_value=float(rng.normal(18.2, 2.0)), alert_level="none"),
        ]
        noisy_trajectories.append(
            AuditTrajectory(
                trajectory_id=f"NOISE-{i}",
                subtype="adjuvant_post_lumpectomy",
                stage="stage_1",
                subgroup="urban_referral",
                visits=visits,
            )
        )

    report = engine.generate_audit_report(noisy_trajectories)
    # Transient single watch without sustained rise must not be flagged as missed signal
    assert report.total_action_not_recorded == 0
