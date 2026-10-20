"""Input-domain and abstention contracts for M3."""

import math

import pytest
from vigil_ml.m3 import adjudicate


def call(**kwargs):
    args = {
        "history": [(0.0, 20.0)],
        "new_day": 30.0,
        "new_value": 21.0,
        "cv_analytical": 0.05,
        "cv_within": 0.08,
    }
    args.update(kwargs)
    return adjudicate(**args)


def test_empty_history_abstains_without_synthetic_probabilities():
    result = call(history=[])

    assert result["abstention"] is True
    assert result["abstention_reason"] == "insufficient_history"
    assert result["action"] == "abstain"
    assert result["p_real"] is result["p_error"] is result["p_stable"] is None
    assert result["rationale_facts"] == []


@pytest.mark.parametrize(
    "override",
    [
        {"new_value": math.nan},
        {"new_day": math.inf},
        {"cv_within": math.nan},
        {"inter_lab_cv": -0.01},
        {"p_real_prior": 0.9, "p_error_prior": 0.1},
        {"p_real_prior": -0.1},
        {"history": [(31.0, 20.0)]},
        {"history": [(0.0, math.inf)]},
        {"history": [(0.0, 0.0)]},
    ],
)
def test_invalid_or_future_model_inputs_are_rejected(override):
    with pytest.raises(ValueError):
        call(**override)


def test_valid_history_returns_finite_normalized_probabilities():
    result = call()

    probabilities = [result["p_real"], result["p_error"], result["p_stable"]]
    assert result["abstention"] is False
    assert result["assumption_config_id"] == "m3_synthetic_contract_v1"
    assert result["assumption_status"] == "synthetic_research_assumptions"
    assert len(result["assumption_config_sha256"]) == 64
    assert all(math.isfinite(p) and 0.0 <= p <= 1.0 for p in probabilities)
    assert sum(probabilities) == pytest.approx(1.0)
