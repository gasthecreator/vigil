"""Non-result checks for the registered EXP-CORE-ML-009 runner contract."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

RUNNER_PATH = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("exp_core_ml_009_run", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_registered_seeds_are_unique_across_conditions_and_replicates() -> None:
    seeds = [
        RUNNER.seed_for(condition, replicate)
        for condition in RUNNER.CONDITION_OFFSETS
        for replicate in RUNNER.REPLICATES
    ]
    assert len(seeds) == 300
    assert len(seeds) == len(set(seeds))


@pytest.mark.parametrize("condition", ["MCAR", "MAR", "MNAR"])
def test_data_contract_keeps_unverified_labels_unknown(condition: str) -> None:
    cohort = RUNNER.generate_replicate(condition, 987_654, n=500)
    assert cohort["truth"].shape == (500,)
    assert cohort["verified"].shape == (500,)
    assert np.isnan(cohort["observed_y"][~cohort["verified"]]).all()
    assert np.array_equal(
        cohort["observed_y"][cohort["verified"]],
        cohort["truth"][cohort["verified"]],
    )
    assert np.all((cohort["p_verify"] > 0.0) & (cohort["p_verify"] < 1.0))


def test_mnar_changes_verification_probability_by_truth() -> None:
    cohort = RUNNER.generate_replicate("MNAR", 987_655, n=2_000)
    assert np.mean(cohort["p_verify"][cohort["truth"] == 1]) > np.mean(
        cohort["p_verify"][cohort["truth"] == 0]
    )


@pytest.mark.parametrize("condition", ["MCAR", "MAR", "MNAR"])
def test_verification_probabilities_match_registered_formulas(condition: str) -> None:
    cohort = RUNNER.generate_replicate(condition, 987_656, n=200)
    x = cohort["x"]
    if condition == "MCAR":
        expected = np.full(len(x), 0.60)
    elif condition == "MAR":
        expected = 1.0 / (1.0 + np.exp(-(-0.5 + x)))
    else:
        outcome_term = 2.0 * cohort["truth"] - 1.0
        expected = 1.0 / (1.0 + np.exp(-(-0.5 + x + outcome_term)))
    assert np.allclose(cohort["p_verify"], expected)


def test_registered_report_is_rendered_from_results() -> None:
    results = {
        "source_commit": "registered-source",
        "design": {"replicates": 1, "n": 10},
        "summary": {
            condition: {
                estimator: {
                    metric: {
                        "mean_error": 0.125,
                        "error_sd": 0.25,
                        "error_percentiles_2_5_97_5": [-0.5, 0.5],
                    }
                    for metric in RUNNER.METRICS
                }
                for estimator in ("complete_case", "ipw")
            }
            for condition in RUNNER.CONDITION_OFFSETS
        },
    }
    rendered = RUNNER.render_report(results)
    assert "| MAR | ipw | roc_auc | 0.125000 | 0.250000 | [-0.500000, 0.500000] |" in rendered


def test_runner_refuses_to_overwrite_existing_result_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experiment_dir = tmp_path / "EXP-CORE-ML-009"
    experiment_dir.mkdir()
    (experiment_dir / "results.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(RUNNER, "EXP", experiment_dir)
    with pytest.raises(RuntimeError, match="one-time"):
        RUNNER.main()


def test_preregistration_matches_runner_design() -> None:
    preregistration = (RUNNER.EXP / "PREREG.md").read_text(encoding="utf-8")
    assert "100 per condition" in preregistration
    assert "2,500 per replicate" in preregistration
    assert RUNNER.seed_for("MCAR", 0) == 20_261_021
    assert RUNNER.seed_for("MAR", 0) == 20_361_021
    assert RUNNER.seed_for("MNAR", 99) == 20_461_120
