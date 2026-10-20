"""
Tests for vigil_eval.metrics: Survival metrics, IPCW, DCA, and Calibration.
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.1) and docs/ML_PROGRAM.md §5.
"""

import numpy as np
from vigil_eval.metrics import (
    compute_calibration_curve,
    compute_ipcw_weights,
    compute_kaplan_meier,
    ipcw_brier_score,
    ipcw_time_dependent_roc_auc,
    patient_landmark_ipcw_weights,
    survival_decision_curve_analysis,
)


def test_kaplan_meier_analytical_reference():
    """
    Verifies Kaplan-Meier against standard hand-calculated textbook example:
    Times: [1, 2, 3, 4, 5]
    Events: [1, 0, 1, 1, 0] (event at 1, censored at 2, events at 3 and 4, censored at 5)
    At t=0: S=1.0
    At t=1: n=5, d=1 -> S = 1 * (4/5) = 0.8
    At t=2: n=4, d=0 -> S = 0.8
    At t=3: n=3, d=1 -> S = 0.8 * (2/3) = 0.5333...
    At t=4: n=2, d=1 -> S = 0.5333 * (1/2) = 0.2666...
    """
    times = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    events = np.array([1, 0, 1, 1, 0])

    km = compute_kaplan_meier(times, events)

    assert np.isclose(km.predict_survival(0.5)[0], 1.0)
    assert np.isclose(km.predict_survival(1.0)[0], 0.8)
    assert np.isclose(km.predict_survival(2.5)[0], 0.8)
    assert np.isclose(km.predict_survival(3.0)[0], 0.8 * (2.0 / 3.0))
    assert np.isclose(km.predict_survival(4.0)[0], 0.8 * (2.0 / 3.0) * 0.5)


def test_ipcw_weights_properties():
    """
    Verifies that IPCW weights:
    - Are non-negative
    - Equal 0 for patients censored prior to horizon
    - Are >= 1.0 for uncensored observations
    """
    times = np.array([50.0, 100.0, 150.0, 200.0, 300.0])
    events = np.array([1, 0, 1, 0, 1])
    horizon = 180.0

    weights = compute_ipcw_weights(times, events, horizon)

    assert len(weights) == 5
    assert np.all(weights >= 0.0)
    # Patient 2 was censored at t=100 (< 180), so weight must be 0
    assert weights[1] == 0.0
    # Patient 1 had event at t=50 (< 180), weight >= 1.0
    assert weights[0] >= 1.0
    # Patient 4 survived to t=200 (> 180), weight >= 1.0
    assert weights[3] >= 1.0


def test_kaplan_meier_preserves_zero_survival_without_probability_floor():
    km = compute_kaplan_meier(np.array([1.0, 2.0]), np.array([0, 1]))
    assert km.predict_survival(2.0)[0] == 0.0


def test_ipcw_weights_are_not_truncated_at_a_hidden_cap():
    # 10,000 censoring events leave one subject at risk. The registered KM
    # estimate is 1/10,001, so its inverse must remain 10,001, not be capped.
    censor_times = np.arange(1.0, 10_001.0)
    times = np.concatenate((censor_times, np.array([10_001.0])))
    events = np.concatenate((np.zeros(len(censor_times), dtype=int), np.array([1])))
    weights = compute_ipcw_weights(times, events, horizon_time=10_000.0)
    assert np.isclose(weights[-1], 10_001.0, rtol=1e-12)


def test_competing_events_resolve_recurrence_status_without_being_censoring():
    times = np.array([50.0, 100.0, 200.0])
    event_codes = np.array([2, 1, 0])  # competing, recurrence, administrative censor
    weights = compute_ipcw_weights(times, event_codes, horizon_time=150.0)
    assert weights[0] > 0.0
    assert weights[1] > 0.0
    assert weights[2] > 0.0

    scores = np.array([0.1, 0.9, 0.2])
    assert ipcw_time_dependent_roc_auc(scores, times, event_codes, 150.0) == 1.0
    assert ipcw_brier_score(np.array([0.05, 0.95, 0.05]), times, event_codes, 150.0) < 0.01


def test_patient_landmark_weights_equalize_total_patient_contribution():
    times = np.array([50.0, 200.0, 100.0, 300.0, 80.0])
    events = np.array([1, 0, 2, 0, 2])
    patient_ids = np.array(["A", "A", "B", "B", "C"])
    weights = patient_landmark_ipcw_weights(times, events, 150.0, patient_ids)
    totals = [weights[patient_ids == patient].sum() for patient in ("A", "B", "C")]
    assert totals[0] > 0.0
    assert np.allclose(totals, totals[0])


