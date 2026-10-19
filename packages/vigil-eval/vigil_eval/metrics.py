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

        # Floor probabilities at small positive epsilon to prevent division by zero in IPCW
        return cast(NDArray[np.floating], np.clip(probs, 1e-4, 1.0))


def compute_kaplan_meier(
    times: np.ndarray,
    events: np.ndarray,
) -> KaplanMeierEstimate:
    """
    Computes standard non-parametric Kaplan-Meier estimate.

    Parameters:
        times: Observed follow-up times (T_i).
        events: Event indicators (1 if event occurred, 0 if censored).
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
    - If T_i <= horizon and Delta_i == 1 (recurrence prior to horizon): w_i = 1 / G(T_i)
    - If T_i > horizon (survived disease-free past horizon): w_i = 1 / G(horizon)
    - If T_i <= horizon and Delta_i == 0 (censored prior to horizon): w_i = 0 (uninformative)
    """
    n = len(follow_up_times)
    weights = np.zeros(n, dtype=float)

    # Estimate censoring distribution G(t) by reversing event indicator
    censoring_indicators = 1 - event_indicators
    g_km = compute_kaplan_meier(follow_up_times, censoring_indicators)

    # Evaluate G(horizon)
    g_at_horizon = float(g_km.predict_survival(horizon_time)[0])

    for i in range(n):
        t_i = follow_up_times[i]
        d_i = event_indicators[i]

        if t_i <= horizon_time:
            if d_i == 1:
                # Recurrence occurred before horizon
                g_ti = float(g_km.predict_survival(t_i)[0])
                weights[i] = 1.0 / g_ti
            else:
                # Censored before horizon: indeterminate status
                weights[i] = 0.0
        else:
            # Survived past horizon
            weights[i] = 1.0 / g_at_horizon

    return weights


def ipcw_time_dependent_roc_auc(
    risk_scores: np.ndarray,
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
) -> float:
    """
    Computes Uno et al. (2007) Inverse Probability of Censoring Weighted time-dependent ROC-AUC.

    Evaluates cumulative cases (T_i <= t, Delta_i = 1) versus dynamic controls (T_j > t).
    """
    weights = compute_ipcw_weights(follow_up_times, event_indicators, horizon_time)

    # Identify case and control indices
    cases_mask = (follow_up_times <= horizon_time) & (event_indicators == 1) & (weights > 0)
    controls_mask = (follow_up_times > horizon_time) & (weights > 0)

    if not np.any(cases_mask) or not np.any(controls_mask):
        return 0.5  # Undefined/degenerate without both cases and controls

    case_scores = risk_scores[cases_mask]
    case_weights = weights[cases_mask]

    control_scores = risk_scores[controls_mask]
    control_weights = weights[controls_mask]

    # Weighted Mann-Whitney concordant pair evaluation
    concordant = 0.0
    total_weight = 0.0

    for c_score, c_wt in zip(case_scores, case_weights):
        # Pairs where case score exceeds control score
        gt = control_scores < c_score
        eq = control_scores == c_score

        pair_weights = c_wt * control_weights
        concordant += np.sum(pair_weights[gt]) + 0.5 * np.sum(pair_weights[eq])
        total_weight += np.sum(pair_weights)

    return float(concordant / total_weight) if total_weight > 0 else 0.5


def ipcw_brier_score(
    predicted_probabilities: np.ndarray,
    follow_up_times: np.ndarray,
    event_indicators: np.ndarray,
    horizon_time: float,
) -> float:
    """
    Computes IPCW-weighted Brier score for survival horizon t (Graf et al. 1999).

    BS(t) = 1/N * sum_i [ (0 - S_i(t))^2 * I(T_i <= t, Delta_i=1) / G(T_i)
                        + (1 - S_i(t))^2 * I(T_i > t) / G(t) ]
    """
    n = len(follow_up_times)
    if n == 0:
        return 0.0

    # Risk of event occurring by horizon: p_i = 1 - S_i(horizon)
    p_hat = np.clip(predicted_probabilities, 0.0, 1.0)
    weights = compute_ipcw_weights(follow_up_times, event_indicators, horizon_time)

    # For patients experiencing event before horizon, true status Y_i = 1
    # For patients surviving past horizon, true status Y_i = 0
    loss = 0.0
    valid_count = 0

    for i in range(n):
        w = weights[i]
        if w <= 0.0:
            continue

        if follow_up_times[i] <= horizon_time and event_indicators[i] == 1:
            y = 1.0
        else:
            y = 0.0

        loss += w * ((p_hat[i] - y) ** 2)
        valid_count += 1

    return float(loss / n) if n > 0 else 0.0


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
    if thresholds is None:
        thresholds = np.linspace(0.01, 0.50, 50)

    n = len(predicted_risks)
    weights = compute_ipcw_weights(follow_up_times, event_indicators, horizon_time)

    is_case = (follow_up_times <= horizon_time) & (event_indicators == 1)
    is_control = follow_up_times > horizon_time

    nb_model = []
    nb_all = []
    nb_none = np.zeros(len(thresholds), dtype=float)

    # Baseline prevalence at horizon via IPCW
    weighted_cases = np.sum(weights[is_case])
    total_w = np.sum(weights[is_case | is_control])
    weighted_cases / total_w if total_w > 0 else 0.05

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
    p = np.clip(predicted_probs, 0.0, 1.0)
    y = np.asarray(observed_labels, dtype=float)
    n = len(p)

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
