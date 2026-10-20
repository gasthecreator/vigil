"""
packages/vigil-ml/tests/test_joint_model_validation.py

Historical K3 validation claims are quarantined; only the fast logistic baseline checks remain active.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from vigil_ml.joint_model import BayesianJointModelK3, FastLandmarkJointModel


def test_historical_k3_parameter_recovery_claim_is_quarantined():
    model = BayesianJointModelK3()
    X = pd.DataFrame({"ca_15_3_curr": [20.0, 30.0]})
    y = pd.Series([0, 1])

    with np.testing.assert_raises_regex(RuntimeError, "is quarantined"):
        model.fit(X, y)
    with np.testing.assert_raises_regex(RuntimeError, "is quarantined"):
        model.predict_risk(X)


def test_fast_landmark_research_baseline_outputs_finite_scores():
    """
    Checks that the research logistic baseline returns a finite score batch; it makes no latency or clinical SLA claim.
    """
    model = FastLandmarkJointModel(horizon_days=365.0)
    batch = pd.DataFrame({
        "ca_15_3_curr": np.linspace(20.0, 40.0, 50),
        "ca_15_3_slope_90d": np.full(50, 0.05),
        "cea_curr": np.full(50, 3.2),
        "age": np.full(50, 52.0),
        "is_stage_3_or_4": np.ones(50),
        "sub_tnbc": np.zeros(50),
        "max_symptom_grade": np.zeros(50),
    })
    with np.testing.assert_raises(RuntimeError):
        model.predict_risk(batch)
    model.fit(batch, pd.Series((batch["ca_15_3_curr"] > 30.0).astype(int)))

    preds = model.predict_risk(batch)

    assert len(preds) == 50
    assert np.isfinite(preds).all()
    assert np.all((preds >= 0.0) & (preds <= 1.0))


def test_fast_landmark_learned_coefficients_r4():
    """
    Overseer Condition R4 Validation Test:
    Confirms that FastLandmarkJointModel genuinely learns its parameters from the training split,
    rather than encoding hard-coded simulator generator coefficients.
    """
    rng = np.random.default_rng(123)
    n = 120
    df = pd.DataFrame({
        "ca_15_3_curr": rng.normal(25.0, 5.0, n),
        "ca_15_3_slope_90d": rng.normal(0.02, 0.05, n),
        "cea_curr": rng.normal(2.5, 1.0, n),
        "age": rng.normal(52.0, 8.0, n),
        "is_stage_3_or_4": rng.binomial(1, 0.3, n),
        "sub_tnbc": rng.binomial(1, 0.2, n),
        "max_symptom_grade": rng.integers(0, 3, n),
    })

    # Scenario 1: Marker strongly predictive
    y1 = pd.Series((df["ca_15_3_curr"] > 27.0).astype(int))
    m1 = FastLandmarkJointModel()
    m1.fit(df, y1)

    assert m1.is_fitted
    assert m1.fitted_coef_ is not None
    # Feature 0 is ca_15_3_curr: should have positive coefficient
    assert m1.fitted_coef_[0] > 0.0

    # Scenario 2: Age strongly predictive
    y2 = pd.Series((df["age"] > 55.0).astype(int))
    m2 = FastLandmarkJointModel()
    m2.fit(df, y2)
    # Feature 3 is age: should have positive coefficient
    assert m2.fitted_coef_[3] > 0.0
    # Coefficients between m1 and m2 must differ because they were learned from data
    assert not np.allclose(m1.fitted_coef_, m2.fitted_coef_)

