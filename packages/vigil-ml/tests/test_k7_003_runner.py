from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO_ROOT / "experiments" / "EXP-S8-K7-003" / "run.py"
SPEC = importlib.util.spec_from_file_location("k7_003_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_k7_003_has_disjoint_registered_seed_allocation():
    assert RUNNER.SEEDS == tuple(range(620261121, 620261141))


def test_k7_003_summary_uses_nested_estimates_and_preserves_denominators():
    row = {
        "condition": "measured_confounding",
        "status": "estimable",
        "truth": {"risk_ratio": 1.10},
        "estimates": {
            "estimates": {"aipw": {"risk_ratio": 1.25}},
            "covariate_balance": {"maximum_weighted_smd": 0.04},
        },
        "aipw_interval_covers_truth": True,
    }
    summary = RUNNER._summarize([row], "measured_confounding")
    assert summary["aipw_risk_ratio_mean"] == pytest.approx(1.25)
    assert summary["absolute_mean_point_estimate_error"] == pytest.approx(0.15)
    assert summary["cohort_interval_coverage_count"] == 1
    assert summary["cohort_interval_coverage_denominator"] == 1


def test_k7_003_runner_requires_committed_pre_run_record(tmp_path, monkeypatch):
    monkeypatch.setattr(RUNNER, "ACCESS_LOG", tmp_path / "missing-access.jsonl")
    monkeypatch.setattr(RUNNER, "RESULTS", tmp_path / "results.json")
    monkeypatch.setattr(RUNNER, "REPORT", tmp_path / "REPORT.md")
    monkeypatch.setattr(RUNNER, "COMPLETION", tmp_path / "RUN_COMPLETION.json")
    with pytest.raises(RuntimeError, match="access log is missing"):
        RUNNER.validate_access()
    assert not (tmp_path / "results.json").exists()
