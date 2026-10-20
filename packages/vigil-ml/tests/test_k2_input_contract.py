import math

import pytest
from vigil_ml.k2 import SequentialDetector


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
