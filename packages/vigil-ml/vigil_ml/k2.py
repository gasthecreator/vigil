"""
packages/vigil-ml/vigil_ml/k2.py

Model K2: Sequential Detection Research Score.
Implements the K2 Acceptance Contract specified in docs/ml/K2-K8-CONTRACT.md.

Accumulates exponential-mixture scores for sequential marker changes. Ville
validity has not been established: the recursive residual is not conditionally
centered given the observed history, and calibration on a finite synthetic
cohort does not prove a conditional scale bound. Empirical stress results are
not a proof of validity.
"""

from enum import Enum
from typing import Any

import numpy as np
from scipy.special import logsumexp


class AlertTier(str, Enum):
    """Categorical software score tiers; not calibrated alert guarantees."""
    NONE = "none"
    WATCH = "watch"       # alpha_pt = 0.20 (log_threshold = ln(5) ~= 1.609)
    REVIEW = "review"     # alpha_pt = 0.05 (log_threshold = ln(20) ~= 2.996)
    URGENT = "urgent"     # alpha_pt = 0.01 (log_threshold = ln(100) ~= 4.605)


class SequentialDetector:
    """
    Exponential-mixture score detector; this implementation is not established
    as an e-process for the unknown-baseline null.

    Uses recursive prediction residuals against the running baseline to eliminate
    bias accumulation across long monitoring horizons (Brown, Durbin, Evans 1975),
    combined with an exponential-mixture score over candidate growth rates.
    """

    def __init__(
        self,
        alpha_pt: float = 0.05,
        sigma_log: float = 0.12,
        burn_in: int = 3,
    ) -> None:
        if isinstance(alpha_pt, (bool, np.bool_)) or isinstance(sigma_log, (bool, np.bool_)):
            raise ValueError("alpha_pt and sigma_log must be numeric non-boolean values")
        self.alpha_pt = float(alpha_pt)
        self.sigma_log = float(sigma_log)
        if not np.isfinite(self.alpha_pt) or not 0.0 < self.alpha_pt < 1.0:
            raise ValueError("alpha_pt must be finite and strictly between 0 and 1")
        if not np.isfinite(self.sigma_log) or self.sigma_log <= 0.0:
            raise ValueError("sigma_log must be finite and positive")
        try:
            numeric_burn_in = float(burn_in)
        except (TypeError, ValueError, OverflowError):
            numeric_burn_in = float("nan")
        if (
            isinstance(burn_in, (bool, np.bool_))
            or not np.isfinite(numeric_burn_in)
            or not numeric_burn_in.is_integer()
            or numeric_burn_in < 1
        ):
            raise ValueError("burn_in must be a positive integer")
        self.burn_in = int(numeric_burn_in)
        self.log_threshold = float(-np.log(self.alpha_pt))

        self.history: list[float] = []
        self.days: list[float] = []
        self._log_e: float = 0.0
        self._alert: bool = False

        # Candidate growth-rate score grid; no supermartingale guarantee is established.
        self.lambdas = np.array([0.3, 0.5, 0.7, 1.0])
        self.log_weights = np.log(np.full(len(self.lambdas), 1.0 / len(self.lambdas)))
        self.log_e_components = np.zeros(len(self.lambdas))

    @property
    def alert(self) -> bool:
        """True once an alert has been raised (latched)."""
        return self._alert

    @property
    def log_e(self) -> float:
        """Current log mixture score; it is not a calibrated evidence value."""
        return self._log_e

    @property
    def tier(self) -> AlertTier:
        """Categorize the current score into software tiers."""
        if self._log_e >= np.log(100.0):
            return AlertTier.URGENT
        elif self._log_e >= np.log(20.0):
            return AlertTier.REVIEW
        elif self._log_e >= np.log(5.0):
            return AlertTier.WATCH
        return AlertTier.NONE

    def integrate_with_risk_score(
        self, k3_or_b4_score: float, imaging_threshold: float
    ) -> dict[str, Any]:
        """
        Disabled adapter retained for a clear migration error. Neither model
        input nor the K2 score has validated utility for recommending care.
        """
        if isinstance(k3_or_b4_score, (bool, np.bool_)) or isinstance(
            imaging_threshold, (bool, np.bool_)
        ):
            raise ValueError("risk score and threshold must be numeric non-boolean values")
        risk_score = float(k3_or_b4_score)
        threshold = float(imaging_threshold)
        if not np.isfinite(risk_score) or not 0.0 <= risk_score <= 1.0:
            raise ValueError("k3_or_b4_score must be finite and between 0 and 1")
        if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError("imaging_threshold must be between 0 and 1")
        raise RuntimeError(
            "K2 risk-score integration is disabled because neither score nor threshold "
            "has validated clinical utility"
        )

    def update(self, day: float, value: float | None) -> bool:
        """
        Incorporate a new observation at the specified day.
        Returns True once an alert has been raised (latched).
        None represents a missed / unmeasured observation.
        """
        numeric_day = float(day)
        if isinstance(day, (bool, np.bool_)) or not np.isfinite(numeric_day):
            raise ValueError("day must be finite and numeric")
        if self.days and numeric_day < self.days[-1]:
            raise ValueError("observed days must be nondecreasing")
        if value is None:
            self.days.append(numeric_day)
            return self._alert

        if isinstance(value, (bool, np.bool_)):
            raise ValueError("value must be a finite positive measurement")
        numeric_value = float(value)
        if not np.isfinite(numeric_value) or numeric_value <= 0.0:
            raise ValueError("value must be a finite positive measurement")
        y = float(np.log(numeric_value))
        n = len(self.history)

        # Baseline burn-in accumulation
        if n < self.burn_in:
            self.history.append(y)
            self.days.append(numeric_day)
            return self._alert

        # Predictable plug-in standardisation:
        # Recursive prediction residual against running baseline:
        # w_t = sqrt(n / (n + 1)) * (y_t - y_bar_{1:n})
        # Under a fixed-mean Gaussian model, this residual is unconditionally
        # centered. Its conditional mean given the observed history is not zero.
        y_bar = float(np.mean(self.history))
        scale = float(np.sqrt(n / (n + 1.0)))
        w = scale * (y - y_bar)
        z = w / self.sigma_log

        # Candidate mixture score increment; the supermartingale condition is unproved.
        for i, lam in enumerate(self.lambdas):
            inc = lam * z - 0.5 * (lam**2)
            self.log_e_components[i] += inc

        self._log_e = float(logsumexp(self.log_weights + self.log_e_components))
        if self._log_e >= self.log_threshold:
            self._alert = True

        self.history.append(y)
        self.days.append(numeric_day)
        return self._alert
