"""
Tests for vigil_ml.joint_model: K3 Bayesian Joint Model and Fast Landmarking approximation.
"""

import numpy as np
import pandas as pd
import pytest
from vigil_ml.joint_model import BayesianJointModelK3, FastLandmarkJointModel


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


def test_bayesian_joint_model_k3_mcmc(longitudinal_survival_data):
    X, y, follow_up, events = longitudinal_survival_data

    # Run quick MCMC for unit test verification (2 chains, 50 warmup, 100 samples)
    model = BayesianJointModelK3(n_chains=2, n_warmup=50, n_samples=100, random_state=42)
    model.fit(X, y, follow_up_times=follow_up, event_indicators=events)

    assert model.diagnostics is not None
    assert "alpha" in model.diagnostics.r_hat
    # Gelman-Rubin R-hat should be close to 1.0
    for param, r_hat in model.diagnostics.r_hat.items():
        assert r_hat <= 1.15, f"R-hat for {param} was {r_hat}, expected <= 1.15"

    # Posterior predictive check
    ppc = model.check_posterior_predictive(X)
    assert ppc.passed, f"PPC coverage {ppc.replicate_coverage_95} was below threshold"

    # Risk predictions
    preds = model.predict_risk(X)
    assert len(preds) == len(X)
    assert np.all((preds >= 0.0) & (preds <= 1.0))


def test_fast_landmark_production_model(longitudinal_survival_data):
    X, y, _, _ = longitudinal_survival_data

    fast_model = FastLandmarkJointModel(horizon_days=180.0)
    fast_model.fit(X, y)

    # Test individual Empirical Bayes state estimation
    days = np.array([0.0, 90.0, 180.0])
    markers = np.array([22.0, 26.0, 35.0])
    b0, b1 = fast_model.estimate_individual_latent_state(days, markers)

    assert isinstance(b0, float)
    assert isinstance(b1, float)
    # Positive trend in markers should produce positive slope random effect b1
    assert b1 > 0.0

    # Test rapid batch risk prediction
    import time

    t0 = time.perf_counter()
    preds = fast_model.predict_risk(X)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(preds) == len(X)
    assert np.all((preds >= 0.0) & (preds <= 1.0))
    # Must meet the low latency requirement (< 100 ms for batch)
    assert elapsed_ms < 100.0, f"Inference took {elapsed_ms:.1f} ms, exceeded 100 ms budget"
