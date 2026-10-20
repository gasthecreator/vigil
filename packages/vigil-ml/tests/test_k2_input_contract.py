import json
import math
from pathlib import Path

import pytest
from vigil_ml.k2 import DEFAULT_K2_RESEARCH_CONFIG, SequentialDetector, load_k2_research_config


def test_default_research_parameters_are_loaded_and_hashed_from_versioned_config():
    detector = SequentialDetector()

    assert detector.alpha_pt == DEFAULT_K2_RESEARCH_CONFIG.alpha_pt
    assert detector.sigma_log == DEFAULT_K2_RESEARCH_CONFIG.sigma_log
    assert detector.burn_in == DEFAULT_K2_RESEARCH_CONFIG.burn_in
    assert detector.lambdas.tolist() == list(DEFAULT_K2_RESEARCH_CONFIG.growth_grid)
    assert detector.config_id == DEFAULT_K2_RESEARCH_CONFIG.config_id
    assert detector.config_source_sha256 == load_k2_research_config().source_sha256
    assert len(detector.effective_config_sha256) == 64


def test_config_loader_refuses_unlabeled_or_malformed_research_parameters(tmp_path):
    config_path = Path(__file__).parents[1] / "vigil_ml" / "models" / "k2_research_config_v1.json"
    raw = json.loads(config_path.read_text())
    raw["status"] = "clinical"
    malformed = tmp_path / "k2.json"
    malformed.write_text(json.dumps(raw))

    with pytest.raises(ValueError, match="unvalidated research"):
        load_k2_research_config(malformed)


@pytest.mark.parametrize("alpha_pt", [0.0, 1.0, -0.1, math.nan, math.inf, True])
def test_constructor_rejects_invalid_alpha(alpha_pt):
    with pytest.raises(ValueError, match="alpha_pt"):
        SequentialDetector(alpha_pt=alpha_pt)


@pytest.mark.parametrize("sigma_log", [0.0, -0.1, math.nan, math.inf, True])
def test_constructor_rejects_invalid_scale(sigma_log):
    with pytest.raises(ValueError, match="sigma_log"):
        SequentialDetector(sigma_log=sigma_log)


@pytest.mark.parametrize("burn_in", [0, -1, 1.5, True, math.nan, math.inf])
def test_constructor_rejects_invalid_burn_in(burn_in):
    with pytest.raises(ValueError, match="burn_in"):
        SequentialDetector(burn_in=burn_in)


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf, -math.inf, True])
def test_update_rejects_invalid_observation_without_mutating_state(value):
    detector = SequentialDetector()

    with pytest.raises(ValueError, match="value must be a finite positive measurement"):
        detector.update(10.0, value)

    assert detector.history == []
    assert detector.days == []
    assert detector.log_e == 0.0


@pytest.mark.parametrize("day", [math.nan, math.inf, -math.inf, True])
def test_update_rejects_invalid_day(day):
    with pytest.raises(ValueError, match="day must be finite and numeric"):
        SequentialDetector().update(day, 20.0)


def test_missing_observation_advances_day_without_entering_marker_history():
    detector = SequentialDetector()

    detector.update(10.0, None)

    assert detector.history == []
    assert detector.days == [10.0]


def test_observations_reject_out_of_order_days_but_allow_same_day_repeats():
    detector = SequentialDetector()
    detector.update(10.0, None)
    detector.update(10.0, 20.0)

    with pytest.raises(ValueError, match="nondecreasing"):
        detector.update(9.0, 21.0)

    assert detector.history == [pytest.approx(math.log(20.0))]
    assert detector.days == [10.0, 10.0]


@pytest.mark.parametrize(
    ("score", "threshold"),
    [
        (math.nan, 0.5),
        (math.inf, 0.5),
        (-0.1, 0.5),
        (1.1, 0.5),
        (0.5, math.nan),
        (0.5, 1.1),
        (True, 0.5),
        (0.5, True),
    ],
)
def test_risk_score_adapter_rejects_invalid_probabilities(score, threshold):
    with pytest.raises(ValueError):
        SequentialDetector().integrate_with_risk_score(score, threshold)


def test_risk_score_adapter_fails_closed_for_valid_looking_inputs():
    with pytest.raises(RuntimeError, match="disabled.*validated clinical utility"):
        SequentialDetector().integrate_with_risk_score(0.8, 0.5)
