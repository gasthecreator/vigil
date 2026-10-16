"""
packages/vigil-ml/vigil_ml/k2.py

Model K2: Anytime-Valid Sequential Detection Engine.
Implements the K2 Acceptance Contract specified in docs/ml/K2-K8-CONTRACT.md.

Guarantees patient-level false-alarm rate control under continuous monitoring
using predictable recursive standardisation and mixture test supermartingales (e-processes).
"""

from enum import Enum
from typing import Any

import numpy as np
from scipy.special import logsumexp


class AlertTier(str, Enum):
    """Categorical anytime-valid alert tiers based on exact Ville thresholds."""
    NONE = "none"
    WATCH = "watch"       # alpha_pt = 0.20 (log_threshold = ln(5) ~= 1.609)
    REVIEW = "review"     # alpha_pt = 0.05 (log_threshold = ln(20) ~= 2.996)
    URGENT = "urgent"     # alpha_pt = 0.01 (log_threshold = ln(100) ~= 4.605)


class SequentialDetector:
    """
    Anytime-valid e-process detector providing rigorous patient-level false-alarm
    control under continuous, indefinite longitudinal monitoring.

    Uses recursive prediction residuals against the running baseline to eliminate
    bias accumulation across long monitoring horizons (Brown, Durbin, Evans 1975),
    combined with a mixture e-process over candidate doubling times / growth rates.
    """

    def __init__(
        self,
        alpha_pt: float = 0.05,
        sigma_log: float = 0.12,
        burn_in: int = 3,
    ) -> None:
        self.alpha_pt = float(alpha_pt)
        self.sigma_log = float(sigma_log)
        self.burn_in = int(burn_in)
        self.log_threshold = float(np.log(1.0 / self.alpha_pt))

        self.history: list[float] = []
        self.days: list[float] = []
        self._log_e: float = 0.0
        self._alert: bool = False

        # Mixture supermartingale grid over plausible exponential growth drifts
        # Covers doubling times from 30d to 180d
        self.lambdas = np.array([0.3, 0.5, 0.7, 1.0])
        self.log_weights = np.log(np.full(len(self.lambdas), 1.0 / len(self.lambdas)))
        self.log_e_components = np.zeros(len(self.lambdas))

    @property
    def alert(self) -> bool:
        """True once an alert has been raised (latched)."""
        return self._alert

    @property
    def log_e(self) -> float:
        """Current log e-value (anytime-valid evidence against 'no change')."""
        return self._log_e

    @property
    def tier(self) -> AlertTier:
        """Categorize anytime-valid evidence level into discrete alert tiers."""
        if self._log_e >= np.log(100.0):
            return AlertTier.URGENT
        elif self._log_e >= np.log(20.0):
            return AlertTier.REVIEW
        elif self._log_e >= np.log(5.0):
            return AlertTier.WATCH
        return AlertTier.NONE

    def integrate_with_risk_score(self, k3_or_b4_score: float) -> dict[str, Any]:
        """
        Documented interface integrating sequential e-process evidence with landmark risk score
        (K3 or B4) for surveillance decision support. Does NOT claim clinical utility.
        """
        return {
            "log_e": self.log_e,
            "e_value": float(np.exp(min(self.log_e, 700.0))),
            "tier": self.tier.value,
            "is_alert": self.alert,
            "landmark_risk_score": float(k3_or_b4_score),
            "combined_action": (
                "RECOMMEND_IMAGING" if (self.alert and k3_or_b4_score >= 0.15)
                else "CLINICAL_REVIEW" if (self.alert or k3_or_b4_score >= 0.15)
                else "CONTINUE_SURVEILLANCE"
            ),
        }

    def update(self, day: float, value: float | None) -> bool:
        """
        Incorporate a new observation at the specified day.
        Returns True once an alert has been raised (latched).
        None represents a missed / unmeasured observation.
        """
        if value is None:
            return self._alert

        y = float(np.log(max(value, 1e-6)))
        n = len(self.history)

        # Baseline burn-in accumulation
        if n < self.burn_in:
            self.history.append(y)
            self.days.append(float(day))
            return self._alert

        # Predictable plug-in standardisation:
        # Recursive prediction residual against running baseline:
        # w_t = sqrt(n / (n + 1)) * (y_t - y_bar_{1:n})
        # Under H_0 with unknown baseline, w_t has exact mean 0 and variance sigma^2,
        # preventing persistent bias accumulation over long monitoring (Ville validity).
        y_bar = float(np.mean(self.history))
        scale = float(np.sqrt(n / (n + 1.0)))
        w = scale * (y - y_bar)
        z = w / self.sigma_log

        # Sub-Gaussian supermartingale increments: M_t(lambda) = exp(lambda * z - lambda^2 / 2)
        for i, lam in enumerate(self.lambdas):
            inc = lam * z - 0.5 * (lam**2)
            self.log_e_components[i] += inc

        self._log_e = float(logsumexp(self.log_weights + self.log_e_components))
        if self._log_e >= self.log_threshold:
            self._alert = True

        self.history.append(y)
        self.days.append(float(day))
        return self._alert
