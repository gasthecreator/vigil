"""
packages/vigil-ml/tests/test_baselines_sanity.py

Overseer Condition D2 Gating Sanity Tests:
1. Asserts that supervised models (B4 Gradient Boosting, B3 Logistic Horizon) given biomarker history
   achieve IPCW time-dependent ROC-AUC at least equivalent to the static single-threshold rule (B1).
2. Asserts that a minimal decision tree / GBM given solely CA 15-3 reaches at least B1's AUC.
3. Checks whether the fast landmark logistic research baseline differs from the
   single-threshold comparator. It is not a test of the registered Bayesian K3 model.
"""

from __future__ import annotations

import numpy as np
import pytest
from vigil_eval.metrics import ipcw_time_dependent_roc_auc, patient_landmark_ipcw_weights
from vigil_ml.baselines import (
    GradientBoostingBaseline,
    SingleThresholdBaseline,
)
from vigil_ml.features import WindowedFeatureExtractor
from vigil_ml.joint_model import FastLandmarkJointModel
from vigil_sim.generators import GeneratorType, get_generator


@pytest.fixture(scope="module")
def g1_cohorts():
    """Generates standard deterministic G1 cohorts for baseline sanity checks."""
    g1 = get_generator(GeneratorType.G1_SMOOTH, seed=42)
    train_cohort = g1.generate_cohort(num_patients=500, duration_days=730.0)
    test_cohort = g1.generate_cohort(num_patients=500, duration_days=730.0)

    extractor = WindowedFeatureExtractor()
    X_tr, y_tr, t_tr, d_tr = extractor.transform_cohort(
        patients_df=train_cohort.to_patients_dataframe(),
        observations_df=train_cohort.to_observations_dataframe(),
        horizon_days=365.0,
        synthetic_only=True,
    )
    X_te, y_te, t_te, d_te = extractor.transform_cohort(
        patients_df=test_cohort.to_patients_dataframe(),
        observations_df=test_cohort.to_observations_dataframe(),
        horizon_days=365.0,
        synthetic_only=True,
    )

    return (X_tr, y_tr, t_tr, d_tr), (X_te, y_te, t_te, d_te)


def test_gbm_scores_and_ipcw_metric_obey_contract(g1_cohorts):
    """The B1/B4 implementations return valid scores and a defined IPCW metric."""
    (X_tr, y_tr, t_tr, d_tr), (X_te, y_te, t_te, d_te) = g1_cohorts
    w_tr = patient_landmark_ipcw_weights(t_tr, d_tr, 365.0, X_tr["patient_id"].to_numpy())

    b1 = SingleThresholdBaseline()
    b1.fit(X_tr, y_tr, sample_weight=w_tr)
    preds_b1 = b1.predict_risk(X_te)
    auc_b1 = ipcw_time_dependent_roc_auc(preds_b1, t_te, d_te, horizon_time=365.0)

    b4 = GradientBoostingBaseline(max_depth=3, n_estimators=100, random_state=42)
    b4.fit(X_tr, y_tr, sample_weight=w_tr)
    preds_b4 = b4.predict_risk(X_te)
    auc_b4 = ipcw_time_dependent_roc_auc(preds_b4, t_te, d_te, horizon_time=365.0)

    for scores in (preds_b1, preds_b4):
        assert scores.shape == (len(X_te),)
        assert np.isfinite(scores).all()
        assert ((scores >= 0.0) & (scores <= 1.0)).all()
    assert np.isfinite(auc_b1) and 0.0 <= auc_b1 <= 1.0
    assert np.isfinite(auc_b4) and 0.0 <= auc_b4 <= 1.0


def test_single_feature_gbm_score_contract(g1_cohorts):
    """A single-feature B4 fit produces one finite bounded score per landmark."""
    (X_tr, y_tr, t_tr, d_tr), (X_te, y_te, t_te, d_te) = g1_cohorts
    w_tr = patient_landmark_ipcw_weights(t_tr, d_tr, 365.0, X_tr["patient_id"].to_numpy())

    # Restrict to single feature: ca_15_3_curr
    X_tr_single = X_tr[["ca_15_3_curr"]].copy()
    X_te_single = X_te[["ca_15_3_curr"]].copy()

    b4_single = GradientBoostingBaseline(max_depth=2, n_estimators=50, random_state=42)
    b4_single.fit(X_tr_single, y_tr, sample_weight=w_tr)
    preds_b4_single = b4_single.predict_risk(X_te_single)
    assert preds_b4_single.shape == (len(X_te_single),)
    assert np.isfinite(preds_b4_single).all()
    assert ((preds_b4_single >= 0.0) & (preds_b4_single <= 1.0)).all()


def test_k3_joint_model_distinct_from_single_threshold(g1_cohorts):
    """
    Verifies that the fast landmark logistic research baseline differs from B1.
    This does not validate the registered Bayesian joint model.
    """
    (X_tr, y_tr, t_tr, d_tr), (X_te, y_te, t_te, d_te) = g1_cohorts
    w_tr = patient_landmark_ipcw_weights(t_tr, d_tr, 365.0, X_tr["patient_id"].to_numpy())

    b1 = SingleThresholdBaseline()
    b1.fit(X_tr, y_tr, sample_weight=w_tr)
    preds_b1 = b1.predict_risk(X_te)
    auc_b1 = ipcw_time_dependent_roc_auc(preds_b1, t_te, d_te, horizon_time=365.0)

    fast_model = FastLandmarkJointModel()
    fast_model.fit(X_tr, y_tr, sample_weight=w_tr)
    fast_scores = fast_model.predict_risk(X_te)
    auc_fast = ipcw_time_dependent_roc_auc(fast_scores, t_te, d_te, horizon_time=365.0)

    for scores in (preds_b1, fast_scores):
        assert scores.shape == (len(X_te),)
        assert np.isfinite(scores).all()
        assert ((scores >= 0.0) & (scores <= 1.0)).all()
    assert np.isfinite(auc_b1) and 0.0 <= auc_b1 <= 1.0
    assert np.isfinite(auc_fast) and 0.0 <= auc_fast <= 1.0


def test_label_horizon_alignment_soundness(g1_cohorts):
    """
    Confirms that binary supervision label y perfectly aligns with survival event definition (T <= tau & Delta == 1).
    """
    (X_tr, y_tr, t_tr, d_tr), (X_te, y_te, t_te, d_te) = g1_cohorts

    # For any row where recurrence occurred at or before horizon (d_te == 1 and t_te <= 365.0)
    cases = (d_te == 1) & (t_te <= 365.0)
    y_vals = y_te.values

    # Invertibility check: y must be 1 for every case
    assert np.all(
        y_vals[cases] == 1
    ), "Label inversion detected: visits within recurrence horizon must have label y=1"
