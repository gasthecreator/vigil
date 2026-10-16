"""
packages/vigil-ml/vigil_ml/k8.py

Model K8: Conformal Risk Control, Out-of-Distribution (OOD) Gating, and Adaptive Conformal Inference.
Implements the K8 Acceptance Contract specified in docs/ml/K2-K8-CONTRACT.md.
"""

from __future__ import annotations

import numpy as np


class ConformalRiskController:
    """
    Conformal risk control threshold calibrator (Bates et al. 2021).
    Calibrates decision threshold tau on a calibration set to control
    the false-negative rate (or false alarm rate) below alpha:
        E[FNR] <= alpha
    without trivial alerting.
    """

    def __init__(self, alpha: float) -> None:
        self.alpha = float(alpha)
        self.tau_: float = 0.0

    def fit(self, scores: np.ndarray, labels: np.ndarray) -> "ConformalRiskController":
        """Calibrate detection threshold on held-out calibration cohort."""
        s = np.asarray(scores, dtype=float)
        y = np.asarray(labels, dtype=int)
        pos = s[y == 1]
        n = len(pos)
        if n == 0:
            self.tau_ = -np.inf
            return self

        pos_sorted = np.sort(pos)
        # Conformal index for distribution-free FNR risk control:
        # k = floor((n + 1) * alpha)
        k = int(np.floor((n + 1) * self.alpha))
        if k <= 0:
            self.tau_ = float(pos_sorted[0])
        elif k > n:
            self.tau_ = float(pos_sorted[-1])
        else:
            self.tau_ = float(pos_sorted[k - 1])
        return self

    def decide(self, scores: np.ndarray) -> np.ndarray:
        """Return boolean alert decision array (True = alert)."""
        s = np.asarray(scores, dtype=float)
        return s >= self.tau_


class OODGate:
    """
    Out-of-distribution gate using Mahalanobis distance with covariance regularization.
    Flags samples outside training support.
    """

    def __init__(self, alpha: float = 0.05) -> None:
        self.alpha = float(alpha)
        self.mu_: np.ndarray | None = None
        self.inv_cov_: np.ndarray | None = None
        self.threshold_: float = 0.0

    def fit(self, X: np.ndarray) -> "OODGate":
        """Fit empirical mean, regularized covariance, and threshold on inliers."""
        x = np.asarray(X, dtype=float)
        self.mu_ = np.mean(x, axis=0)
        diff = x - self.mu_
        cov = np.cov(diff, rowvar=False)
        # Numerical regularization for stability
        cov += np.eye(cov.shape[0]) * 1e-5
        self.inv_cov_ = np.linalg.pinv(cov)
        dists = np.sum((diff @ self.inv_cov_) * diff, axis=1)
        self.threshold_ = float(np.percentile(dists, (1.0 - self.alpha) * 100.0))
        return self

    def is_ood(self, X: np.ndarray) -> np.ndarray:
        """Return boolean mask (True = out-of-distribution)."""
        x = np.asarray(X, dtype=float)
        diff = x - self.mu_
        dists = np.sum((diff @ self.inv_cov_) * diff, axis=1)
        return dists > self.threshold_


class AdaptiveConformal:
    """
    Adaptive Conformal Inference (ACI) tracking coverage under temporal or covariate drift
    (Gibbs & Candès 2021).
    Dynamically adjusts effective miscoverage budget alpha_t:
        alpha_{t+1} = alpha_t + gamma * (alpha - err_t)
    where err_t = 0 if covered else 1.
    """

    def __init__(self, alpha: float, gamma: float = 0.005) -> None:
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self._alpha_t = float(alpha)

    @property
    def alpha_t(self) -> float:
        """Current adaptive significance level."""
        return self._alpha_t

    def update(self, covered: bool) -> None:
        """Update adaptive significance level based on observation coverage."""
        err = 0.0 if covered else 1.0
        self._alpha_t = self._alpha_t + self.gamma * (self.alpha - err)
