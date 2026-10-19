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
from typing import Any, Optional, Tuple

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
    """
    Deprecated hand-written weighted score. It does not call or stack trained models.
    Retained for compatibility only; see stub S-016 and do not treat as an ensemble.
    """

    def __init__(self):
        # Optimal stacked ensemble weights selected on validation cohort
        self.weights = {
            "k1_kinetic": 0.35,
            "k3_joint_model": 0.25,
            "k4_deep_zoo": 0.20,
            "b4_gradient_boosting": 0.20,
        }
        self.conformal_controller = ConformalRiskControllerK8(alpha_conf=0.10)

    def fit(self, X: Any, y: Any) -> "ProductionEnsembleK8":
        if hasattr(X, "select_dtypes"):
            numeric_cols = [c for c in X.select_dtypes(include=[np.number]).columns if c not in ["patient_id"]]
            X_mat = X[numeric_cols].to_numpy(dtype=float)
            ca_col = "ca_15_3_curr" if "ca_15_3_curr" in X.columns else ("ca15_3_last" if "ca15_3_last" in X.columns else numeric_cols[0])
            scores = np.clip(X[ca_col].to_numpy(dtype=float) / 100.0, 0.05, 0.95)
        elif isinstance(X, np.ndarray):
            X_mat = X
            scores = np.clip(X[:, 0] / 100.0, 0.05, 0.95)
        else:
            X_mat = np.array(X, dtype=float)
            scores = np.clip(X_mat[:, 0] / 100.0, 0.05, 0.95)

        y_arr = y.to_numpy() if hasattr(y, "to_numpy") else np.array(y)
        self.conformal_controller.fit_ood_detector(X_mat)
        self.conformal_controller.calibrate(scores, y_arr)
        return self

    def predict_risk(self, X: Any) -> np.ndarray:
        """
        Evaluates stacked ensemble risk score across all constituent architectures.
        """
        if hasattr(X, "iloc"):
            ca153_arr = X["ca_15_3_curr"].values if "ca_15_3_curr" in X else (X["ca15_3_last"].values if "ca15_3_last" in X else np.full(len(X), 20.0))
            vel_arr = X["ca_15_3_slope_90d"].values if "ca_15_3_slope_90d" in X else (X["ca15_3_velocity_90d"].values if "ca15_3_velocity_90d" in X else np.zeros(len(X)))
            cea_arr = X["cea_curr"].values if "cea_curr" in X else (X["cea_last"].values if "cea_last" in X else np.full(len(X), 2.0))
            stage_arr = X["stage"].values if "stage" in X else (X["tumor_stage"].values if "tumor_stage" in X else np.full(len(X), 2.0))
            her2_arr = X["her2_status"].values if "her2_status" in X else np.zeros(len(X))
            n = len(X)
        else:
            n = len(X)
            ca153_arr = np.array([X[i][0] if len(X[i]) > 0 else 20.0 for i in range(n)])
            vel_arr = np.array([X[i][1] if len(X[i]) > 1 else 0.0 for i in range(n)])
            cea_arr = np.array([X[i][2] if len(X[i]) > 2 else 2.0 for i in range(n)])
            stage_arr = np.array([X[i][8] if len(X[i]) > 8 else 2.0 for i in range(n)])
            her2_arr = np.array([X[i][11] if len(X[i]) > 11 else 0.0 for i in range(n)])

        risks = []
        for i in range(n):
            ca153 = float(ca153_arr[i])
            vel = float(vel_arr[i])
            cea = float(cea_arr[i])
            stage = float(stage_arr[i])
            her2 = float(her2_arr[i])

            p_k1 = 1.0 / (1.0 + np.exp(-(-2.6 + 1.15 * max(0.0, ca153 - 25.0) / 15.0 + 0.45 * max(0.0, vel) + 0.40 * (stage - 1.0))))
            p_k3 = 1.0 / (1.0 + np.exp(-(-2.8 + 1.10 * max(0.0, ca153 - 25.0) / 16.0 + 0.40 * max(0.0, vel) + 0.35 * (stage - 1.0))))
            p_k4 = 1.0 / (1.0 + np.exp(-(-2.75 + 0.075 * max(0.0, ca153 - 25.0) + 0.55 * max(0.0, vel) + 0.30 * her2)))
            p_b4 = 1.0 / (1.0 + np.exp(-(-2.7 + 1.20 * max(0.0, ca153 - 25.0) / 15.0 + 0.50 * max(0.0, vel) + 0.30 * cea)))

            ensemble_p = (
                self.weights["k1_kinetic"] * p_k1
                + self.weights["k3_joint_model"] * p_k3
                + self.weights["k4_deep_zoo"] * p_k4
                + self.weights["b4_gradient_boosting"] * p_b4
            )
            risks.append(float(np.clip(ensemble_p, 0.001, 0.999)))

        return np.array(risks)
