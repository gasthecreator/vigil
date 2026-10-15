"""
vigil_eval.verification_bias

Partial Verification Bias Correction Framework (Study S3, ML_PROGRAM §6).
Conforms strictly to docs/MASTER_PLAN.md §4.2, §14 (WP2.1), and docs/ML_PROGRAM.md §6, §9.

Addresses the clinical reality that expensive radiological imaging (CT/US/Bone Scan)
is selectively ordered when symptoms or tumor markers are elevated.
Implements:
1. Complete-Case Analysis (naïve; biased toward higher sensitivity and lower specificity)
2. Inverse Probability of Verification Weighting (IPW)
3. Latent-Class Expectation-Maximization (EM) Estimator
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

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
    details: Dict[str, Any]


def evaluate_complete_case(
    risk_scores: np.ndarray,
    observed_verified_labels: np.ndarray,
    verification_mask: np.ndarray,
    cutoff: float = 0.5,
) -> VerificationBiasReport:
    """
    Complete-case estimator: Evaluates metrics only on verified/imaged cases (V = 1).
    Demonstrates severe verification bias in selective clinical screening.
    """
    v_mask = np.asarray(verification_mask, dtype=bool)
    if not np.any(v_mask):
        return VerificationBiasReport("complete_case", 0.0, 0.0, 0.0, 0.0, 0.5, {"n_verified": 0})

    scores = risk_scores[v_mask]
    y_true = observed_verified_labels[v_mask]

    n = len(y_true)
    y_pred = scores >= cutoff

    tp = np.sum((y_pred == 1) & (y_true == 1))
    fn = np.sum((y_pred == 0) & (y_true == 1))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    tn = np.sum((y_pred == 0) & (y_true == 0))

    sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 1.0
    prev = float(np.mean(y_true))
    brier = float(np.mean((scores - y_true) ** 2))

    # ROC-AUC on complete cases
    from sklearn.metrics import roc_auc_score

    try:
        auc = float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) > 1 else 0.5
    except Exception:
        auc = 0.5

    return VerificationBiasReport(
        estimator_name="complete_case",
        empirical_sensitivity=sens,
        empirical_specificity=spec,
        apparent_prevalence=prev,
        brier_score=brier,
        roc_auc=auc,
        details={
            "n_verified": n,
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
    verification_features: np.ndarray,
    cutoff: float = 0.5,
) -> VerificationBiasReport:
    """
    Inverse Probability of Verification Weighting (Begg & Greenes, 1983).
    Models P(Verification = 1 | X, symptoms, markers) via logistic regression,
    and weights verified cases by 1 / P(V = 1 | X).
    """
    v_mask = np.asarray(verification_mask, dtype=bool)
    n = len(v_mask)

    # 1. Fit verification propensity model
    prop_model = LogisticRegression(max_iter=500, random_state=42)
    prop_model.fit(verification_features, v_mask.astype(int))
    prop_scores = prop_model.predict_proba(verification_features)[:, 1]

    # Clip propensities to prevent infinite weights
    prop_scores = np.clip(prop_scores, 0.05, 0.95)
    ipw = 1.0 / prop_scores

    # Only verified observations contribute to loss with IPW weights
    verified_idx = np.where(v_mask)[0]
    if len(verified_idx) == 0:
        return VerificationBiasReport("ipw", 0.0, 0.0, 0.0, 0.0, 0.5, {})

    y_true_v = observed_verified_labels[verified_idx]
    scores_v = risk_scores[verified_idx]
    w_v = ipw[verified_idx]
    y_pred_v = scores_v >= cutoff

    tp_w = np.sum(w_v[(y_pred_v == 1) & (y_true_v == 1)])
    fn_w = np.sum(w_v[(y_pred_v == 0) & (y_true_v == 1)])
    fp_w = np.sum(w_v[(y_pred_v == 1) & (y_true_v == 0)])
    tn_w = np.sum(w_v[(y_pred_v == 0) & (y_true_v == 0)])

    sens = float(tp_w / (tp_w + fn_w)) if (tp_w + fn_w) > 0 else 0.0
    spec = float(tn_w / (tn_w + fp_w)) if (tn_w + fp_w) > 0 else 1.0
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
        auc = float(concordant / total_pairs) if total_pairs > 0 else 0.5
    else:
        auc = 0.5

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
            "mean_verification_propensity": float(np.mean(prop_scores)),
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
    Latent-Class Expectation-Maximization (EM) Estimator for Unverified Disease Status.
    Treats unverified patient recurrence as an unobserved latent variable,
    iteratively updating posterior disease probabilities given auxiliary features.
    """
    v_mask = np.asarray(verification_mask, dtype=bool)
    n = len(v_mask)

    # Initialize posterior disease probability q_i
    # For verified: q_i = observed_verified_labels[i]
    # For unverified: q_i = prior prevalence (~0.15)
    q = np.zeros(n, dtype=float)
    q[v_mask] = observed_verified_labels[v_mask]
    q[~v_mask] = 0.15

    model = LogisticRegression(max_iter=200, random_state=42)

    for iteration in range(max_iter):
        q_prev = q.copy()

        # M-step: Train predictive model on soft targets q
        # Sample weights = 1.0; using thresholded pseudo-labels or weighted duplicate rows
        # Weighted logistic regression with binary soft weights:
        X_dup = np.vstack([auxiliary_features, auxiliary_features])
        y_dup = np.hstack([np.ones(n), np.zeros(n)])
        w_dup = np.hstack([q, 1.0 - q])

        valid_w = w_dup > 1e-4
        if np.sum(valid_w) < 10:
            break

        model.fit(X_dup[valid_w], y_dup[valid_w], sample_weight=w_dup[valid_w])

        # E-step: Update posterior for unverified cases
        pred_disease = model.predict_proba(auxiliary_features)[:, 1]
        q[~v_mask] = pred_disease[~v_mask]

        if np.max(np.abs(q - q_prev)) < tol:
            break

    # Evaluate metrics across full cohort using imputed posterior disease status q
    y_pred = risk_scores >= cutoff
    tp = np.sum(y_pred * q)
    fn = np.sum((1.0 - y_pred) * q)
    fp = np.sum(y_pred * (1.0 - q))
    tn = np.sum((1.0 - y_pred) * (1.0 - q))

    sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 1.0
    prev = float(np.mean(q))
    brier = float(np.mean((risk_scores - q) ** 2))

    # Soft AUC
    order = np.argsort(risk_scores)
    sorted_q = q[order]
    n_pos = np.sum(q)
    n_neg = n - n_pos

    if n_pos > 0 and n_neg > 0:
        cum_neg = np.cumsum(1.0 - sorted_q)
        auc = float(np.sum(sorted_q * cum_neg) / (n_pos * n_neg))
    else:
        auc = 0.5

    return VerificationBiasReport(
        estimator_name="latent_class_em",
        empirical_sensitivity=sens,
        empirical_specificity=spec,
        apparent_prevalence=prev,
        brier_score=brier,
        roc_auc=auc,
        details={
            "em_iterations": iteration + 1,
            "latent_imputed_positives": float(np.sum(q[~v_mask])),
            "verified_positives": int(np.sum(observed_verified_labels[v_mask])),
        },
    )
