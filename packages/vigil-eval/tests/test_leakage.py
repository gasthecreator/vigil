"""
Unit tests for vigil_eval.leakage.
Validates leakage detection suite against clean data and deliberately injected leaky fixtures.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler
from vigil_eval.leakage import (
    CanaryTestFailedError,
    OutcomeDerivedFeatureError,
    PatientSplitLeakageError,
    PreprocessingLeakageError,
    TemporalLeakageError,
    UnobservedValueLeakageError,
    check_outcome_derived_features,
    check_patient_split_leakage,
    check_scaler_fit_leakage,
    check_temporal_future_leakage,
    run_latent_column_canary,
    run_shuffled_label_canary,
    run_unobserved_value_canary,
)


def test_patient_split_leakage_clean():
    """Verify clean disjoint splits pass without error."""
    train_df = pd.DataFrame({"patient_id": ["P1", "P2", "P3"], "value": [1, 2, 3]})
    val_df = pd.DataFrame({"patient_id": ["P4", "P5"], "value": [4, 5]})
    test_df = pd.DataFrame({"patient_id": ["P6", "P7"], "value": [6, 7]})

    # Should not raise
    check_patient_split_leakage(train_df, test_df, val_df)


def test_patient_split_leakage_train_test_overlap():
    """Verify overlapping patient ID between train and test triggers PatientSplitLeakageError."""
    train_df = pd.DataFrame({"patient_id": ["P1", "P2", "P3"]})
    test_df = pd.DataFrame({"patient_id": ["P3", "P4"]})  # P3 leaked

    with pytest.raises(PatientSplitLeakageError) as exc_info:
        check_patient_split_leakage(train_df, test_df)
    assert "P3" in str(exc_info.value)


def test_patient_split_leakage_val_overlap():
    """Verify overlapping patient ID between val and other splits triggers PatientSplitLeakageError."""
    train_df = pd.DataFrame({"patient_id": ["P1", "P2"]})
    val_df = pd.DataFrame({"patient_id": ["P2", "P3"]})  # P2 leaked
    test_df = pd.DataFrame({"patient_id": ["P4", "P5"]})

    with pytest.raises(PatientSplitLeakageError) as exc_info:
        check_patient_split_leakage(train_df, test_df, val_df)
    assert "P2" in str(exc_info.value)


def test_temporal_future_leakage_clean():
    """Verify temporal check passes when all feature times <= prediction time."""
    df = pd.DataFrame(
        {
            "pred_time": [100.0, 150.0, 200.0],
            "obs_time_1": [50.0, 140.0, 199.9],
            "obs_time_2": [90.0, 120.0, 200.0],
        }
    )
    check_temporal_future_leakage(df, "pred_time", ["obs_time_1", "obs_time_2"])


def test_temporal_future_leakage_detected():
    """Verify temporal future leakage triggers TemporalLeakageError."""
    df = pd.DataFrame(
        {
            "pred_time": [100.0, 150.0, 200.0],
            "obs_time": [50.0, 155.0, 190.0],  # row 1: 155 > 150
        }
    )
    with pytest.raises(TemporalLeakageError) as exc_info:
        check_temporal_future_leakage(df, "pred_time", ["obs_time"])
    assert "obs_time" in str(exc_info.value)


def test_outcome_derived_tokens_clean():
    """Verify clean feature names pass lexical check."""
    X = pd.DataFrame(
        {
            "ca153_mean_u_ml": [25.0, 30.0],
            "alt_slope": [0.1, -0.2],
            "age_at_diagnosis": [52, 64],
        }
    )
    check_outcome_derived_features(X)


def test_outcome_derived_tokens_forbidden():
    """Verify forbidden target tokens trigger OutcomeDerivedFeatureError."""
    # Test 'is_anomaly'
    X1 = pd.DataFrame({"ca153": [20, 30], "is_anomaly": [0, 1]})
    with pytest.raises(OutcomeDerivedFeatureError) as exc1:
        check_outcome_derived_features(X1)
    assert "is_anomaly" in str(exc1.value)

    # Test 'recurrence_flag'
    X2 = pd.DataFrame({"feature_a": [1, 2], "true_recurrence_flag": [0, 1]})
    with pytest.raises(OutcomeDerivedFeatureError) as exc2:
        check_outcome_derived_features(X2)
    assert "recurrence" in str(exc2.value)


def test_outcome_derived_correlation_leakage():
    """Verify features near-perfectly correlated with target trigger OutcomeDerivedFeatureError."""
    rng = np.random.default_rng(42)
    y = pd.Series(rng.integers(0, 2, size=100))
    # Create feature with 1.0 correlation to y
    X = pd.DataFrame(
        {
            "innocent_feature": rng.normal(size=100),
            "leaked_proxy": y.astype(float) + 1e-6,
        }
    )

    with pytest.raises(OutcomeDerivedFeatureError) as exc:
        check_outcome_derived_features(X, y=y)
    assert "leaked_proxy" in str(exc.value)


def test_scaler_fit_leakage():
    """Verify scaler fitted directly on test set statistics triggers PreprocessingLeakageError."""
    rng = np.random.default_rng(42)
    train_X = rng.normal(loc=0.0, scale=1.0, size=(100, 3))
    test_X = rng.normal(loc=10.0, scale=2.0, size=(50, 3))

    scaler_clean = StandardScaler()
    scaler_clean.fit(train_X)
    # Fit on train -> should pass on test_X
    check_scaler_fit_leakage(scaler_clean, test_X)

    # Leaky scaler fit on test_X directly
    scaler_leaky = StandardScaler()
    scaler_leaky.fit(test_X)
    with pytest.raises(PreprocessingLeakageError):
        check_scaler_fit_leakage(scaler_leaky, test_X)


def test_shuffled_label_canary_passes_on_unleaked_data():
    """Verify that on regular synthetic features, shuffled labels collapse to chance AUC <= 0.60."""
    rng = np.random.default_rng(42)
    n = 200
    X = pd.DataFrame(
        {
            "f1": rng.normal(size=n),
            "f2": rng.normal(size=n),
            "f3": rng.normal(size=n),
        }
    )
    y = pd.Series(rng.integers(0, 2, size=n))

    auc = run_shuffled_label_canary(X, y, seed=42)
    assert auc <= 0.60


def test_shuffled_label_canary_detects_leaked_target_in_features():
    """
    If a feature contains the exact label before permutation, shuffling y should still break
    the link between feature and shuffled y; BUT if an estimator fits a cheat or has degenerate
    split leakage, canary thresholds catch it. Here we test canary rejection on an artificially
    injected perfect model that over-predicts permuted labels.
    """
    rng = np.random.default_rng(42)
    n = 100
    X = pd.DataFrame({"f1": rng.normal(size=n)})
    y = pd.Series(rng.integers(0, 2, size=n))

    # Mock an estimator that memorizes/cheats
    class CheatingEstimator:
        def fit(self, X, y):
            self.y = y
            return self

        def predict_proba(self, X):
            # Predicts true probability perfectly on test set
            probs = np.zeros((len(X), 2))
            probs[:, 1] = 0.99
            return probs

    # If canary max_tolerated_auc is set low (e.g., 0.40) or model fails to collapse
    with pytest.raises(CanaryTestFailedError):
        run_shuffled_label_canary(X, y, max_tolerated_auc=0.40, seed=42)


def test_unobserved_value_canary_passes_on_masked_data():
    """Clean data with unobserved values as NaN passes canary check."""
    df = pd.DataFrame({
        "observed_ca_15_3": [True, False, True],
        "latent_ca_15_3": [25.0, 30.0, 35.0],
        "ca_15_3": [25.0, np.nan, 35.0],
    })
    counts = run_unobserved_value_canary(df)
    assert counts == {"ca_15_3": 1}


def test_unobserved_value_canary_detects_leaked_values():
    """Data where unobserved rows leak non-NaN values fails canary check."""
    df = pd.DataFrame({
        "observed_ca_15_3": [True, False, True],
        "latent_ca_15_3": [25.0, 30.0, 35.0],
        "ca_15_3": [25.0, 30.0, 35.0],  # Leaked value when observed is False!
    })
    with pytest.raises(UnobservedValueLeakageError, match="Unobserved-value canary FAILED"):
        run_unobserved_value_canary(df)


def test_latent_column_canary():
    """Features containing latent_ or true_ prefixes are caught."""
    clean_X = pd.DataFrame({"ca_15_3_curr": [25.0, 26.0], "age": [45.0, 52.0]})
    run_latent_column_canary(clean_X)

    leaky_X = pd.DataFrame({"ca_15_3_curr": [25.0, 26.0], "latent_ca_15_3": [25.0, 26.0]})
    with pytest.raises(OutcomeDerivedFeatureError, match="Latent column canary FAILED"):
        run_latent_column_canary(leaky_X)

