import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

RUNNER_PATH = Path(__file__).resolve().parents[3] / "experiments" / "EXP-M3-002" / "run.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("exp_m3_002_runner", RUNNER_PATH)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)
RENDERER_PATH = RUNNER_PATH.parent / "render.py"
RENDERER_SPEC = importlib.util.spec_from_file_location("exp_m3_002_renderer", RENDERER_PATH)
assert RENDERER_SPEC is not None and RENDERER_SPEC.loader is not None
RENDERER = importlib.util.module_from_spec(RENDERER_SPEC)
RENDERER_SPEC.loader.exec_module(RENDERER)


def test_study_uses_only_finite_positive_observed_values_and_records_exclusions():
    observations = pd.DataFrame(
        {
            "observed_ca_15_3": [True, True, True, True, True, True, False],
            "ca_15_3": [10.0, 0.0, -1.0, np.nan, np.inf, 12.0, 15.0],
            "day": [0.0, 1.0, 2.0, 3.0, 4.0, np.inf, 6.0],
        }
    )

    eligible, exclusions = RUNNER.valid_marker_rows(observations)

    assert eligible["ca_15_3"].tolist() == [10.0]
    assert exclusions == {
        "excluded_unobserved_observations": 1,
        "excluded_missing_values": 1,
        "excluded_nonfinite_values": 1,
        "excluded_nonpositive_values": 2,
        "excluded_nonfinite_days": 1,
    }


def test_study_history_uses_strictly_earlier_days():
    days = np.asarray([0.0, 30.0, 30.0, 60.0, 90.0])

    assert RUNNER.strictly_prior_indices(days, 3).tolist() == [0, 1, 2]
    assert RUNNER.strictly_prior_indices(days, 4).tolist() == [0, 1, 2, 3]


def test_successor_study_uses_fresh_seeds():
    assert RUNNER.STUDY_ID == "EXP-M3-002"
    assert RUNNER.SEEDS == (20261024, 20261025, 20261026)


def test_renderer_reports_eligibility_exclusions():
    report = RENDERER.render_report(
        {
            "study_id": "EXP-M3-002",
            "protocol_version": "1.0",
            "source_commit": "test",
            "strata": [
                {
                    "generator": "G1",
                    "seed": 20261024,
                    "n_evaluations": 10,
                    "excluded_unobserved_observations": 1,
                    "excluded_missing_values": 2,
                    "excluded_nonfinite_values": 3,
                    "excluded_nonpositive_values": 4,
                    "excluded_nonfinite_days": 5,
                }
            ],
            "configurations": [],
        }
    )

    assert "| G1 | 20261024 | 10 | 1 | 2 | 3 | 4 | 5 |" in report
