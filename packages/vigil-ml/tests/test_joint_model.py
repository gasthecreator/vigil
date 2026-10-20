"""
Tests for the quarantined historical K3 alias and landmark logistic baseline.
"""

import numpy as np
import pandas as pd
import pytest
from vigil_ml.joint_model import (
    BayesianJointModelK3,
    FastLandmarkJointModel,
    LandmarkLogisticResearchBaseline,
)


@pytest.fixture
def longitudinal_survival_data():
    rng = np.random.default_rng(42)
    n = 120
    X = pd.DataFrame(
        {
            "patient_id": [f"PT-{i}" for i in range(n)],
            "eval_day": rng.uniform(0, 360, n),
            "age": rng.normal(48, 8, n),
            "ca_15_3_curr": rng.uniform(15, 70, n),
            "ca_15_3_slope_90d": rng.normal(0.04, 0.05, n),
        }
    )
    follow_up = rng.uniform(60, 500, n)
    # Recurrence hazard coupled to marker level
    events = (X["ca_15_3_curr"] > 35.0).astype(int)
    y = pd.Series(events)
    return X, y, follow_up, events.values


def test_historical_bayesian_k3_alias_fails_closed(longitudinal_survival_data):
    X, y, _, _ = longitudinal_survival_data
    model = BayesianJointModelK3(n_chains=2, n_warmup=50, n_samples=100, random_state=42)

    with pytest.raises(RuntimeError, match="is quarantined"):
        model.fit(X, y)
    with pytest.raises(RuntimeError, match="is quarantined"):
        model.check_posterior_predictive(X)
    with pytest.raises(RuntimeError, match="is quarantined"):
        model.predict_risk(X)
    assert model.get_model_id() == "K3_QUARANTINED_INVALID_HISTORICAL_IMPLEMENTATION"


def test_fast_landmark_logistic_research_baseline(longitudinal_survival_data):
    X, y, _, _ = longitudinal_survival_data
    model = LandmarkLogisticResearchBaseline(horizon_days=180.0)
    model.fit(X, y)
    preds = model.predict_risk(X)

    assert isinstance(model, FastLandmarkJointModel)
    assert len(preds) == len(X)
    assert np.all(np.isfinite(preds))
    assert np.all((preds >= 0.0) & (preds <= 1.0))
