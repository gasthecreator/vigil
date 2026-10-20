"""
vigil_eval.metrics

Core survival, time-dependent, and clinical utility evaluation metrics for Vigil.
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.1) and docs/ML_PROGRAM.md §5.

Includes:
- Kaplan-Meier censoring distribution estimation
- Inverse Probability of Censoring Weighting (IPCW)
- IPCW time-dependent ROC-AUC (Uno et al. 2007)
- IPCW time-dependent Brier score
- Survival Decision Curve Analysis (DCA Net Benefit)
- Calibration curves and Expected Calibration Error (ECE)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, cast

import numpy as np
from numpy.typing import NDArray


def _probability_vector(values: np.ndarray, name: str) -> NDArray[np.float64]:
    """Validate probabilities without silently repairing invalid model output."""
    probabilities = np.asarray(values, dtype=float)
    if probabilities.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional probability array")
    if not np.isfinite(probabilities).all() or np.any(
        (probabilities < 0.0) | (probabilities > 1.0)
    ):
        raise ValueError(f"{name} must contain finite probabilities in [0, 1]")
    return probabilities


@dataclass
class KaplanMeierEstimate:
    """Estimated Kaplan-Meier survival/censoring curve."""

    times: np.ndarray  # Unique event/censoring times (sorted)
    survival_prob: np.ndarray  # Estimated S(t) = P(T > t)

    def predict_survival(self, t: float | np.ndarray) -> NDArray[np.floating]:
        """Evaluates S(t) at arbitrary query times t using right-continuous step function."""
        t_arr = np.atleast_1d(t)
        # Search sorted insertion indices
        indices = np.searchsorted(self.times, t_arr, side="right") - 1
        probs = np.zeros_like(t_arr, dtype=float)

        valid_mask = indices >= 0
        probs[valid_mask] = self.survival_prob[indices[valid_mask]]
        probs[~valid_mask] = 1.0  # Before first event, survival is 1.0

        # Preserve the estimated censoring survival exactly. A probability floor
        # changes the estimand by silently truncating IPCW weights.
        return cast(NDArray[np.floating], probs)


def compute_kaplan_meier(
    times: np.ndarray,
    events: np.ndarray,
) -> KaplanMeierEstimate:
    """
    Computes standard non-parametric Kaplan-Meier estimate.

    Parameters:
        times: Observed follow-up times (T_i).
        events: Event indicators (1 for the event in this KM curve, 0 otherwise).
    """
    if len(times) == 0:
        return KaplanMeierEstimate(times=np.array([0.0]), survival_prob=np.array([1.0]))

    order = np.argsort(times)
    sorted_times = times[order]
    sorted_events = events[order]

    unique_times, idx_start, counts = np.unique(sorted_times, return_index=True, return_counts=True)

    n_at_risk = len(times) - idx_start
    # Sum events occurring at each unique time
    n_events = np.zeros(len(unique_times), dtype=int)
    for i, (start, count) in enumerate(zip(idx_start, counts)):
        n_events[i] = np.sum(sorted_events[start : start + count])

    # Survival hazard fractions
    hazard_frac = 1.0 - (n_events / np.maximum(n_at_risk, 1))
    survival_prob = np.cumprod(hazard_frac)

    return KaplanMeierEstimate(times=unique_times, survival_prob=survival_prob)


def compute_ipcw_weights(
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
) -> np.ndarray:
    """
    Computes Inverse Probability of Censoring Weights (IPCW) at evaluation horizon t.

    Censoring distribution G(t) = P(C > t) is estimated by reversing event indicator (1 - Delta).
    Weight formulation:
    - If an event occurs by horizon: w_i = 1 / G(T_i)
    - If T_i > horizon (outcome-free past horizon): w_i = 1 / G(horizon)
    - If T_i <= horizon and Delta_i == 0 (censored prior to horizon): w_i = 0 (uninformative)
    """
    n = len(follow_up_times)
    if len(event_indicators) != n:
        raise ValueError("follow_up_times and event_indicators must have equal length")
    if not np.isfinite(follow_up_times).all() or np.any(np.asarray(follow_up_times) < 0):
        raise ValueError("follow_up_times must be finite and non-negative")
    if not np.isin(event_indicators, [0, 1, 2]).all():
        raise ValueError("event_indicators must use codes 0=censor, 1=recurrence, 2=competing event")
    weights = np.zeros(n, dtype=float)

    # Estimate censoring distribution G(t) by reversing event indicator
    # Event code: 0=censored, 1=event of interest, 2=competing event.
    # Competing events are known outcomes, not censoring observations.
    censoring_indicators = (event_indicators == 0).astype(int)
    g_km = compute_kaplan_meier(follow_up_times, censoring_indicators)

    # Only require support at the horizon for observations known to remain
    # event-free beyond it. If G is zero there, the horizon estimand is not
    # identifiable from this cohort; do not manufacture a finite weight.
    has_horizon_controls = bool(np.any(np.asarray(follow_up_times) > horizon_time))
    g_at_horizon = (
        float(g_km.predict_survival(horizon_time)[0]) if has_horizon_controls else None
    )

    def inverse_supported_probability(probability: float, at: float) -> float:
        if probability <= 0.0:
            raise ValueError(
                f"IPCW is undefined: censoring survival is zero at time {at}"
            )
        weight = 1.0 / probability
        if not np.isfinite(weight):
            raise ValueError(
                f"IPCW is undefined: inverse censoring survival is not finite at time {at}"
            )
        return weight

    for i in range(n):
        t_i = follow_up_times[i]
        d_i = event_indicators[i]

        if t_i <= horizon_time:
            if d_i in (1, 2):
                # An event of either type resolves recurrence status by horizon.
                g_ti = float(g_km.predict_survival(t_i)[0])
                weights[i] = inverse_supported_probability(g_ti, float(t_i))
            else:
                # Censored before horizon: indeterminate status
                weights[i] = 0.0
        else:
            # Survived past horizon
            # A horizon control was found above, so this probability exists.
            assert g_at_horizon is not None
            weights[i] = inverse_supported_probability(g_at_horizon, horizon_time)

    return weights


def ipcw_time_dependent_roc_auc(
    risk_scores: np.ndarray,
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
    weights: np.ndarray | None = None,
) -> float:
    """
    Computes Uno et al. (2007) Inverse Probability of Censoring Weighted time-dependent ROC-AUC.

    Evaluates recurrence cases versus patients without recurrence by t; competing events are controls.
    """
    if not (len(risk_scores) == len(follow_up_times) == len(event_indicators)):
        raise ValueError("risk scores, follow-up times, and event indicators must have equal length")
    weights = (
        compute_ipcw_weights(follow_up_times, event_indicators, horizon_time)
        if weights is None
        else np.asarray(weights, dtype=float)
    )
    if len(weights) != len(follow_up_times):
        raise ValueError("weights must have the same length as follow_up_times")
    if not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("weights must be finite and non-negative")
    if not np.isfinite(risk_scores).all():
        raise ValueError("risk_scores must be finite")

    # Identify case and control indices
    cases_mask = (follow_up_times <= horizon_time) & (event_indicators == 1) & (weights > 0)
    controls_mask = (
        ((follow_up_times > horizon_time) | (event_indicators == 2)) & (weights > 0)
    )

    if not np.any(cases_mask) or not np.any(controls_mask):
        return float("nan")

    case_scores = risk_scores[cases_mask]
    case_weights = weights[cases_mask]

    control_scores = risk_scores[controls_mask]
    control_weights = weights[controls_mask]

    # Weighted Mann-Whitney concordance in O(n log n), using cumulative control
    # weights and binary searches. The previous nested loop was quadratic and
    # made patient-cluster bootstrap studies needlessly slow.
    order = np.argsort(control_scores, kind="mergesort")
    sorted_scores = control_scores[order]
    cumulative_weights = np.concatenate(([0.0], np.cumsum(control_weights[order])))
    left = np.searchsorted(sorted_scores, case_scores, side="left")
    right = np.searchsorted(sorted_scores, case_scores, side="right")
    less_weight = cumulative_weights[left]
    equal_weight = cumulative_weights[right] - less_weight
    concordant = float(np.sum(case_weights * (less_weight + 0.5 * equal_weight)))
    total_weight = float(np.sum(case_weights) * cumulative_weights[-1])
    return concordant / total_weight if total_weight > 0 else float("nan")


def ipcw_brier_score(
    predicted_probabilities: np.ndarray,
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
    weights: np.ndarray | None = None,
) -> float:
    """
    Computes IPCW-weighted Brier score for survival horizon t (Graf et al. 1999).

    BS(t) = 1/N * sum_i [ (0 - S_i(t))^2 * I(T_i <= t, Delta_i=1) / G(T_i)
                        + (1 - S_i(t))^2 * I(T_i > t) / G(t) ]
    """
    n = len(follow_up_times)
    if len(event_indicators) != n:
        raise ValueError("follow_up_times and event_indicators must have equal length")
    if n == 0:
        return float("nan")

    # Risk of event occurring by horizon: p_i = 1 - S_i(horizon)
    p_hat = _probability_vector(predicted_probabilities, "predicted_probabilities")
    weights = (
        compute_ipcw_weights(follow_up_times, event_indicators, horizon_time)
        if weights is None
        else np.asarray(weights, dtype=float)
    )
    if len(weights) != len(follow_up_times):
        raise ValueError("weights must have the same length as follow_up_times")
    if not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("weights must be finite and non-negative")
    if not np.any(weights > 0):
        return float("nan")
    if len(p_hat) != n:
        raise ValueError("predicted_probabilities must match follow_up_times")

    # For patients experiencing recurrence by horizon, Y_i = 1; competing events
    # and event-free follow-up beyond horizon resolve Y_i = 0.
    outcome = ((follow_up_times <= horizon_time) & (event_indicators == 1)).astype(float)
    return float(np.sum(weights * (p_hat - outcome) ** 2) / n)


@dataclass
class DecisionCurveResult:
    thresholds: np.ndarray
    net_benefit_model: np.ndarray
    net_benefit_all: np.ndarray
    net_benefit_none: np.ndarray


def survival_decision_curve_analysis(
    predicted_risks: np.ndarray,
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
    thresholds: Optional[np.ndarray] = None,
) -> DecisionCurveResult:
    """
    Computes Decision Curve Analysis (DCA) Net Benefit across threshold probabilities (Vickers et al.).

    Net Benefit(p_t) = TruePositives/N - FalsePositives/N * (p_t / (1 - p_t))
    Using IPCW weights to account for right-censoring at horizon.
    """
    predicted_risks = _probability_vector(predicted_risks, "predicted_risks")
    follow_up_times = np.asarray(follow_up_times, dtype=float)
    event_indicators = np.asarray(event_indicators)
    if not (len(predicted_risks) == len(follow_up_times) == len(event_indicators)):
        raise ValueError("risks, follow-up times, and event indicators must have equal length")
    if thresholds is None:
        thresholds = np.linspace(0.01, 0.50, 50)
    else:
        thresholds = np.asarray(thresholds, dtype=float)
    if thresholds.ndim != 1 or len(thresholds) == 0:
        raise ValueError("thresholds must be a non-empty one-dimensional array")
    if not np.isfinite(thresholds).all() or np.any((thresholds <= 0.0) | (thresholds >= 1.0)):
        raise ValueError("decision thresholds must be finite and strictly between zero and one")

    n = len(predicted_risks)
    if n == 0:
        undefined = np.full(len(thresholds), np.nan)
        return DecisionCurveResult(
            thresholds=thresholds,
            net_benefit_model=undefined.copy(),
            net_benefit_all=undefined.copy(),
            net_benefit_none=undefined.copy(),
        )
    weights = compute_ipcw_weights(follow_up_times, event_indicators, horizon_time)

    is_case = (follow_up_times <= horizon_time) & (event_indicators == 1)
    is_control = (follow_up_times > horizon_time) | (event_indicators == 2)

    nb_model = []
    nb_all = []
    nb_none = np.zeros(len(thresholds), dtype=float)

    for pt in thresholds:
        harm_ratio = pt / (1.0 - pt)

        # Model policy: intervene if predicted_risk >= pt
        selected = predicted_risks >= pt
        tp_w = np.sum(weights[selected & is_case])
        fp_w = np.sum(weights[selected & is_control])

        net_b = (tp_w / n) - (fp_w / n) * harm_ratio
        nb_model.append(net_b)

        # Treat-all policy: intervene on every patient
        tp_all = np.sum(weights[is_case])
        fp_all = np.sum(weights[is_control])
        net_b_all = (tp_all / n) - (fp_all / n) * harm_ratio
        nb_all.append(net_b_all)

    return DecisionCurveResult(
        thresholds=thresholds,
        net_benefit_model=np.array(nb_model),
        net_benefit_all=np.array(nb_all),
        net_benefit_none=nb_none,
    )


@dataclass
class CalibrationReport:
    bin_centers: np.ndarray
    predicted_probs: np.ndarray
    observed_probs: np.ndarray
    bin_counts: np.ndarray
    expected_calibration_error: float
    max_calibration_error: float


def compute_calibration_curve(
    predicted_probs: np.ndarray,
    observed_labels: np.ndarray,
    n_bins: int = 10,
    strategy: str = "quantile",
) -> CalibrationReport:
    """
    Computes calibration curve and Expected Calibration Error (ECE).

    Parameters:
        predicted_probs: Predicted risk probabilities in [0, 1].
        observed_labels: Binary outcome labels (0 or 1).
        n_bins: Number of bins.
        strategy: 'quantile' (equal-sized bins) or 'uniform' (equal-width bins).
    """
    p = _probability_vector(predicted_probs, "predicted_probs")
    y = np.asarray(observed_labels, dtype=float)
    n = len(p)
    if y.ndim != 1 or len(y) != n:
        raise ValueError("predicted_probs and observed_labels must be equal-length vectors")
    if n_bins < 1:
        raise ValueError("n_bins must be at least one")
    if strategy not in {"quantile", "uniform"}:
        raise ValueError("strategy must be 'quantile' or 'uniform'")
    if not np.isfinite(y).all() or not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("observed_labels must contain finite binary values")
    if n == 0:
        return CalibrationReport(
            bin_centers=np.array([]), predicted_probs=np.array([]), observed_probs=np.array([]),
            bin_counts=np.array([], dtype=int), expected_calibration_error=float("nan"),
            max_calibration_error=float("nan"),
        )

    if strategy == "quantile":
        # Adaptive quantile bin edges
        quantiles = np.linspace(0.0, 1.0, n_bins + 1)
        bin_edges = np.unique(np.quantile(p, quantiles))
        if len(bin_edges) < 2:
            bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    else:
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)

    bin_centers = []
    mean_preds = []
    mean_obs = []
    counts = []
    weighted_diffs = []

    for i in range(len(bin_edges) - 1):
        low = bin_edges[i]
        high = bin_edges[i + 1]

        if i == len(bin_edges) - 2:
            mask = (p >= low) & (p <= high)
        else:
            mask = (p >= low) & (p < high)

        count = np.sum(mask)
        if count == 0:
            continue

        pred_mean = float(np.mean(p[mask]))
        obs_mean = float(np.mean(y[mask]))

        bin_centers.append(0.5 * (low + high))
        mean_preds.append(pred_mean)
        mean_obs.append(obs_mean)
        counts.append(count)

        diff = abs(pred_mean - obs_mean)
        weighted_diffs.append((count / n) * diff)

    ece = float(np.sum(weighted_diffs)) if weighted_diffs else 0.0
    mce = (
        float(np.max([abs(pr - ob) for pr, ob in zip(mean_preds, mean_obs)])) if mean_preds else 0.0
    )

    return CalibrationReport(
        bin_centers=np.array(bin_centers),
        predicted_probs=np.array(mean_preds),
        observed_probs=np.array(mean_obs),
        bin_counts=np.array(counts),
        expected_calibration_error=ece,
        max_calibration_error=mce,
    )


def compute_ipcw_calibration_curve(
    predicted_probs: np.ndarray,
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
    n_bins: int = 10,
    weights: np.ndarray | None = None,
) -> CalibrationReport:
    """Compute horizon calibration using censoring weights and competing-event controls."""
    p = _probability_vector(predicted_probs, "predicted_probs")
    times = np.asarray(follow_up_times, dtype=float)
    events = np.asarray(event_indicators)
    if not (len(p) == len(times) == len(events)):
        raise ValueError("Predictions and event-time arrays must have equal length")
    if n_bins < 1:
        raise ValueError("n_bins must be at least one")
    if not np.isin(events, (0, 1, 2)).all():
        raise ValueError("event_indicators must use codes 0=censor, 1=recurrence, 2=competing event")

    weights = (
        compute_ipcw_weights(times, events, horizon_time)
        if weights is None
        else np.asarray(weights, dtype=float)
    )
    if len(weights) != len(times):
        raise ValueError("weights must have the same length as follow_up_times")
    if not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("weights must be finite and non-negative")
    known = weights > 0
    if not np.any(known):
        return CalibrationReport(
            bin_centers=np.array([]), predicted_probs=np.array([]), observed_probs=np.array([]),
            bin_counts=np.array([], dtype=int), expected_calibration_error=float("nan"),
            max_calibration_error=float("nan"),
        )
    outcome = ((times <= horizon_time) & (events == 1)).astype(float)
    edges = np.unique(np.quantile(p[known], np.linspace(0.0, 1.0, n_bins + 1)))
    if len(edges) < 2:
        edges = np.array([0.0, 1.0])

    centers, predicted, observed, counts, bin_weights = [], [], [], [], []
    for i, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        mask = known & (p >= low) & ((p <= high) if i == len(edges) - 2 else (p < high))
        if not np.any(mask):
            continue
        w = weights[mask]
        total_w = float(np.sum(w))
        pred_mean = float(np.average(p[mask], weights=w))
        obs_mean = float(np.average(outcome[mask], weights=w))
        centers.append(float((low + high) / 2.0))
        predicted.append(pred_mean)
        observed.append(obs_mean)
        counts.append(int(np.sum(mask)))
        bin_weights.append(total_w)

    total_w = float(np.sum(bin_weights))
    errors = np.abs(np.asarray(predicted) - np.asarray(observed))
    ece = float(np.dot(errors, bin_weights) / total_w) if total_w else float("nan")
    mce = float(np.max(errors)) if len(errors) else float("nan")
    return CalibrationReport(
        bin_centers=np.asarray(centers),
        predicted_probs=np.asarray(predicted),
        observed_probs=np.asarray(observed),
        bin_counts=np.asarray(counts, dtype=int),
        expected_calibration_error=ece,
        max_calibration_error=mce,
    )


def patient_landmark_ipcw_weights(
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
    patient_ids: np.ndarray,
) -> np.ndarray:
    """IPCW weights normalized so each determinable patient contributes equal total weight."""
    times = np.asarray(follow_up_times, dtype=float)
    events = np.asarray(event_indicators, dtype=int)
    ids = np.asarray(patient_ids)
    if not (len(times) == len(events) == len(ids)):
        raise ValueError("Follow-up, event, and patient arrays must have equal length")
    weights = compute_ipcw_weights(times, events, horizon_time)
    # Preserve within-patient IPCW ratios while normalizing each patient's total
    # training contribution to one. Dividing only by visit count is insufficient:
    # patients with different censoring weights would still dominate by follow-up.
    for patient_id in np.unique(ids):
        patient_rows = ids == patient_id
        patient_total = float(np.sum(weights[patient_rows]))
        if patient_total > 0:
            weights[patient_rows] /= patient_total
    positive = weights > 0
    if np.any(positive):
        weights[positive] /= float(np.mean(weights[positive]))
    return weights
