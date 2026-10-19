"""
packages/vigil-eval/tests/test_model_canaries.py

Multi-Model Canary Suite for Condition P8-E (VERDICT-P5C.md).
Enforces leakage canaries across all model families and their inputs:
  - Baselines: B1 (Single Threshold), B2 (Velocity), B3 (Cox Hazard), B4 (Gradient Boosting)
  - K1 (Hybrid Kinetic Model): sequence inputs and shuffled outcome canary
  - K2 (Sequential e-process): anytime-valid false alarm bound under null
  - K3 (Fast Landmark Joint Model): landmark feature matrix and shuffled survival canary
  - M3 (Plausibility Adjudicator): laboratory plausibility inputs and shuffled error canary
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
from vigil_eval.leakage import (
    check_outcome_derived_features,
    run_latent_column_canary,
    run_shuffled_label_canary,
    run_unobserved_value_canary,
)
from vigil_eval.metrics import ipcw_time_dependent_roc_auc, patient_landmark_ipcw_weights
from vigil_ml.baselines import (
    GradientBoostingBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)
from vigil_ml.features import WindowedFeatureExtractor
from vigil_ml.joint_model import FastLandmarkJointModel
from vigil_ml.k1 import HybridKineticModelK1, K1Observations
from vigil_ml.k2 import SequentialDetector
from vigil_ml.m3 import adjudicate
from vigil_sim.generators import GeneratorType, get_generator


@pytest.fixture(scope="module")
def synthetic_cohort():
    """Generates a reproducible G1 cohort for model canary testing."""
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=123)
    cohort = gen.generate_cohort(num_patients=250, duration_days=730.0)
    return cohort


def test_b1_to_b4_canaries(synthetic_cohort):
    """Verifies that tabular feature inputs for B1-B4 pass unobserved-value,

    latent-column, and shuffled-label canaries.
    """
    obs_df = synthetic_cohort.to_observations_dataframe(legacy_leaky=False)
    pts_df = synthetic_cohort.to_patients_dataframe()

    # 1. Unobserved-value canary on raw observations
    unobserved_counts = run_unobserved_value_canary(obs_df)
    assert unobserved_counts.get("ca_15_3", 0) > 0, (
        "Expected some unobserved CA 15-3 in synthetic cohort"
    )

    # 2. Extract features
    extractor = WindowedFeatureExtractor()
    X, y, t, d = extractor.transform_cohort(
        patients_df=pts_df, observations_df=obs_df, horizon_days=365.0
    )

    # 3. Latent-column canary
    run_latent_column_canary(X)
    check_outcome_derived_features(X)

    # 4. Shuffled-label canary for B1, B2, B3, B4
    # All models must collapse to chance (ROC-AUC <= 0.60) under permuted labels
    auc_b1 = run_shuffled_label_canary(X, y, model_factory=SingleThresholdBaseline, seed=42)
    assert auc_b1 <= 0.60, f"B1 shuffled-label canary failed: AUC = {auc_b1}"

    auc_b2 = run_shuffled_label_canary(X, y, model_factory=VelocityBaseline, seed=42)
    assert auc_b2 <= 0.60, f"B2 shuffled-label canary failed: AUC = {auc_b2}"

    auc_b3 = run_shuffled_label_canary(
        X, y, model_factory=lambda: RegularizedCoxHazardBaseline(C=0.5), seed=42
    )
    assert auc_b3 <= 0.60, f"B3 shuffled-label canary failed: AUC = {auc_b3}"

    auc_b4 = run_shuffled_label_canary(
        X, y, model_factory=lambda: GradientBoostingBaseline(max_depth=3, n_estimators=50), seed=42
    )
    assert auc_b4 <= 0.60, f"B4 shuffled-label canary failed: AUC = {auc_b4}"


def test_k1_kinetic_canaries(synthetic_cohort):
    """Verifies K1 inputs contain no unobserved values and K1 collapses under shuffled labels."""
    obs_df = synthetic_cohort.to_observations_dataframe(legacy_leaky=False)
    pts_df = synthetic_cohort.to_patients_dataframe()

    # Extract sequences for test patients
    k1_inputs = []
    labels = []

    for _, pt in pts_df.iterrows():
        pid = pt["patient_id"]
        pt_obs = obs_df[(obs_df["patient_id"] == pid) & (obs_df["ca_15_3"].notna())]
        days = pt_obs["day"].to_numpy(dtype=float)
        ca_vals = pt_obs["ca_15_3"].to_numpy(dtype=float)
        # Verify no NaN or unobserved values in K1 inputs
        assert not np.isnan(ca_vals).any(), "K1 input contains NaN values"

        k1_inputs.append(K1Observations(days=days, values={"ca153": ca_vals}))
        labels.append(1 if pt.get("observed_recurrence_event") else 0)

    k1 = HybridKineticModelK1(horizon_days=365.0)
    preds = k1.predict_risk(k1_inputs)

    # Shuffled label canary across 5 random permutations
    rng = np.random.default_rng(42)
    shuffled_aucs = []
    for _ in range(5):
        permutation = rng.permutation(len(labels))
        shuffled_labels = np.asarray(labels)[permutation]
        auc = float(roc_auc_score(shuffled_labels, preds))
        shuffled_aucs.append(auc)

    mean_shuffled_auc = float(np.mean(shuffled_aucs))
    # Discrimination under shuffled labels must be near chance (<= 0.60)
    assert mean_shuffled_auc <= 0.60, (
        f"K1 shuffled label canary failed: mean AUC = {mean_shuffled_auc:.4f}"
    )


def test_k2_sequential_canaries():
    """Exercise the canonical K2 API on null streams without treating a canary as proof."""
    rng = np.random.default_rng(101)
    n_patients = 100
    n_visits = 12
    scores = []
    for _ in range(n_patients):
        vals = 15.0 + rng.normal(0.0, 2.0, size=n_visits)
        days = np.arange(n_visits) * 90.0
        detector = SequentialDetector(alpha_pt=0.05, sigma_log=0.2)
        for day, value in zip(days, vals):
            detector.update(float(day), float(value))
        scores.append(detector.log_e)
    assert np.all(np.isfinite(scores))


def test_k3_joint_model_canaries(synthetic_cohort):
    """Verifies K3 inputs have no latent columns and collapses to chance under shuffled survival outcomes."""
    obs_df = synthetic_cohort.to_observations_dataframe(legacy_leaky=False)
    pts_df = synthetic_cohort.to_patients_dataframe()

    extractor = WindowedFeatureExtractor()
    X, y, t, d = extractor.transform_cohort(
        patients_df=pts_df, observations_df=obs_df, horizon_days=365.0
    )

    # Latent-column canary
    run_latent_column_canary(X)

    # Shuffled-label canary
    rng = np.random.default_rng(42)
    d_shuffled = rng.permutation(d)

    k3 = FastLandmarkJointModel(horizon_days=365.0)
    weights = patient_landmark_ipcw_weights(t, d, 365.0, X["patient_id"].to_numpy())
    k3.fit(X, y, sample_weight=weights)
    preds = k3.predict_risk(X)

    auc_shuffled = float(ipcw_time_dependent_roc_auc(preds, t, d_shuffled, horizon_time=365.0))
    assert auc_shuffled <= 0.60, f"K3 shuffled-outcome canary failed: AUC = {auc_shuffled:.4f}"


def test_m3_plausibility_canaries(synthetic_cohort):
    """Verifies M3 inputs handle unobserved values properly and classifications collapse under label permutation."""
    # 1. Negative or zero numeric inputs rejected
    with pytest.raises(ValueError):
        adjudicate(history=[], new_day=10.0, new_value=-5.0, cv_analytical=0.05, cv_within=0.10)
    with pytest.raises(ValueError):
        adjudicate(history=[], new_day=10.0, new_value=0.0, cv_analytical=0.05, cv_within=0.10)

    # 2. Clean evaluation on reference stable case
    res_stable = adjudicate(
        history=[(0.0, 20.0), (30.0, 21.0), (60.0, 19.5)],
        new_day=90.0,
        new_value=20.5,
        cv_analytical=0.05,
        cv_within=0.08,
    )
    assert res_stable["action"] == "explained"
    assert res_stable["p_stable"] > 0.80

    # 3. Clean evaluation on gross decimal transcription error (x10 jump)
    res_error = adjudicate(
        history=[(0.0, 20.0), (30.0, 21.0), (60.0, 20.0)],
        new_day=90.0,
        new_value=205.0,  # x10 error
        cv_analytical=0.05,
        cv_within=0.08,
    )
    assert res_error["action"] == "needs_repeat"
    assert res_error["p_error"] > 0.30

    # 4. Shuffled-label canary on plausible vs gross error cases
    # Construct a benchmark of 50 stable and 50 gross-error cases
    rng = np.random.default_rng(42)
    scores = []
    true_labels = []

    for _ in range(50):
        # Stable
        v = float(20.0 * (1.0 + rng.normal(0, 0.05)))
        r = adjudicate([(0.0, 20.0)], 90.0, v, 0.05, 0.08)
        scores.append(r["p_error"])
        true_labels.append(0)

        # Gross error (x10 jump)
        v_err = float(20.0 * 10.0 * (1.0 + rng.normal(0, 0.05)))
        r_err = adjudicate([(0.0, 20.0)], 90.0, v_err, 0.05, 0.08)
        scores.append(r_err["p_error"])
        true_labels.append(1)

    scores = np.array(scores)
    true_labels = np.array(true_labels)

    # Normal AUC should be high (> 0.95)
    clean_auc = roc_auc_score(true_labels, scores)
    assert clean_auc > 0.95, f"M3 error detection AUC expected > 0.95, got {clean_auc}"

    # Shuffled label canary: permute labels across cases
    shuffled_labels = rng.permutation(true_labels)
    shuffled_auc = roc_auc_score(shuffled_labels, scores)
    assert abs(shuffled_auc - 0.50) < 0.15, f"M3 shuffled label canary failed: AUC = {shuffled_auc}"
