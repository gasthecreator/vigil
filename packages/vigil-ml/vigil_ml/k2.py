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

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import logsumexp


@dataclass(frozen=True)
class K2ResearchConfig:
    """Versioned K2 implementation defaults; they are not calibrated parameters."""

    config_id: str
    status: str
    source: str
    source_sha256: str
    alpha_pt: float
    sigma_log: float
    burn_in: int
    growth_grid: tuple[float, ...]
    tier_score_thresholds: tuple[tuple[str, float], ...]


def load_k2_research_config(path: Path | None = None) -> K2ResearchConfig:
    """Load and validate the versioned historical software defaults."""
    config_path = path or Path(__file__).resolve().parent / "models" / "k2_research_config_v1.json"
    raw_bytes = config_path.read_bytes()
    raw = json.loads(raw_bytes)
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported K2 research config schema")
    if (
        not raw.get("config_id")
        or raw.get("status") != "unvalidated_research_defaults"
        or not raw.get("source")
    ):
        raise ValueError("K2 defaults must remain explicitly unvalidated research settings")
    if isinstance(raw["alpha_pt"], bool) or isinstance(raw["sigma_log"], bool):
        raise ValueError("K2 config numeric settings must not be booleans")
    alpha_pt = float(raw["alpha_pt"])
    sigma_log = float(raw["sigma_log"])
    burn_in_raw = raw["burn_in"]
    if any(isinstance(value, bool) for value in raw["growth_grid"]):
        raise ValueError("K2 config growth_grid values must not be booleans")
    growth_grid = tuple(float(value) for value in raw["growth_grid"])
    tier_thresholds = raw["tier_score_thresholds"]
    if not np.isfinite(alpha_pt) or not 0.0 < alpha_pt < 1.0:
        raise ValueError("K2 config alpha_pt must be finite and between zero and one")
    if not np.isfinite(sigma_log) or sigma_log <= 0.0:
        raise ValueError("K2 config sigma_log must be finite and positive")
    if isinstance(burn_in_raw, bool) or not isinstance(burn_in_raw, int) or burn_in_raw < 1:
        raise ValueError("K2 config burn_in must be a positive integer")
    if not growth_grid or not all(np.isfinite(value) and value > 0.0 for value in growth_grid):
        raise ValueError("K2 config growth_grid must contain finite positive values")
    if len(set(growth_grid)) != len(growth_grid):
        raise ValueError("K2 config growth_grid values must be unique")
    names = ("watch", "review", "urgent")
    if set(tier_thresholds) != set(names):
        raise ValueError("K2 tier thresholds must have watch, review, urgent ordering")
    thresholds = tuple((name, float(tier_thresholds[name])) for name in names)
    if not all(np.isfinite(value) and value > 1.0 for _, value in thresholds):
        raise ValueError("K2 tier score thresholds must be finite and greater than one")
    if any(left[1] >= right[1] for left, right in zip(thresholds, thresholds[1:])):
        raise ValueError("K2 tier score thresholds must increase")
    return K2ResearchConfig(
        config_id=str(raw["config_id"]),
        status=str(raw["status"]),
        source=str(raw["source"]),
        source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        alpha_pt=alpha_pt,
        sigma_log=sigma_log,
        burn_in=burn_in_raw,
        growth_grid=growth_grid,
        tier_score_thresholds=thresholds,
    )


DEFAULT_K2_RESEARCH_CONFIG = load_k2_research_config()


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
        alpha_pt: float | None = None,
        sigma_log: float | None = None,
        burn_in: int | None = None,
        growth_grid: tuple[float, ...] | list[float] | None = None,
    ) -> None:
        config = DEFAULT_K2_RESEARCH_CONFIG
        alpha_pt = config.alpha_pt if alpha_pt is None else alpha_pt
        sigma_log = config.sigma_log if sigma_log is None else sigma_log
        burn_in = config.burn_in if burn_in is None else burn_in
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
        raw_grid = config.growth_grid if growth_grid is None else growth_grid
        if any(isinstance(value, (bool, np.bool_)) for value in raw_grid):
            raise ValueError("growth_grid values must be numeric non-boolean values")
        grid = np.asarray(raw_grid, dtype=float)
        if (
            grid.ndim != 1
            or len(grid) == 0
            or not np.isfinite(grid).all()
            or np.any(grid <= 0.0)
            or len(np.unique(grid)) != len(grid)
        ):
            raise ValueError("growth_grid must contain unique finite positive values")
        self.config_source_sha256 = config.source_sha256
        self.tier_score_thresholds = dict(config.tier_score_thresholds)
        default_values = (
            self.alpha_pt == config.alpha_pt
            and self.sigma_log == config.sigma_log
            and self.burn_in == config.burn_in
            and np.array_equal(grid, np.asarray(config.growth_grid))
        )
        self.config_id = config.config_id if default_values else "k2_custom_research"
        effective = {
            "alpha_pt": self.alpha_pt,
            "sigma_log": self.sigma_log,
            "burn_in": self.burn_in,
            "growth_grid": grid.tolist(),
            "tier_score_thresholds": self.tier_score_thresholds,
        }
        self.effective_config_sha256 = hashlib.sha256(
            json.dumps(effective, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()

        self.history: list[float] = []
        self.days: list[float] = []
        self._log_e: float = 0.0
        self._alert: bool = False

        # Configured growth-rate score grid; no supermartingale guarantee is established.
        self.lambdas = grid
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
        if self._log_e >= np.log(self.tier_score_thresholds["urgent"]):
            return AlertTier.URGENT
        elif self._log_e >= np.log(self.tier_score_thresholds["review"]):
            return AlertTier.REVIEW
        elif self._log_e >= np.log(self.tier_score_thresholds["watch"]):
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
