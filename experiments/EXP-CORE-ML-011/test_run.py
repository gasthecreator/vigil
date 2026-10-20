"""Fast unregistered tests for the EXP-CORE-ML-011 runner contracts."""

import importlib.util
from pathlib import Path

import pytest

RUNNER_PATH = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("exp_core_ml_011_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_exact_poisson_test_is_bounded_and_detects_extreme_count():
    assert 0.0 <= runner.poisson_two_sided_exact(10, 10.0) <= 1.0
    assert runner.poisson_two_sided_exact(100, 1.0) < 0.01


def test_rk4_reference_matches_exact_constant_burden_transition():
    from vigil_sim.mechanisms import propagate_first_order_secretion

    exact = propagate_first_order_secretion([0.0, 27.25], [11.0], 4.0, 0.6, 0.03)[-1]
    reference = runner.rk4_constant_burden(0.0, 27.25, 4.0, 11.0, 0.6, 0.03)
    assert abs(exact - reference) <= 1e-6


def test_report_is_rendered_from_saved_json_shape():
    result = {
        "source_commit": "abc123",
        "profile_id": "balanced_synthetic_core_v4",
        "g1_transition_check": {
            "cases": 1000,
            "max_absolute_error": 1e-10,
            "passed": True,
            "no_recurrence_signal_violations": 0,
        },
        "g2_poisson_check": {
            "patients": 5000,
            "observed_events": 100,
            "expected_events": 101.0,
            "poisson_p_value": 0.9,
            "uniform_ks_statistic": 0.02,
            "uniform_ks_p_value": 0.5,
            "no_recurrence_violations": 0,
            "count_mismatches": 0,
        },
        "replicates": [
            {
                "generator": "G2",
                "replicate": 0,
                "patients": 1000,
                "events": 100,
                "eligible_person_days": 5000.0,
            }
        ],
        "limits": "synthetic only",
    }
    report = runner.render_report(result)
    assert "1000" in report
    assert "synthetic only" in report


def test_report_does_not_call_synthetic_mechanism_evidence_clinical_calibration():
    result = {
        "source_commit": "abc123",
        "profile_id": "balanced_synthetic_core_v4",
        "g1_transition_check": {
            "cases": 1,
            "max_absolute_error": 0.0,
            "passed": True,
            "no_recurrence_signal_violations": 0,
        },
        "g2_poisson_check": {
            "patients": 1,
            "observed_events": 0,
            "expected_events": 0.0,
            "poisson_p_value": 1.0,
            "uniform_ks_statistic": 0.0,
            "uniform_ks_p_value": 0.0,
            "no_recurrence_violations": 0,
            "count_mismatches": 0,
        },
        "replicates": [],
        "limits": "Synthetic mechanism fidelity only.",
    }
    assert "do not establish clinical calibration" in runner.render_report(result)


def test_registered_runner_refuses_dirty_worktree_without_creating_outputs():
    with pytest.raises(SystemExit, match="worktree must be clean"):
        runner.run()
    assert not any(path.exists() for path in runner.OUTPUTS)
