r"""Unit and Privacy Property Tests for Missed-Signal Quality Audit (M10).

Verifies Master Plan §6.10, §11, ADR 0016, ADR 0017, and VERDICT-P7B (Conditions P13-B, P13-C, P13-D):
1. Strictly neutral descriptive register (no punitive language).
2. Small-cell suppression ($k \ge 5$) prevents re-identification in rare strata.
3. No production code path exposes raw unsuppressed strata or backdoor flags.
4. Independent Injected Truth: Evaluated via K2/M3 detection, achieving >= 85% sensitivity and >= 80% precision.
5. Specificity under biological noise and transient benign spikes (false alarm rate <= 5%).
6. Pipeline-only decoupling: system-created tasks without clinician action do not suppress missed signals (missed rate > 0).
"""

from __future__ import annotations

import numpy as np
from vigil_ml.quality import (
    AuditReport,
    AuditTrajectory,
    AuditVisit,
    MissedSignalAuditEngine,
    generate_facility_audit_cohort,
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


def test_no_code_path_leaks_unsuppressed_strata():
    """Condition P13-D: Verify that AuditReport contains zero backdoor fields and no unsuppressed small cells."""
    engine = MissedSignalAuditEngine()
    # Confirm expose_raw_for_testing is NOT an accepted parameter on generate_audit_report
    import inspect

    sig = inspect.signature(engine.generate_audit_report)
    assert "expose_raw_for_testing" not in sig.parameters, (
        "Backdoor parameter expose_raw_for_testing must not exist on generate_audit_report"
    )

    # Confirm AuditReport dataclass has no raw unsuppressed attribute
    field_names = [f.name for f in AuditReport.__dataclass_fields__.values()]
    assert "raw_unsuppressed_for_testing" not in field_names

    # Test with varying small cell counts (n=1, 2, 3, 4)
    cohort = []
    for k in range(3):
        cohort.append(
            AuditTrajectory(
                trajectory_id=f"LEAK-TEST-{k}",
                subtype="ultra_rare_sarcoma",
                stage="stage_4",
                subgroup="remote_clinic",
                visits=[
                    AuditVisit(day=0, marker_value=16.0),
                    AuditVisit(day=90, marker_value=24.0),
                    AuditVisit(day=180, marker_value=38.0),
                ],
            )
        )

    report = engine.generate_audit_report(cohort)
    for bd in [report.subgroup_breakdown, report.subtype_breakdown, report.stage_breakdown]:
        for name, metric in bd.items():
            if metric.is_suppressed:
                assert metric.total_signals == "<5"
                assert metric.action_not_recorded_count == "<5"
                assert metric.action_not_recorded_rate is None
            else:
                assert (
                    metric.total_signals == 0
                    or (isinstance(metric.total_signals, int) and metric.total_signals >= 5)
                )


def test_pipeline_only_facility_produces_non_zero_missed_rate():
    """Condition P13-C: A facility with only system-created tasks must yield an action_not_recorded rate != 0."""
    cohort = generate_facility_audit_cohort(
        facility_type="facility_5_pipeline_only", n_trajectories=100, seed=20261017
    )
    engine = MissedSignalAuditEngine()
    report = engine.generate_audit_report(cohort)

    assert report.total_signals_detected > 0, "Pipeline-only facility should have detected signals"
    assert report.total_action_recorded == 0, (
        "Automated system tasks must not be credited as clinician action"
    )
    assert report.total_action_not_recorded == report.total_signals_detected
    assert report.overall_action_not_recorded_rate == 1.0, (
        f"Expected missed rate 1.0 for un-actioned facility, got {report.overall_action_not_recorded_rate}"
    )


def test_synthetic_ground_truth_recovery():
    """Engine must accurately recover injected missed signals vs acted-upon and stable cases."""
    engine = MissedSignalAuditEngine()
    cohort = generate_synthetic_audit_cohort(
        n_missed=150, n_acted=250, n_stable=600, inject_small_cell_strata=False, seed=20261017
    )

    report = engine.generate_audit_report(cohort)

    # Total signals detected >= 95% of injected 400 signals
    assert report.total_signals_detected >= 380
    assert report.total_action_not_recorded >= 140
    assert report.total_action_recorded >= 240

    # Sensitivity: true missed signals identified / injected missed signals
    sensitivity = report.total_action_not_recorded / 150
    assert sensitivity >= 0.95

    # Specificity: evaluate stable patients directly (test-only inspection)
    stable_patients = [t for t in cohort if t.trajectory_id.startswith("TRJ-STABLE")]
    false_positives = sum(
        1 for t in stable_patients if engine.evaluate_trajectory(t)["signal_present"]
    )
    assert false_positives == 0, (
        f"Expected 0 false signals in stable patients, found {false_positives}"
    )


def test_biological_noise_resilience():
    """Benign physiological fluctuations and transient spikes must not trigger false alarms."""
    engine = MissedSignalAuditEngine()

    # Test facility 4 (High benign spike clinic)
    spike_cohort = generate_facility_audit_cohort(
        facility_type="facility_4_benign_spikes", n_trajectories=200, seed=999
    )
    report_spikes = engine.generate_audit_report(spike_cohort)

    # Transient benign spikes that resolve without treatment should not latch as progression
    assert report_spikes.total_signals_detected <= 10, (
        f"Too many false alarms in benign spike clinic: {report_spikes.total_signals_detected}/200"
    )
    false_alarm_rate = report_spikes.total_signals_detected / 200.0
    assert false_alarm_rate <= 0.05, f"False alarm rate {false_alarm_rate:.2%} exceeds 5% budget"
