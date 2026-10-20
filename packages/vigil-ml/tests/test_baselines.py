"""
Tests for vigil_ml.baselines: Classical surveillance baselines (M2 stack).
"""

import numpy as np
import pandas as pd
import pytest
from vigil_ml.baselines import (
    GradientBoostingBaseline,
    PrevalenceBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)


@pytest.fixture
def mock_dataset():
    rng = np.random.default_rng(42)
    n = 100
    X = pd.DataFrame(
        {
            "eval_day": rng.uniform(0, 360, n),
            "age": rng.normal(50, 10, n),
            "is_er_pos": rng.binomial(1, 0.6, n),
            "is_pr_pos": rng.binomial(1, 0.5, n),
            "is_her2_pos": rng.binomial(1, 0.2, n),
            "is_stage_3_or_4": rng.binomial(1, 0.5, n),
            "ca_15_3_curr": rng.uniform(15, 60, n),
            "ca_15_3_slope_90d": rng.normal(0.02, 0.05, n),
            "cea_curr": rng.uniform(1, 10, n),
            "cea_slope_90d": rng.normal(0.01, 0.02, n),
            "alt_curr": rng.uniform(15, 45, n),
            "max_symptom_grade": rng.choice([0, 1, 2, 3], n),
        }
    )
    # Target recurrence probability linked to ca_15_3 and stage
    z = (X["ca_15_3_curr"] - 30.0) / 10.0 + X["is_stage_3_or_4"] * 0.8
    p = 1.0 / (1.0 + np.exp(-z))
    y = pd.Series(rng.binomial(1, p), name="target")
    return X, y


def test_prevalence_baseline(mock_dataset):
    X, y = mock_dataset
    model = PrevalenceBaseline().fit(X, y)
    assert model.target_contract_ is None  # no metadata is invented for untagged labels
    preds = model.predict_risk(X)
    assert len(preds) == len(X)
    assert np.all(preds == float(np.mean(y)))


def test_single_threshold_baseline(mock_dataset):
    X, y = mock_dataset
    model = SingleThresholdBaseline(cutoff=30.0)
    model.fit(X, y)
    preds = model.predict_risk(X)
    # Higher marker level must strictly increase predicted risk
    high_marker_idx = X["ca_15_3_curr"] >= 45.0
    low_marker_idx = X["ca_15_3_curr"] <= 20.0
    assert np.mean(preds[high_marker_idx]) > np.mean(preds[low_marker_idx])


def test_velocity_baseline(mock_dataset):
    X, y = mock_dataset
    model = VelocityBaseline(velocity_cutoff=0.05)
    model.fit(X, y)
    preds = model.predict_risk(X)
    assert np.all((preds >= 0.0) & (preds <= 1.0))


def test_regularized_cox_hazard_baseline(mock_dataset):
    X, y = mock_dataset
    model = RegularizedCoxHazardBaseline().fit(X, y)
    preds = model.predict_risk(X)
    assert len(preds) == len(X)
    assert np.all((preds >= 0.0) & (preds <= 1.0))


def test_gradient_boosting_baseline(mock_dataset):
    X, y = mock_dataset
    model = GradientBoostingBaseline(n_estimators=30).fit(X, y)
    preds = model.predict_risk(X)
    assert len(preds) == len(X)
    assert np.all((preds >= 0.0) & (preds <= 1.0))


@pytest.mark.parametrize(
    "model_type",
    [PrevalenceBaseline, SingleThresholdBaseline, VelocityBaseline],
)
def test_rule_baselines_reject_misaligned_training_labels(mock_dataset, model_type):
    X, y = mock_dataset
    with pytest.raises(ValueError, match="same number of rows"):
        model_type().fit(X.iloc[:-1], y)


def test_rule_baselines_reject_multidimensional_sample_weights(mock_dataset):
    X, y = mock_dataset
    with pytest.raises(ValueError, match="one-dimensional"):
        PrevalenceBaseline().fit(X, y, sample_weight=np.ones((len(y), 1)))


def test_classifier_baselines_reject_multidimensional_labels(mock_dataset):
    X, y = mock_dataset
    with pytest.raises(ValueError, match="one-dimensional"):
        RegularizedCoxHazardBaseline().fit(X, pd.DataFrame({"target": y}))


@pytest.mark.parametrize(
    "model_type",
    [
        PrevalenceBaseline,
        SingleThresholdBaseline,
        VelocityBaseline,
        RegularizedCoxHazardBaseline,
        GradientBoostingBaseline,
    ],
)
def test_baselines_reject_ignored_fit_options(mock_dataset, model_type):
    X, y = mock_dataset
    with pytest.raises(TypeError, match="Unsupported fit options"):
        model_type().fit(X, y, horizon_days=180)


@pytest.mark.parametrize(
    "model_type",
    [
        PrevalenceBaseline,
        SingleThresholdBaseline,
        VelocityBaseline,
        RegularizedCoxHazardBaseline,
        GradientBoostingBaseline,
    ],
)
def test_baselines_retain_explicit_target_contract(mock_dataset, model_type):
    X, y = mock_dataset
    y.attrs.update(
        target_estimand="observed_diagnosis",
        horizon_days=180.0,
        synthetic_only=True,
    )
    model = model_type().fit(X, y)
    assert model.target_contract_ is not None
    assert model.target_contract_.estimand == "observed_diagnosis"
    assert model.target_contract_.horizon_days == 180.0
    assert model.target_contract_.synthetic_only is True


def test_baselines_reject_partial_or_boolean_target_contract(mock_dataset):
    X, y = mock_dataset
    y.attrs["target_estimand"] = "observed_diagnosis"
    with pytest.raises(ValueError, match="target_estimand and horizon_days"):
        PrevalenceBaseline().fit(X, y)

    y.attrs["horizon_days"] = True
    with pytest.raises(ValueError, match="target horizon_days.*boolean"):
        PrevalenceBaseline().fit(X, y)
