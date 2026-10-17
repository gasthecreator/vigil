"""Module M3: Plausibility Adjudicator.

Distinguishes genuine tumor marker progression, pre-analytical/analytical gross errors,
and analytical/within-subject biological baseline fluctuations using Reference Change
Values (RCV) and a calibrated Bayesian 3-way generative mixture model.

Safety Policy: Outlier results are NEVER dismissed ("dismissed" is not an allowed action).
Results are classified as:
  - "escalate": high probability of true disease progression (p_real >= 0.60, p_err < 0.30)
  - "explained": high probability of baseline fluctuation (p_stable >= 0.90, p_err < 0.30)
  - "needs_repeat": potential analytical/pre-analytical error (p_error >= 0.30) or
    indeterminate variation requiring confirmation before clinical intervention.

Reference Change Values conform to Evidence E9 (Aarsand et al. 2021, Ricós et al. 1999).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple, Union


def rcv(
    cv_analytical: float,
    cv_within: float,
    z: float = 1.96,
    log_normal: bool = False,
) -> Union[float, Tuple[float, float]]:
    """Calculate Reference Change Value (RCV).

    Args:
        cv_analytical: Analytical coefficient of variation (s_A / mean).
        cv_within: Within-subject biological coefficient of variation (s_I / mean).
        z: Z-score multiplier for significance level (default 1.96 for 95% two-sided).
        log_normal: If True, computes asymmetrical log-normal RCV (up, down).
                    If False, computes classical symmetrical Gaussian RCV.

    Returns:
        float if log_normal=False: sqrt(2) * z * sqrt(cva^2 + cvi^2)
        tuple (up, down) if log_normal=True:
            up = exp(z * sqrt(2) * s) - 1
            down = exp(-z * sqrt(2) * s) - 1
            where s = sqrt(ln(1 + cva^2) + ln(1 + cvi^2))
    """
    if not log_normal:
        return math.sqrt(2.0) * z * math.sqrt(cv_analytical**2 + cv_within**2)

    s = math.sqrt(math.log(1.0 + cv_analytical**2) + math.log(1.0 + cv_within**2))
    up = math.exp(z * math.sqrt(2.0) * s) - 1.0
    down = math.exp(-z * math.sqrt(2.0) * s) - 1.0
    return up, down


def _norm_pdf(x: float, mean: float, std: float) -> float:
    """Evaluate univariate Gaussian probability density function."""
    if std <= 0.0:
        return 1.0 if abs(x - mean) < 1e-9 else 0.0
    diff = x - mean
    return math.exp(-0.5 * (diff / std) ** 2) / (math.sqrt(2.0 * math.pi) * std)


def _norm_cdf(z: float) -> float:
    """Evaluate standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def adjudicate(
    history: List[Tuple[float, float]],
    new_day: float,
    new_value: float,
    cv_analytical: float,
    cv_within: float,
    lab_changed: bool = False,
    inter_lab_cv: float = 0.10,
    p_error_prior: float = 0.03,
    p_real_prior: float = 0.20,
) -> Dict[str, Any]:
    """Adjudicate marker plausibility via 3-way Bayesian generative mixture model.

    Evaluates whether the newly observed marker measurement represents:
      1. Real progression: persistent elevation f ~ logUniform(1.4, 3.0)
      2. Gross error: specimen mixup (population draw) or decimal transcription error (x10, /10)
      3. Stable: physiological baseline fluctuation around personalized geometric mean.

    Args:
        history: List of prior (day, value) observations.
        new_day: Day of current measurement.
        new_value: Observed analyte concentration.
        cv_analytical: Analytical coefficient of variation (CVa).
        cv_within: Within-subject biological coefficient of variation (CVi).
        lab_changed: Whether specimen was analyzed at a different facility/analyzer.
        inter_lab_cv: Multiplicative inter-laboratory coefficient of variation.
        p_error_prior: Prior probability of gross error (default 0.03).
        p_real_prior: Prior probability of real progression (default 0.20).

    Returns:
        dict containing:
            "p_real": Posterior probability of true disease progression.
            "p_error": Posterior probability of analytical/pre-analytical gross error.
            "p_stable": Posterior probability of stable baseline fluctuation.
            "action": Clinical decision ("explained" | "needs_repeat" | "escalate").
            "rationale_facts": Provenance-traceable structured facts for downstream narrative.
    """
    if new_value <= 0.0:
        raise ValueError(f"Observed value must be positive, got {new_value}")

    # Compute personalized baseline from historical draws (geometric mean)
    log_history = [math.log(val) for _, val in history if val > 0.0]
    n_hist = len(log_history)
    if n_hist > 0:
        log_base = sum(log_history) / n_hist
    else:
        log_base = math.log(new_value)
        n_hist = 1

    base = math.exp(log_base)
    log_y = math.log(new_value)
    log_ratio = log_y - log_base
    obs_change = new_value / base

    # Variance components in log space:
    # Measurement noise + baseline estimation uncertainty + optional lab switch variance
    sig_meas_sq = cv_analytical**2 + cv_within**2
    sig_sq = sig_meas_sq * (1.0 + 1.0 / n_hist)
    if lab_changed:
        sig_sq += inter_lab_cv**2
    sig = math.sqrt(sig_sq)

    # 1. Likelihood given stable: log(y / L) ~ N(0, sig^2)
    lik_stable = _norm_pdf(log_ratio, 0.0, sig)

    # 2. Likelihood given real change: log(y / L) ~ Uniform(ln 1.4, ln 3.0) convolved with N(0, sig^2)
    a, b = math.log(1.4), math.log(3.0)
    phi_a = _norm_cdf((log_ratio - a) / sig)
    phi_b = _norm_cdf((log_ratio - b) / sig)
    lik_real = max((phi_a - phi_b) / (b - a), 1e-300)

    # 3. Likelihood given gross error (mixture of 3 equally likely error mechanisms):
    # Mode 0: Population draw / sample mixup: log(y) ~ N(ln 18.0, 0.6^2 + (inter_lab_cv^2 if lab_changed else 0))
    sig_pop_sq = 0.6**2 + (inter_lab_cv**2 if lab_changed else 0.0)
    sig_pop = math.sqrt(sig_pop_sq)
    lik_err_pop = _norm_pdf(log_y, math.log(18.0), sig_pop)

    # Mode 1: Decimal shift up (x10): log(y / L) ~ N(ln 10, sig^2)
    lik_err_x10 = _norm_pdf(log_ratio, math.log(10.0), sig)

    # Mode 2: Decimal shift down (/10): log(y / L) ~ N(-ln 10, sig^2)
    lik_err_div10 = _norm_pdf(log_ratio, -math.log(10.0), sig)

    lik_error = (lik_err_pop + lik_err_x10 + lik_err_div10) / 3.0

    # Prior probabilities
    p_stable_prior = max(1.0 - p_real_prior - p_error_prior, 0.0)

    # Posterior probabilities via Bayes' rule
    w_real = p_real_prior * lik_real
    w_error = p_error_prior * lik_error
    w_stable = p_stable_prior * lik_stable
    w_total = w_real + w_error + w_stable

    if w_total > 0.0:
        p_real = w_real / w_total
        p_error = w_error / w_total
        p_stable = w_stable / w_total
    else:
        p_real = p_real_prior
        p_error = p_error_prior
        p_stable = p_stable_prior

    # Ensure probabilities are bounded in [0.0, 1.0] and sum to 1.0
    p_real = max(0.0, min(1.0, p_real))
    p_error = max(0.0, min(1.0, p_error))
    p_stable = max(0.0, min(1.0, p_stable))
    p_sum = p_real + p_error + p_stable
    if p_sum > 0.0:
        p_real /= p_sum
        p_error /= p_sum
        p_stable /= p_sum
    else:
        p_real, p_error, p_stable = p_real_prior, p_error_prior, p_stable_prior

    # Safety Policy: Outliers are NEVER dismissed.
    # Needs repeat if error probability is high or result is ambiguous;
    # Escalate if real progression probability is high;
    # Explained only if high baseline stability confidence.
    if p_error >= 0.30:
        action = "needs_repeat"
    elif p_real >= 0.60:
        action = "escalate"
    elif p_stable >= 0.90:
        action = "explained"
    else:
        action = "needs_repeat"

    rcv_metric = float(rcv(cv_analytical, cv_within, z=1.96, log_normal=False))

    rationale_facts = [
        {
            "fact_id": "f_rcv",
            "type": "rcv",
            "value": rcv_metric,
        },
        {
            "fact_id": "f_observed_change",
            "type": "observed_change",
            "value": float(obs_change),
        },
        {
            "fact_id": "f_p_real",
            "type": "p_real",
            "value": float(p_real),
        },
        {
            "fact_id": "f_p_error",
            "type": "p_error",
            "value": float(p_error),
        },
        {
            "fact_id": "f_p_stable",
            "type": "p_stable",
            "value": float(p_stable),
        },
        {
            "fact_id": "f_action",
            "type": "action",
            "value": action,
        },
    ]

    return {
        "p_real": float(p_real),
        "p_error": float(p_error),
        "p_stable": float(p_stable),
        "action": action,
        "rationale_facts": rationale_facts,
    }
