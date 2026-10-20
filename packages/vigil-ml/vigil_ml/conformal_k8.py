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

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from scipy.stats import chi2  # type: ignore[import-untyped]


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
    config_id: str
    config_sha256: str


class ConformalRiskControllerK8:
    """
    Implements a finite-sample rank threshold under exchangeability of positive scores.
    Adaptive updates and the separate OOD heuristic do not inherit this guarantee.
    """

    CONFIG_PATH = Path(__file__).parent / "models" / "k8_research_config_v1.json"

    def __init__(
        self,
        alpha_conf: Optional[float] = None,
        adapt_rate: Optional[float] = None,
        *,
        config_path: Optional[Path] = None,
    ):
        try:
            config = json.loads((config_path or self.CONFIG_PATH).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("K8 research configuration must be readable UTF-8 JSON") from exc
        required = {
            "schema_version",
            "config_id",
            "status",
            "provenance",
            "alpha_conf",
            "adapt_rate",
            "contract_ood_alpha",
            "contract_covariance_regularizer",
            "contract_aci_gamma",
            "ood_tail_probability",
            "covariance_regularizer",
            "epistemic_abstention_cutoff",
            "interval_normal_quantile",
            "interval_minimum_half_width",
            "urgent_score_threshold",
            "watch_threshold_fraction",
            "adaptation_threshold_floor",
            "adaptation_threshold_ceiling",
        }
        if not isinstance(config, dict) or set(config) != required:
            raise ValueError("K8 research configuration keys do not match the versioned schema")
        if config["schema_version"] != "1" or config["status"] != "unvalidated_research_defaults":
            raise ValueError(
                "K8 research configuration must identify its schema and unvalidated status"
            )
        numeric_keys = required - {"schema_version", "config_id", "status", "provenance"}
        if any(
            isinstance(config[key], bool) or not isinstance(config[key], (int, float))
            for key in numeric_keys
        ):
            raise ValueError("K8 research configuration numeric fields must be numbers")
        if any(not np.isfinite(config[key]) for key in numeric_keys):
            raise ValueError("K8 research configuration numeric fields must be finite")
        if not isinstance(config["config_id"], str) or not config["config_id"]:
            raise ValueError("K8 research configuration must have a non-empty config_id")
        if not isinstance(config["provenance"], str) or not config["provenance"]:
            raise ValueError("K8 research configuration must document its provenance")
        alpha_conf = config["alpha_conf"] if alpha_conf is None else alpha_conf
        adapt_rate = config["adapt_rate"] if adapt_rate is None else adapt_rate
        if isinstance(alpha_conf, (bool, np.bool_)) or not isinstance(
            alpha_conf, (int, float, np.number)
        ):
            raise ValueError("alpha_conf must be a numeric scalar")
        if isinstance(adapt_rate, (bool, np.bool_)) or not isinstance(
            adapt_rate, (int, float, np.number)
        ):
            raise ValueError("adapt_rate must be a numeric scalar")
        if not np.isfinite(alpha_conf) or not 0.0 < alpha_conf < 1.0:
            raise ValueError("alpha_conf must be between 0 and 1")
        if not np.isfinite(adapt_rate) or adapt_rate <= 0.0:
            raise ValueError("adapt_rate must be positive")
        if not 0.0 < config["ood_tail_probability"] < 1.0:
            raise ValueError("ood_tail_probability must be between 0 and 1")
        if config["covariance_regularizer"] <= 0.0:
            raise ValueError("covariance_regularizer must be positive")
        if not 0.0 < config["contract_ood_alpha"] < 1.0:
            raise ValueError("contract_ood_alpha must be between 0 and 1")
        if config["contract_covariance_regularizer"] <= 0.0:
            raise ValueError("contract_covariance_regularizer must be positive")
        if config["contract_aci_gamma"] <= 0.0:
            raise ValueError("contract_aci_gamma must be positive")
        bounded = {
            "epistemic_abstention_cutoff": (0.0, None),
            "interval_normal_quantile": (0.0, None),
            "interval_minimum_half_width": (0.0, 1.0),
            "urgent_score_threshold": (0.0, 1.0),
            "watch_threshold_fraction": (0.0, 1.0),
            "adaptation_threshold_floor": (0.0, 1.0),
            "adaptation_threshold_ceiling": (0.0, 1.0),
        }
        for key, (lower, upper) in bounded.items():
            value = config[key]
            if value < lower or (upper is not None and value > upper):
                raise ValueError(f"{key} is outside its valid numeric range")
        if config["adaptation_threshold_floor"] >= config["adaptation_threshold_ceiling"]:
            raise ValueError("adaptation threshold floor must be below its ceiling")
        self.config = {**config, "alpha_conf": float(alpha_conf), "adapt_rate": float(adapt_rate)}
        self.config_id = str(config["config_id"])
        self.config_sha256 = hashlib.sha256(
            json.dumps(self.config, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.alpha_conf = alpha_conf
        self.adapt_rate = adapt_rate
        self.calibrated_threshold: Optional[float] = None
        self.running_threshold: Optional[float] = None
        self.is_calibrated = False
        # OOD baseline statistics on feature space
        self.feature_means: Optional[np.ndarray] = None
        self.feature_cov_inv: Optional[np.ndarray] = None
        self.ood_threshold: Optional[float] = None

    def calibrate(
        self, val_scores: np.ndarray, val_labels: np.ndarray
    ) -> "ConformalRiskControllerK8":
        """
        Calibrates the operating threshold on held-out validation data to strictly bound FNR.
        """
        val_scores = np.asarray(val_scores, dtype=float)
        val_labels = np.asarray(val_labels)
        if val_scores.ndim != 1 or val_labels.ndim != 1 or len(val_scores) != len(val_labels):
            raise ValueError(
                "validation scores and labels must be one-dimensional arrays of equal length"
            )
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
        cov = np.cov(X_train, rowvar=False) + self.config["covariance_regularizer"] * np.eye(
            X_train.shape[1]
        )
        self.feature_cov_inv = np.linalg.pinv(cov)
        self.ood_threshold = float(
            chi2.ppf(1.0 - self.config["ood_tail_probability"], df=X_train.shape[1])
        )
        return self

    def check_ood(self, x: np.ndarray) -> Tuple[bool, float]:
        """
        Computes Mahalanobis distance from reference training manifold.
        """
        if self.feature_means is None or self.feature_cov_inv is None or self.ood_threshold is None:
            return False, 0.0
        x = np.asarray(x, dtype=float)
        if x.shape != self.feature_means.shape or not np.all(np.isfinite(x)):
            raise ValueError("x must be a finite feature vector matching the fitted OOD dimensions")
        diff = x - self.feature_means
        dist_sq = float(diff @ self.feature_cov_inv @ diff)
        threshold = self.ood_threshold
        is_ood = dist_sq > threshold
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
        if not self.is_calibrated or self.running_threshold is None:
            return ConformalPredictionResult(
                risk_score=None,
                score_range=None,
                alert_tier="abstain",
                is_alert=False,
                conformal_quantile=None,
                abstention=AbstentionReason.ABSTAIN_UNCALIBRATED,
                explanation_summary="No calibration cohort is loaded. Defer this score for clinician review.",
                config_id=self.config_id,
                config_sha256=self.config_sha256,
            )
        # Check OOD abstention
        if feature_vector is not None:
            is_ood, dist = self.check_ood(feature_vector)
            ood_threshold = self.ood_threshold
            if is_ood and ood_threshold is not None:
                return ConformalPredictionResult(
                    risk_score=None,
                    score_range=None,
                    alert_tier="abstain",
                    is_alert=False,
                    conformal_quantile=self.running_threshold,
                    abstention=AbstentionReason.ABSTAIN_OOD,
                    explanation_summary=f"Feature vector exceeded the research OOD cutoff (Mahalanobis D={dist:.1f} > {np.sqrt(ood_threshold):.1f}). Review source data and assumptions.",
                    config_id=self.config_id,
                    config_sha256=self.config_sha256,
                )

        # Check epistemic uncertainty abstention
        if epistemic_std > self.config["epistemic_abstention_cutoff"]:
            return ConformalPredictionResult(
                risk_score=None,
                score_range=None,
                alert_tier="abstain",
                is_alert=False,
                conformal_quantile=self.running_threshold,
                abstention=AbstentionReason.ABSTAIN_HIGH_UNCERTAINTY,
                explanation_summary="The configured uncertainty screen withheld this research score. Review the source data and model assumptions.",
                config_id=self.config_id,
                config_sha256=self.config_sha256,
            )

        # Conformal interval
        margin = max(
            self.config["interval_minimum_half_width"],
            self.config["interval_normal_quantile"] * epistemic_std,
        )
        ci_low = max(0.0, raw_risk - margin)
        ci_high = min(1.0, raw_risk + margin)

        # Tiers
        is_alert = raw_risk >= self.running_threshold
        if raw_risk >= self.config["urgent_score_threshold"]:
            tier = "urgent"
        elif raw_risk >= self.running_threshold:
            tier = "review"
        elif raw_risk >= (self.running_threshold * self.config["watch_threshold_fraction"]):
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
            config_id=self.config_id,
            config_sha256=self.config_sha256,
        )

    def adapt_online(self, pred_alert: bool, true_event: bool) -> None:
        """
        Adaptive Conformal Inference (ACI) step: updates decision threshold
        to maintain exact coverage over non-stationary clinical environments.
        """
        if not self.is_calibrated or self.running_threshold is None:
            raise RuntimeError("K8 adaptation requires a calibrated research threshold")
        if not isinstance(pred_alert, (bool, np.bool_)) or not isinstance(
            true_event, (bool, np.bool_)
        ):
            raise ValueError("pred_alert and true_event must be boolean feedback values")
        # If false negative occurred (missed alert on true event) -> lower threshold
        if true_event and not pred_alert:
            self.running_threshold = max(
                self.config["adaptation_threshold_floor"], self.running_threshold - self.adapt_rate
            )
        # If false alarm occurred on confirmed non-recurrence -> raise threshold slightly
        elif pred_alert and not true_event:
            self.running_threshold = min(
                self.config["adaptation_threshold_ceiling"],
                self.running_threshold + (self.adapt_rate * self.alpha_conf),
            )


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