def test_ipcw_time_dependent_roc_auc():
    """Verifies that IPCW ROC-AUC correctly discriminates high-risk vs low-risk cases."""
    rng = np.random.default_rng(42)
    n = 200
    horizon = 180.0

    # True event times: half fast recurrences (< 180), half slow (> 180)
    true_times = np.concatenate(
        [
            rng.uniform(30.0, 170.0, n // 2),
            rng.uniform(200.0, 600.0, n // 2),
        ]
    )
    # Events observed with ~15% random censoring
    censoring_times = rng.uniform(100.0, 700.0, n)
    follow_up = np.minimum(true_times, censoring_times)
    events = (true_times <= censoring_times).astype(int)

    # Perfect predictor: high score for early recurrences
    perfect_scores = 1.0 / (true_times + 1.0)
    auc_perfect = ipcw_time_dependent_roc_auc(perfect_scores, follow_up, events, horizon)
    assert auc_perfect > 0.90, f"Expected high AUC for near-perfect predictor, got {auc_perfect}"

    # Random noise predictor: AUC near 0.50
    noise_scores = rng.uniform(0.0, 1.0, n)
    auc_noise = ipcw_time_dependent_roc_auc(noise_scores, follow_up, events, horizon)
    assert 0.40 <= auc_noise <= 0.60, f"Expected chance AUC ~0.50, got {auc_noise}"


def test_ipcw_brier_score():
    """Verifies that accurate predictions yield lower Brier score than inverted predictions."""
    rng = np.random.default_rng(42)
    n = 150
    horizon = 180.0

    times = rng.uniform(50.0, 400.0, n)
    events = rng.binomial(1, 0.7, n)

    # True binary status at horizon (ignoring censoring for ground-truth simulation)
    is_case = (times <= horizon) & (events == 1)
    good_preds = np.where(is_case, 0.85, 0.15)
    bad_preds = np.where(is_case, 0.15, 0.85)

    bs_good = ipcw_brier_score(good_preds, times, events, horizon)
    bs_bad = ipcw_brier_score(bad_preds, times, events, horizon)

    assert bs_good < bs_bad, (
        f"Good predictor Brier {bs_good} should be lower than bad predictor {bs_bad}"
    )


def test_survival_decision_curve_analysis():
    """Verifies Decision Curve Analysis calculation and structure."""
    rng = np.random.default_rng(42)
    n = 200
    horizon = 180.0

    times = rng.uniform(30.0, 400.0, n)
    events = rng.binomial(1, 0.5, n)
    risks = rng.uniform(0.05, 0.45, n)

    dca = survival_decision_curve_analysis(risks, times, events, horizon)

    assert len(dca.thresholds) == 50
    assert len(dca.net_benefit_model) == 50
    assert len(dca.net_benefit_all) == 50
    assert np.all(dca.net_benefit_none == 0.0)


def test_calibration_curve_and_ece():
    """Verifies Expected Calibration Error computation on calibrated vs miscalibrated predictions."""
    rng = np.random.default_rng(42)
    n = 1000

    # Generate genuinely calibrated probabilities: Y ~ Bernoulli(P)
    calibrated_probs = rng.uniform(0.05, 0.95, n)
    labels = rng.binomial(1, calibrated_probs)

    calib = compute_calibration_curve(calibrated_probs, labels, n_bins=10)
    assert calib.expected_calibration_error < 0.06, (
        f"Calibrated probabilities ECE {calib.expected_calibration_error} unexpectedly high"
    )

    # Severely miscalibrated predictions (constant overconfidence)
    overconfident_probs = np.full(n, 0.90)
    calib_bad = compute_calibration_curve(overconfident_probs, labels, n_bins=5)
    assert calib_bad.expected_calibration_error > 0.20


def test_undefined_ipcw_metrics_are_nan_not_plausible_scores():
    times = np.array([10.0, 20.0])
    events = np.array([0, 0])
    scores = np.array([0.2, 0.8])
    assert np.isnan(ipcw_time_dependent_roc_auc(scores, times, events, horizon_time=30.0))
    assert np.isnan(ipcw_brier_score(scores, times, events, horizon_time=30.0))
