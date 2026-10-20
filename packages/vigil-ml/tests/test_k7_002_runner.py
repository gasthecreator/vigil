from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO_ROOT / "experiments" / "EXP-S8-K7-002" / "run.py"
SPEC = importlib.util.spec_from_file_location("k7_002_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_k7_runner_fails_closed_without_pre_run_access_record(tmp_path, monkeypatch):
    monkeypatch.setattr(RUNNER, "ACCESS_LOG", tmp_path / "missing-access.jsonl")
    monkeypatch.setattr(RUNNER, "RESULTS", tmp_path / "results.json")
    monkeypatch.setattr(RUNNER, "REPORT", tmp_path / "REPORT.md")
    monkeypatch.setattr(RUNNER, "COMPLETION", tmp_path / "RUN_COMPLETION.json")
    with pytest.raises(RuntimeError, match="access log is missing"):
        RUNNER.validate_access()
    assert not (tmp_path / "results.json").exists()
    assert not (tmp_path / "REPORT.md").exists()


def test_k7_summary_reads_nested_estimator_result_and_keeps_denominators():
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


def test_k7_002_fails_closed_after_appended_spent_seed_record(tmp_path, monkeypatch):
    access_log = tmp_path / "access.jsonl"
    entries = [
        {"experiment_id": "EXP-S8-K7-002", "status": "pre_run_record_committed"},
        {"experiment_id": "EXP-S8-K7-002", "event": "one_time_run_failed_after_cohort_generation"},
    ]
    access_log.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
    monkeypatch.setattr(RUNNER, "ACCESS_LOG", access_log)
    monkeypatch.setattr(RUNNER, "RESULTS", tmp_path / "results.json")
    monkeypatch.setattr(RUNNER, "REPORT", tmp_path / "REPORT.md")
    monkeypatch.setattr(RUNNER, "COMPLETION", tmp_path / "RUN_COMPLETION.json")
    monkeypatch.setattr(RUNNER, "_git", lambda *args: "")
    with pytest.raises(RuntimeError, match="exactly one K7-002 authorization"):
        RUNNER.validate_access()
