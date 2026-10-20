from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from vigil_sim.generators import CohortDataset

RUNNER_PATH = Path(__file__).resolve().parents[3] / "experiments" / "EXP-SIM-CAL-E1-002" / "run.py"
SPEC = importlib.util.spec_from_file_location("e1_study_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_runner_design_constants_match_preregistered_values():
    prereg = RUNNER.PREREG_PATH.read_text(encoding="utf-8")
    assert "30 independent cohorts per generator" in prereg
    assert "1,023 patients per cohort" in prereg
    assert "2,263 administrative follow-up days" in prereg
    assert "base_seed = 615000 + generator_offset + replicate" in prereg
    assert "Bootstrap seed: `615999`" in prereg
    assert "offsets G1=100, G2=200, G3=300" in prereg
    assert "fewer than 24 of 30 replicates" in prereg
    assert RUNNER.PROFILE_SHA256 in prereg
    assert RUNNER.PROFILE_SHA256 == RUNNER.sha256(RUNNER.PROFILE_PATH)
    assert "10,000 bootstrap resamples" in prereg
    assert RUNNER.REPLICATES == 30
    assert RUNNER.PATIENTS_PER_COHORT == 1023
    assert RUNNER.FOLLOWUP_DAYS == 2263.0
    assert RUNNER.BOOTSTRAP_SEED == 615999
    assert RUNNER.BOOTSTRAP_REPLICATES == 10000
    assert RUNNER.MIN_DEFINED_REPLICATES == 24
    assert RUNNER.CONFIDENCE_LEVEL == 0.95
    assert [(name, offset) for name, _, offset in RUNNER.GENERATORS] == [
        ("G1", 100),
        ("G2", 200),
        ("G3", 300),
    ]


def test_study_seed_allocation_is_unique():
    seeds = [
        RUNNER._seed(offset, replicate)
        for _, _, offset in RUNNER.GENERATORS
        for replicate in range(RUNNER.REPLICATES)
    ]
    assert len(seeds) == 90
    assert len(set(seeds)) == len(seeds)
    assert seeds == sorted(seeds)


def test_bootstrap_withholds_interval_when_too_few_replicates_define_metric():
    rng = np.random.default_rng(RUNNER.BOOTSTRAP_SEED)
    summary = RUNNER._bootstrap_summary([0.5] * 23 + [None] * 7, rng)

    assert summary["defined_replicates"] == 23
    assert summary["status"] == "not_estimable"
    assert summary["ci"] is None


def test_bootstrap_uses_registered_seed_count_and_preserves_defined_count():
    rng = np.random.default_rng(RUNNER.BOOTSTRAP_SEED)
    summary = RUNNER._bootstrap_summary([float(i) for i in range(24)] + [None] * 6, rng)

    assert summary["defined_replicates"] == 24
    assert summary["total_replicates"] == 30
    assert summary["ci_replicates"] == 10000
    assert summary["status"] == "estimated"
    assert summary["ci"][0] <= summary["mean"] <= summary["ci"][1]


def test_renderer_labels_synthetic_limits_and_unestimable_site_endpoint():
    result = {
        "profile_id": "balanced_synthetic_core_v4",
        "cutoff": {
            "source_value": 60.0,
            "source_unit": "U/mL",
            "value": 60.0,
            "canonical_unit": "[iU]/mL",
        },
        "aggregate": {
            "G1": {
                "case_detection": {
                    "defined_replicates": 30,
                    "total_replicates": 30,
                    "mean": 0.41,
                    "ci": [0.3, 0.5],
                }
            }
        },
    }
    report = RUNNER.render_report(result)

    assert "Synthetic simulator diagnostics only" in report
    assert "do not establish clinical calibration" in report
    assert "not_estimable" in report
    assert "> 60.0 U/mL" in report
    assert "Molina et al. 1995" in report
    assert "ASCO guidance (2026)" in report
    assert "uses observed diagnosis" in report


def test_committed_report_matches_saved_json_when_study_result_exists():
    if not RUNNER.RESULTS_PATH.exists():
        return
    result = json.loads(RUNNER.RESULTS_PATH.read_text(encoding="utf-8"))
    assert RUNNER.REPORT_PATH.read_text(encoding="utf-8") == RUNNER.render_report(result)


def test_runner_writes_access_record_before_cohort_generation(monkeypatch, tmp_path):
    root = tmp_path
    experiment = root / "experiments" / RUNNER.EXPERIMENT_ID
    experiment.mkdir(parents=True)
    profile = root / "packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json"
    prereg = experiment / "PREREG.md"
    prereg.write_text("registered test protocol\n", encoding="utf-8")
    profile.parent.mkdir(parents=True)
    profile.write_text('{"profile_id":"balanced_synthetic_core_v4"}\n', encoding="utf-8")
    fake_script = experiment / "run.py"
    fake_script.write_text("test runner\n", encoding="utf-8")
    for relative in (
        "packages/vigil-sim/vigil_sim/generators.py",
        "packages/vigil-sim/vigil_sim/e1_comparison.py",
        "packages/vigil-core/vigil_core/units.py",
        "uv.lock",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test source\n", encoding="utf-8")

    monkeypatch.setattr(RUNNER, "ROOT", root)
    monkeypatch.setattr(RUNNER, "__file__", fake_script)
    monkeypatch.setattr(RUNNER, "EXPERIMENT", experiment)
    monkeypatch.setattr(RUNNER, "PROFILE_PATH", profile)
    monkeypatch.setattr(RUNNER, "PREREG_PATH", prereg)
    monkeypatch.setattr(RUNNER, "ACCESS_LOG_PATH", experiment / "ACCESS_LOG.jsonl")
    monkeypatch.setattr(RUNNER, "RESULTS_PATH", experiment / "results.json")
    monkeypatch.setattr(RUNNER, "REPORT_PATH", experiment / "REPORT.md")
    monkeypatch.setattr(RUNNER, "COMPLETION_PATH", experiment / "RUN_COMPLETION.json")
    monkeypatch.setattr(RUNNER, "GENERATORS", (("G1", RUNNER.GeneratorType.G1_SMOOTH, 100),))
    monkeypatch.setattr(RUNNER, "REPLICATES", 2)
    monkeypatch.setattr(RUNNER, "PATIENTS_PER_COHORT", 3)
    monkeypatch.setattr(RUNNER, "FOLLOWUP_DAYS", 10.0)
    monkeypatch.setattr(RUNNER, "MIN_DEFINED_REPLICATES", 2)
    monkeypatch.setattr(RUNNER, "BOOTSTRAP_REPLICATES", 100)
    monkeypatch.setattr(RUNNER, "_require_clean_checkout", lambda: "source-commit")
    monkeypatch.setattr(RUNNER, "_git", lambda *args: "prereg-commit")
    monkeypatch.setattr(RUNNER, "PROFILE_SHA256", "mismatched-preregistered-hash")

    with pytest.raises(RuntimeError, match="profile hash differs from preregistration"):
        RUNNER.run_study()
    assert not RUNNER.ACCESS_LOG_PATH.exists()
    monkeypatch.setattr(RUNNER, "PROFILE_SHA256", RUNNER.sha256(profile))

    def fake_generator(generator_type, *, seed, population_config):
        assert population_config["profile_id"] == "balanced_synthetic_core_v4"

        class FakeGenerator:
            def generate_cohort(self, *, num_patients, duration_days):
                assert num_patients == 3
                assert duration_days == 10.0
                return CohortDataset(
                    patients=[],
                    observations=[],
                    latent_states=[],
                    generator_type=generator_type,
                    seed=seed,
                )

        return FakeGenerator()

    failed_experiment = root / "experiments" / "failure-case"
    failed_experiment.mkdir(parents=True)
    failed_prereg = failed_experiment / "PREREG.md"
    failed_prereg.write_text("failure-path test protocol\n", encoding="utf-8")
    monkeypatch.setattr(RUNNER, "EXPERIMENT", failed_experiment)
    monkeypatch.setattr(RUNNER, "PREREG_PATH", failed_prereg)
    monkeypatch.setattr(RUNNER, "ACCESS_LOG_PATH", failed_experiment / "ACCESS_LOG.jsonl")
    monkeypatch.setattr(RUNNER, "RESULTS_PATH", failed_experiment / "results.json")
    monkeypatch.setattr(RUNNER, "REPORT_PATH", failed_experiment / "REPORT.md")
    monkeypatch.setattr(RUNNER, "COMPLETION_PATH", failed_experiment / "RUN_COMPLETION.json")
    monkeypatch.setattr(RUNNER, "get_generator", fake_generator)

    def failing_evaluator(cohort, *, administrative_followup_days):
        raise ValueError("registered evaluator failure")

    monkeypatch.setattr(RUNNER, "evaluate_e1_source_comparison", failing_evaluator)
    with pytest.raises(ValueError, match="registered evaluator failure"):
        RUNNER.run_study()
    failure_cohort_path = failed_experiment / "FAILED_COHORT_G1-REP-00.json"
    assert failure_cohort_path.exists()
    failed_cohort = json.loads(failure_cohort_path.read_text(encoding="utf-8"))
    assert failed_cohort["cohort"]["generator_type"] == RUNNER.GeneratorType.G1_SMOOTH.value
    assert failed_cohort["cohort"]["seed"] == 615100
    assert failed_cohort["cohort"]["patients"] == []
    failed_events = [
        json.loads(line) for line in RUNNER.ACCESS_LOG_PATH.read_text(encoding="utf-8").splitlines()
    ]
    assert failed_events[-1]["event"] == "cohort_evaluation_failed"
    assert failed_events[-1]["failed_cohort_sha256"] == RUNNER.sha256(failure_cohort_path)

    monkeypatch.setattr(RUNNER, "EXPERIMENT", experiment)
    monkeypatch.setattr(RUNNER, "PREREG_PATH", prereg)
    monkeypatch.setattr(RUNNER, "ACCESS_LOG_PATH", experiment / "ACCESS_LOG.jsonl")
    monkeypatch.setattr(RUNNER, "RESULTS_PATH", experiment / "results.json")
    monkeypatch.setattr(RUNNER, "REPORT_PATH", experiment / "REPORT.md")
    monkeypatch.setattr(RUNNER, "COMPLETION_PATH", experiment / "RUN_COMPLETION.json")

    def fake_evaluator(cohort, *, administrative_followup_days):
        return {
            "generator": cohort.generator_type.value,
            "seed": cohort.seed,
            "ca_15_3_cutoff": {
                "source_value": 60.0,
                "source_unit": "U/mL",
                "value": 60.0,
                "canonical_unit": "[iU]/mL",
            },
            "case_detection": {
                "diagnosed_cases": 2,
                "monitored_cases": 2,
                "detected_cases": 1,
                "fraction_monitored_detected": 0.5,
                "fraction_all_diagnosed_detected": 0.5,
            },
            "conditional_lead_time": {
                "mean_months": 4.0,
                "sample_sd_months": 0.5,
            },
            "observed_ned_specificity": {
                "specificity": 0.9,
                "eligible_ned_patients": 10,
                "measured_ned_patients": 9,
                "negative_measured_ned_patients": 8,
            },
            "oracle_recurrence_free_specificity": {
                "specificity": 0.95,
                "eligible_recurrence_free_patients": 5,
                "measured_recurrence_free_patients": 4,
                "negative_measured_patients": 3,
            },
        }

    monkeypatch.setattr(RUNNER, "get_generator", fake_generator)
    monkeypatch.setattr(RUNNER, "evaluate_e1_source_comparison", fake_evaluator)

    results = RUNNER.run_study()

    events = [
        json.loads(line) for line in RUNNER.ACCESS_LOG_PATH.read_text(encoding="utf-8").splitlines()
    ]
    assert events[0]["event"] == "run_started"
    assert events[0]["study_cohort_generation_begins_after_this_record"] is True
    assert [event["event"] for event in events[1:]] == [
        "cohort_access_started",
        "cohort_generated_and_evaluated",
        "cohort_access_started",
        "cohort_generated_and_evaluated",
        "run_completed",
    ]
    assert len(results["replicates"]["G1"]) == 2
    report = RUNNER.REPORT_PATH.read_text(encoding="utf-8")
    assert report == RUNNER.render_report(results)
    assert "## Per-seed counts and estimates" in report
    assert "| G1 | 615100 | 1/2 | 1/2 | 2/2 | 4 ± 0.5 | 8/9 | 9/10 | 3/4 |" in report
    completion = json.loads(RUNNER.COMPLETION_PATH.read_text(encoding="utf-8"))
    assert completion["access_log_sha256"] == RUNNER.sha256(RUNNER.ACCESS_LOG_PATH)
    assert completion["results_sha256"] == RUNNER.sha256(RUNNER.RESULTS_PATH)
    with pytest.raises(RuntimeError, match="artifacts already exist"):
        RUNNER.run_study()
