from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import poisson

PATH = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("exp_core_ml_013_run", PATH)
RUN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUN
SPEC.loader.exec_module(RUN)


def test_registered_replicate_seed_allocation_is_stable():
    assert RUN.cohort_seed("G1", 0) == 20_580_101
    assert RUN.cohort_seed("G2", 2) == 20_730_101
    assert RUN.cohort_seed("G3", 4) == 20_880_101


def test_probability_ordering_poisson_test_handles_center_and_zero_rate():
    expected = 4.0
    observed = 4
    probabilities = poisson.pmf(np.arange(30), expected)
    p = probabilities[probabilities <= poisson.pmf(observed, expected) * (1 + 1e-12)].sum()
    assert RUN.exact_two_sided_poisson_p(observed, expected) == pytest.approx(p)
    assert RUN.exact_two_sided_poisson_p(0, 0.0) == 1.0
    assert RUN.exact_two_sided_poisson_p(1, 0.0) == 0.0


def test_holm_adjustment_is_monotone_and_keeps_family_size():
    adjusted = RUN.holm_adjust({"first": 0.001, "second": 0.02, "third": 0.03})
    assert adjusted == pytest.approx({"first": 0.003, "second": 0.04, "third": 0.04})


def test_report_is_rendered_from_and_matches_saved_json(tmp_path):
    result = {
        "source_commit": "test-sha",
        "replicates": [],
    }
    result_path = tmp_path / "results.json"
    report_path = tmp_path / "REPORT.md"
    RUN.write_saved_result_and_report(result_path, report_path, result)
    saved = json.loads(result_path.read_text(encoding="utf-8"))
    assert report_path.read_text(encoding="utf-8") == RUN.render(saved)


def test_runner_refuses_existing_output_before_git_or_simulation(monkeypatch, tmp_path):
    (tmp_path / "results.json").write_text("existing", encoding="utf-8")
    monkeypatch.setattr(RUN, "EXP", tmp_path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("git must not run when an output already exists")

    monkeypatch.setattr(RUN.subprocess, "run", forbidden)
    with pytest.raises(RuntimeError, match="already exists"):
        RUN.main()


def test_runner_refuses_dirty_tree_without_creating_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr(RUN, "EXP", tmp_path)
    calls = 0

    def fake_run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return type("Result", (), {"stdout": " M source.py\n"})()

    monkeypatch.setattr(RUN.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="dirty working tree"):
        RUN.main()
    assert calls == 1
    assert not list(tmp_path.iterdir())


def test_small_replicate_contract_and_report_are_deterministic(monkeypatch):
    monkeypatch.setattr(RUN, "COHORT_SIZE", 24)
    test_seeds = {"G1": 31_500_001, "G2": 31_600_001, "G3": 31_700_001}
    monkeypatch.setattr(RUN, "cohort_seed", lambda stream, _replicate: test_seeds[stream])
    profile = json.loads(RUN.PROFILE.read_text(encoding="utf-8"))
    result = RUN.one_replicate(0, profile)
    assert all(row["n_generated"] == 24 for row in result["cohort_contract"].values())
    assert result["g1_recurrence_count"] == result["cohort_contract"]["G1"]["n_true_recurrent"]
    assert result["g2"]["production_event_count_total"] >= 0
    assert result["g2"]["eligible_recurrence_person_time_days"] >= 0.0
    full = {"source_commit": "test-sha", "replicates": [result]}
    report = RUN.render(full)
    assert report == RUN.render(json.loads(json.dumps(full)))
    assert "no G3 mechanism or performance claim" in report
