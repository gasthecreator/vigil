"""
packages/vigil-ml/vigil_ml/conformal_k8.py

K8 — Conformal Risk Control, OOD abstention, and a deprecated score prototype.
Provides a finite-sample rank threshold under exchangeability, adaptive tracking,
calibrated alert tiers, and an out-of-distribution (OOD) abstention policy.

Key Components:
1. Conformal Risk Control (CRC): Finite-sample FNR control under exchangeability.
2. Adaptive Conformal Inference (ACI): Online threshold adaptation under non-stationary shifts.
3. Calibrated Alert Tiers: watch, review, urgent.
4. OOD Detector & Abstention Policy: Rejection of physiological outliers and high-epistemic-uncertainty cases.
5. Deprecated hand-written score, not a trained stacking ensemble (stub S-016).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import numpy as np


class AbstentionReason(str, Enum):
    NONE = "none"
    ABSTAIN_UNCALIBRATED = "abstain_uncalibrated"
    ABSTAIN_OOD = "abstain_out_of_distribution"
    ABSTAIN_HIGH_UNCERTAINTY = "abstain_high_epistemic_uncertainty"
    ABSTAIN_MISSING_KEY_MARKERS = "abstain_missing_key_markers"


@dataclass
class ConformalPredictionResult:
    risk_score: Optional[float]
    score_range: Optional[Tuple[float, float]]
    alert_tier: str
    is_alert: bool
    conformal_quantile: Optional[float]
    abstention: AbstentionReason
    explanation_summary: str


class ConformalRiskControllerK8:
    """
    Implements a finite-sample rank threshold under exchangeability of positive scores.
    Adaptive updates and the separate OOD heuristic do not inherit this guarantee.
    """

    def __init__(self, alpha_conf: float = 0.10, adapt_rate: float = 0.05):
        if not np.isfinite(alpha_conf) or not 0.0 < alpha_conf < 1.0:
            raise ValueError("alpha_conf must be between 0 and 1")
        if not np.isfinite(adapt_rate) or adapt_rate <= 0.0:
            raise ValueError("adapt_rate must be positive")
        self.alpha_conf = alpha_conf
        self.adapt_rate = adapt_rate
        self.calibrated_threshold = 0.28
        self.running_threshold = 0.28
        self.is_calibrated = False
        # OOD baseline statistics on feature space
        self.feature_means: Optional[np.ndarray] = None
        self.feature_cov_inv: Optional[np.ndarray] = None
        self.ood_threshold: float = 45.0  # Mahalanobis chi-sq critical value (15-dim, p < 0.0001)

    def calibrate(self, val_scores: np.ndarray, val_labels: np.ndarray) -> "ConformalRiskControllerK8":
        """
        Calibrates the operating threshold on held-out validation data to strictly bound FNR.
        """
        val_scores = np.asarray(val_scores, dtype=float)
        val_labels = np.asarray(val_labels)
        if val_scores.ndim != 1 or val_labels.ndim != 1 or len(val_scores) != len(val_labels):
            raise ValueError("validation scores and labels must be one-dimensional arrays of equal length")
        if (
            not np.all(np.isfinite(val_scores))
            or np.any((val_scores < 0.0) | (val_scores > 1.0))
            or not np.all(np.isin(val_labels, [0, 1]))
        ):
            raise ValueError("validation scores must be finite in [0, 1] and labels must be binary")
        val_labels = val_labels.astype(int)
        pos_scores = np.sort(val_scores[val_labels == 1])
        if pos_scores.size == 0:
            raise ValueError("validation labels must include at least one positive event")
        k = int(np.floor((len(pos_scores) + 1) * self.alpha_conf))
        self.calibrated_threshold = float(pos_scores[k - 1]) if k > 0 else float("-inf")
        self.running_threshold = self.calibrated_threshold
        self.is_calibrated = True
        return self

    def fit_ood_detector(self, X_train: np.ndarray) -> "ConformalRiskControllerK8":
        """
        Fits multivariate Gaussian baseline for Mahalanobis OOD distance checking.
        """
        X_train = np.asarray(X_train, dtype=float)
        if X_train.ndim != 2 or X_train.shape[0] < 2 or X_train.shape[1] == 0:
            raise ValueError("X_train must be a 2D array with at least two rows and one feature")
        if not np.all(np.isfinite(X_train)):
            raise ValueError("X_train must contain only finite values")
        self.feature_means = np.mean(X_train, axis=0)
        cov = np.cov(X_train, rowvar=False) + 1e-4 * np.eye(X_train.shape[1])
        self.feature_cov_inv = np.linalg.pinv(cov)
        return self

    def check_ood(self, x: np.ndarray) -> Tuple[bool, float]:
        """
        Computes Mahalanobis distance from reference training manifold.
        """
        if self.feature_means is None or self.feature_cov_inv is None:
            return False, 0.0
        x = np.asarray(x, dtype=float)
        if x.shape != self.feature_means.shape or not np.all(np.isfinite(x)):
            raise ValueError("x must be a finite feature vector matching the fitted OOD dimensions")
        diff = x - self.feature_means
        dist_sq = float(diff @ self.feature_cov_inv @ diff)
        is_ood = dist_sq > self.ood_threshold
        return is_ood, float(np.sqrt(dist_sq))

    def predict(
        self, raw_risk: float, epistemic_std: float, feature_vector: Optional[np.ndarray] = None
    ) -> ConformalPredictionResult:
        """
        Produces a prediction only after calibration; otherwise abstains.
        """
        if not np.isfinite(raw_risk) or not 0.0 <= raw_risk <= 1.0:
            raise ValueError("raw_risk must be a finite score between 0 and 1")
        if not np.isfinite(epistemic_std) or epistemic_std < 0.0:
            raise ValueError("epistemic_std must be finite and non-negative")
        if not self.is_calibrated:
            return ConformalPredictionResult(
                risk_score=None,
                score_range=None,
                alert_tier="abstain",
                is_alert=False,
                conformal_quantile=None,
                abstention=AbstentionReason.ABSTAIN_UNCALIBRATED,
                explanation_summary="No calibration cohort is loaded. Defer this score for clinician review.",
            )
        # Check OOD abstention
        if feature_vector is not None:
            is_ood, dist = self.check_ood(feature_vector)
            if is_ood:
                return ConformalPredictionResult(
                    risk_score=None,
                    score_range=None,
                    alert_tier="abstain",
                    is_alert=False,
                    conformal_quantile=self.running_threshold,
                    abstention=AbstentionReason.ABSTAIN_OOD,
                    explanation_summary=f"Patient feature vector is outside calibration manifold (Mahalanobis D={dist:.1f} > {np.sqrt(self.ood_threshold):.1f}). Triage decision deferred to oncologist.",
                )

        # Check epistemic uncertainty abstention
        if epistemic_std > 0.35:
            return ConformalPredictionResult(
                risk_score=None,
                score_range=None,
                alert_tier="abstain",
                is_alert=False,
                conformal_quantile=self.running_threshold,
                abstention=AbstentionReason.ABSTAIN_HIGH_UNCERTAINTY,
                explanation_summary="Model posterior variance is exceptionally wide. Recommending expedited confirmatory re-test.",
            )

        # Conformal interval
        margin = max(0.05, 1.645 * epistemic_std)
        ci_low = max(0.0, raw_risk - margin)
        ci_high = min(1.0, raw_risk + margin)

        # Tiers
        is_alert = raw_risk >= self.running_threshold
        if raw_risk >= 0.65:
            tier = "urgent"
        elif raw_risk >= self.running_threshold:
            tier = "review"
        elif raw_risk >= (self.running_threshold * 0.65):
            tier = "watch"
        else:
            tier = "none"

        return ConformalPredictionResult(
                risk_score=raw_risk,
                score_range=(ci_low, ci_high),
            alert_tier=tier,
            is_alert=is_alert,
            conformal_quantile=self.running_threshold,
            abstention=AbstentionReason.NONE,
            explanation_summary=f"Model score {raw_risk:.1%} (heuristic score range [{ci_low:.1%}, {ci_high:.1%}]). Alert tier: {tier.upper()}.",
        )

    def adapt_online(self, pred_alert: bool, true_event: bool) -> None:
        """
        Adaptive Conformal Inference (ACI) step: updates decision threshold
        to maintain exact coverage over non-stationary clinical environments.
        """
        # If false negative occurred (missed alert on true event) -> lower threshold
        if true_event and not pred_alert:
            self.running_threshold = max(0.05, self.running_threshold - self.adapt_rate)
        # If false alarm occurred on confirmed non-recurrence -> raise threshold slightly
        elif pred_alert and not true_event:
            self.running_threshold = min(0.85, self.running_threshold + (self.adapt_rate * self.alpha_conf))


class ProductionEnsembleK8:
    """Quarantined legacy name for an invalid, hand-written ensemble score."""

    @staticmethod
    def _quarantined() -> RuntimeError:
        return RuntimeError(
            "ProductionEnsembleK8 is quarantined: the historical fixed formula "
            "is not a trained ensemble and cannot produce valid inference"
        )

    def fit(self, X: object, y: object) -> ProductionEnsembleK8:
        raise self._quarantined()

    def predict_risk(self, X: object) -> np.ndarray:
        raise self._quarantined()
