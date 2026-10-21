"""
vigil_eval.verification_bias

Partial-verification estimators for explicitly specified observed-label cohorts.

Addresses the clinical reality that expensive radiological imaging (CT/US/Bone Scan)
is selectively ordered when symptoms or tumor markers are elevated.
Implements:
1. Complete-Case Analysis (naïve; biased toward higher sensitivity and lower specificity)
2. Inverse Probability of Verification Weighting (IPW)
3. A legacy pseudo-label routine is retained as a fail-closed compatibility entry point;
   it is not a latent-class EM estimator and does not return estimates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass
class VerificationBiasReport:
    estimator_name: str
    empirical_sensitivity: float
    empirical_specificity: float
    apparent_prevalence: float
    brier_score: float
    roc_auc: float
    details: dict[str, Any]


def _validated_inputs(
    risk_scores: np.ndarray,
    observed_verified_labels: np.ndarray,
    verification_mask: np.ndarray,
    verification_features: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    scores = np.asarray(risk_scores, dtype=float)
    labels = np.asarray(observed_verified_labels, dtype=float)
    raw_mask = np.asarray(verification_mask)
    if scores.ndim != 1 or labels.ndim != 1 or raw_mask.ndim != 1:
        raise ValueError("scores, labels, and verification_mask must be one-dimensional")
    if not (len(scores) == len(labels) == len(raw_mask)):
        raise ValueError("scores, labels, and verification_mask must have equal lengths")
    try:
        numeric_mask = raw_mask.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError("verification_mask must contain only known 0/1 values") from exc
    if not np.all(np.isfinite(numeric_mask)) or np.any(
        (numeric_mask != 0.0) & (numeric_mask != 1.0)
    ):
        raise ValueError("verification_mask must contain only known 0/1 values")
    mask = numeric_mask.astype(bool)
    if not np.all(np.isfinite(scores)) or np.any((scores < 0.0) | (scores > 1.0)):
        raise ValueError("risk_scores must be finite probabilities in [0, 1]")
    verified_labels = labels[mask]
    if not np.all(np.isfinite(verified_labels)) or np.any(
        (verified_labels != 0.0) & (verified_labels != 1.0)
    ):
        raise ValueError("verified outcomes must be known binary labels")

    features = None
    if verification_features is not None:
        features = np.asarray(verification_features, dtype=float)
        if features.ndim != 2 or features.shape[0] != len(mask) or features.shape[1] == 0:
            raise ValueError("verification_features must be a non-empty 2D matrix aligned by row")
        if not np.all(np.isfinite(features)):
            raise ValueError("verification_features must be finite; impute using a declared fit split")
    return scores, labels, mask, features


def _cutoff_value(cutoff: float) -> float:
    value = float(cutoff)
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("cutoff must be a finite probability in [0, 1]")
    return value


def _undefined_report(name: str, details: dict[str, Any]) -> VerificationBiasReport:
    return VerificationBiasReport(
        estimator_name=name,
        empirical_sensitivity=float("nan"),
        empirical_specificity=float("nan"),
        apparent_prevalence=float("nan"),
        brier_score=float("nan"),
        roc_auc=float("nan"),
        details={**details, "metrics_defined": False},
    )


def evaluate_complete_case(
    risk_scores: np.ndarray,
    observed_verified_labels: np.ndarray,
    verification_mask: np.ndarray,
    cutoff: float,
) -> VerificationBiasReport:
    """
    Descriptive estimator: evaluates only verified cases (V = 1). Its selection
    bias depends on the verification process and is not quantified by this routine.
    """
    scores, labels, v_mask, _ = _validated_inputs(
        risk_scores, observed_verified_labels, verification_mask
    )
    cutoff = _cutoff_value(cutoff)
    if not np.any(v_mask):
        return _undefined_report("complete_case", {"n_verified": 0, "reason": "no verified outcomes"})

    scores = scores[v_mask]
    y_true = labels[v_mask].astype(int)

    n = len(y_true)
    y_pred = scores >= cutoff

    tp = np.sum((y_pred == 1) & (y_true == 1))
    fn = np.sum((y_pred == 0) & (y_true == 1))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    tn = np.sum((y_pred == 0) & (y_true == 0))

    sens = float(tp / (tp + fn)) if (tp + fn) > 0 else float("nan")
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else float("nan")
    prev = float(np.mean(y_true))
    brier = float(np.mean((scores - y_true) ** 2))

    # ROC-AUC on complete cases
    from sklearn.metrics import roc_auc_score

    auc = float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) > 1 else float("nan")

    return VerificationBiasReport(
        estimator_name="complete_case",
        empirical_sensitivity=sens,
        empirical_specificity=spec,
        apparent_prevalence=prev,
        brier_score=brier,
        roc_auc=auc,
        details={
            "n_verified": n,
            "metrics_defined": bool(
                np.all(np.isfinite([sens, spec, prev, brier, auc]))
            ),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        },
    )


def evaluate_ipw_verification(
    risk_scores: np.ndarray,
    observed_verified_labels: np.ndarray,
    verification_mask: np.ndarray,
    verification_features: np.ndarray | None,
    cutoff: float,
    verification_propensities: np.ndarray | None = None,
) -> VerificationBiasReport:
    """
    Inverse Probability of Verification Weighting (Begg & Greenes, 1983).
    Models P(Verification = 1 | X) via logistic regression and weights verified
    cases by its inverse, unless caller supplies propensities fitted on a distinct
    development sample. The latter path is useful when the evaluation cohort is
    held out; it never refits on that cohort. Either path identifies population
    metrics only under conditional exchangeability, positivity, and a sufficiently
    specified propensity model. Diagnostics are returned and unsupported cases
    are reported as undefined.
    """
    scores, labels, v_mask, features = _validated_inputs(
        risk_scores, observed_verified_labels, verification_mask, verification_features
    )
    cutoff = _cutoff_value(cutoff)
    n = len(v_mask)
    n_verified = int(np.sum(v_mask))
    if n_verified == 0:
        return _undefined_report("ipw", {"n_total": n, "n_verified": 0, "reason": "no verified outcomes"})

    supplied_propensities = None
    if verification_propensities is not None:
        supplied_propensities = np.asarray(verification_propensities, dtype=float)
        if supplied_propensities.ndim != 1 or len(supplied_propensities) != n:
            raise ValueError("verification_propensities must be one-dimensional and aligned with rows")
        if not np.all(np.isfinite(supplied_propensities)) or np.any(
            (supplied_propensities < 0.0) | (supplied_propensities > 1.0)
        ):
            raise ValueError("verification_propensities must be finite probabilities in [0, 1]")

    # A cohort with no unverified outcomes needs no estimated propensity model.
    if np.all(v_mask):
        prop_scores = np.ones(n, dtype=float)
    elif np.unique(v_mask).size < 2:
        return _undefined_report(
            "ipw", {"n_total": n, "n_verified": n_verified, "reason": "verification has no variation"}
        )
    elif supplied_propensities is not None:
        prop_scores = supplied_propensities
    else:
        if features is None:
            raise ValueError("verification_features are required when verification varies")
        prop_model = LogisticRegression(max_iter=500)
        prop_model.fit(features, v_mask.astype(int))
        prop_scores = prop_model.predict_proba(features)[:, 1]
    fully_verified = bool(np.all(v_mask))
    propensity_support_invalid = np.any(prop_scores <= 0.0) or np.any(
        (~v_mask) & (prop_scores >= 1.0)
    )
    if not np.all(np.isfinite(prop_scores)) or (
        not fully_verified and propensity_support_invalid
    ):
        return _undefined_report(
            "ipw",
            {
                "n_total": n,
                "n_verified": n_verified,
                "reason": "verification propensity violates positivity or conflicts with observed verification",
            },
        )
    ipw = np.zeros(n, dtype=float)
    ipw[v_mask] = 1.0 / prop_scores[v_mask]
    if not np.all(np.isfinite(ipw[v_mask])):
        return _undefined_report(
            "ipw",
            {
                "n_total": n,
                "n_verified": n_verified,
                "reason": "inverse propensity weights are not finite",
            },
        )

    # Only verified observations contribute to loss with IPW weights
    verified_idx = np.where(v_mask)[0]

    y_true_v = labels[verified_idx].astype(int)
    scores_v = scores[verified_idx]
    w_v = ipw[verified_idx]
    y_pred_v = scores_v >= cutoff

    tp_w = np.sum(w_v[(y_pred_v == 1) & (y_true_v == 1)])
    fn_w = np.sum(w_v[(y_pred_v == 0) & (y_true_v == 1)])
    fp_w = np.sum(w_v[(y_pred_v == 1) & (y_true_v == 0)])
    tn_w = np.sum(w_v[(y_pred_v == 0) & (y_true_v == 0)])

    sens = float(tp_w / (tp_w + fn_w)) if (tp_w + fn_w) > 0 else float("nan")
    spec = float(tn_w / (tn_w + fp_w)) if (tn_w + fp_w) > 0 else float("nan")
    prev = float(np.sum(w_v * y_true_v) / np.sum(w_v))
    brier = float(np.sum(w_v * ((scores_v - y_true_v) ** 2)) / np.sum(w_v))

    # Weighted ROC-AUC
    # Mann-Whitney weighted rank sum
    pos_mask = y_true_v == 1
    neg_mask = y_true_v == 0
    if np.any(pos_mask) and np.any(neg_mask):
        concordant = 0.0
        total_pairs = 0.0
        for s_pos, w_pos in zip(scores_v[pos_mask], w_v[pos_mask]):
            gt = scores_v[neg_mask] < s_pos
            eq = scores_v[neg_mask] == s_pos
            pair_w = w_pos * w_v[neg_mask]
            concordant += np.sum(pair_w[gt]) + 0.5 * np.sum(pair_w[eq])
            total_pairs += np.sum(pair_w)
        auc = float(concordant / total_pairs) if total_pairs > 0 else float("nan")
    else:
        auc = float("nan")

    return VerificationBiasReport(
        estimator_name="ipw",
        empirical_sensitivity=sens,
        empirical_specificity=spec,
        apparent_prevalence=prev,
        brier_score=brier,
        roc_auc=auc,
        details={
            "n_total": n,
            "n_verified": int(np.sum(v_mask)),
            "metrics_defined": bool(
                np.all(np.isfinite([sens, spec, prev, brier, auc]))
            ),
            "mean_verification_propensity": float(np.mean(prop_scores)),
            "minimum_verified_propensity": float(np.min(prop_scores[v_mask])),
            "maximum_verified_inverse_weight": float(np.max(w_v)),
            "effective_sample_size": float(np.sum(w_v) ** 2 / np.sum(w_v**2)),
            "identification_assumption": "Outcome is conditionally independent of verification given verification_features; positivity holds for the target population.",
            "weighted_tp": float(tp_w),
            "weighted_fp": float(fp_w),
        },
    )


def evaluate_latent_class_em(
    risk_scores: np.ndarray,
    observed_verified_labels: np.ndarray,
    verification_mask: np.ndarray,
    auxiliary_features: np.ndarray,
    max_iter: int = 50,
    tol: float = 1e-4,
    cutoff: float = 0.5,
) -> VerificationBiasReport:
    """
    Retired compatibility entry point. The former routine initialized unknown
    outcomes from a fixed prevalence and iterated pseudo-label predictions; it
    did not fit an identifiable latent-class likelihood. Without a registered
    missingness model or validation data, reporting its outputs would imply
    unsupported estimates.
    """
    raise NotImplementedError(
        "The former pseudo-label procedure was not latent-class EM; register and validate an identifiable model before estimating unverified outcomes."
    )
