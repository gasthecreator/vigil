"""Module M3: Plausibility Adjudicator.

Compares one tumor-marker observation with a patient's prior results under an explicit
Bayesian 3-way generative mixture model. It is not a longitudinal recurrence detector.

Research action policy: outlier results are never dismissed ("dismissed" is not an allowed action).
Results are classified as:
  - "abstain": insufficient prior history to form a baseline; no probabilities are emitted
  - "escalate": model-conditional action at the configured real-change boundary
  - "explained": model-conditional action at the configured stable boundary
  - "needs_repeat": action at the configured gross-error boundary or
    indeterminate variation requiring confirmation before clinical intervention.

Numeric assumptions are loaded from `models/m3_assumptions_v1.json` and are synthetic research settings.
The reference-change formula is conventional; its biological variation inputs are separately sourced in E9.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple, Union, cast


@dataclass(frozen=True)
class M3Assumptions:
    """Versioned synthetic M3 assumptions; none are clinical estimates."""

    config_id: str
    status: str
    source: str
    config_sha256: str
    rcv_z: float
    illustrative_cv_analytical: float
    illustrative_cv_within: float
    p_error_prior: float
    p_real_prior: float
    inter_lab_cv: float
    real_change_ratio_min: float
    real_change_ratio_max: float
    gross_error_mode_weights: tuple[float, float, float]
    population_error_log_median: float
    population_error_log_sd: float
    decimal_shift_factor: float
    error_needs_repeat_threshold: float
    real_change_escalate_threshold: float
    stable_explained_threshold: float

    @property
    def effective_config_sha256(self) -> str:
        """Hash the exact assumption values used, independent of source-file formatting."""
        payload = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "config_sha256"
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(encoded).hexdigest()

    def __post_init__(self) -> None:
        numeric = (
            self.rcv_z,
            self.illustrative_cv_analytical,
            self.illustrative_cv_within,
            self.p_error_prior,
            self.p_real_prior,
            self.inter_lab_cv,
            self.real_change_ratio_min,
            self.real_change_ratio_max,
            *self.gross_error_mode_weights,
            self.population_error_log_median,
            self.population_error_log_sd,
            self.decimal_shift_factor,
            self.error_needs_repeat_threshold,
            self.real_change_escalate_threshold,
            self.stable_explained_threshold,
        )
        if not self.config_id or not self.source or self.status != "synthetic_research_assumptions":
            raise ValueError("M3 assumptions must have an id and remain synthetic research settings")
        if len(self.config_sha256) != 64 or any(char not in "0123456789abcdef" for char in self.config_sha256):
            raise ValueError("M3 assumptions must carry a lowercase SHA-256 config hash")
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("M3 assumptions must all be finite")
        if self.rcv_z <= 0 or min(self.illustrative_cv_analytical, self.illustrative_cv_within, self.inter_lab_cv) < 0:
            raise ValueError("M3 CV and RCV settings must be nonnegative and z must be positive")
        if self.p_error_prior < 0 or self.p_real_prior < 0 or self.p_error_prior + self.p_real_prior >= 1:
            raise ValueError("M3 component priors must be nonnegative and sum to less than one")
        if not 0 < self.real_change_ratio_min < self.real_change_ratio_max:
            raise ValueError("M3 real-change ratio bounds must be positive and increasing")
        if len(self.gross_error_mode_weights) != 3 or any(weight < 0 for weight in self.gross_error_mode_weights):
            raise ValueError("M3 gross-error weights must contain three nonnegative values")
        if not math.isclose(sum(self.gross_error_mode_weights), 1.0, abs_tol=1e-12):
            raise ValueError("M3 gross-error mode weights must sum to one")
        if self.population_error_log_median <= 0 or self.population_error_log_sd <= 0 or self.decimal_shift_factor <= 1:
            raise ValueError("M3 gross-error scale and decimal-shift settings are invalid")
        if any(not 0 <= threshold <= 1 for threshold in (
            self.error_needs_repeat_threshold,
            self.real_change_escalate_threshold,
            self.stable_explained_threshold,
        )):
            raise ValueError("M3 action thresholds must be probabilities in [0, 1]")


def load_m3_assumptions(path: Path | None = None) -> M3Assumptions:
    """Load the versioned synthetic research configuration."""
    config_path = path or Path(__file__).resolve().parent / "models" / "m3_assumptions_v1.json"
    config_bytes = config_path.read_bytes()
    raw = json.loads(config_bytes)
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported M3 assumptions schema version")
    expected_modes = ["population_draw", "decimal_shift_up", "decimal_shift_down"]
    if raw.get("gross_error", {}).get("modes") != expected_modes:
        raise ValueError("M3 gross-error modes must use the configured supported ordering")
    mode_weights = tuple(float(value) for value in raw["gross_error"]["mode_weights"])
    if len(mode_weights) != 3:
        raise ValueError("M3 gross-error mode weights must contain exactly three values")
    return M3Assumptions(
        config_id=raw["config_id"],
        status=raw["status"],
        source=raw["source"],
        config_sha256=hashlib.sha256(config_bytes).hexdigest(),
        rcv_z=float(raw["rcv_z"]),
        illustrative_cv_analytical=float(raw["illustrative_marker_cv"]["analytical"]),
        illustrative_cv_within=float(raw["illustrative_marker_cv"]["within_subject"]),
        p_error_prior=float(raw["priors"]["error"]),
        p_real_prior=float(raw["priors"]["real_change"]),
        inter_lab_cv=float(raw["inter_lab_cv"]),
        real_change_ratio_min=float(raw["real_change_ratio"]["minimum"]),
        real_change_ratio_max=float(raw["real_change_ratio"]["maximum"]),
        gross_error_mode_weights=mode_weights,
        population_error_log_median=float(raw["gross_error"]["population_log_median"]),
        population_error_log_sd=float(raw["gross_error"]["population_log_sd"]),
        decimal_shift_factor=float(raw["gross_error"]["decimal_shift_factor"]),
        error_needs_repeat_threshold=float(raw["action_thresholds"]["error_needs_repeat"]),
        real_change_escalate_threshold=float(raw["action_thresholds"]["real_change_escalate"]),
        stable_explained_threshold=float(raw["action_thresholds"]["stable_explained"]),
    )


DEFAULT_M3_ASSUMPTIONS = load_m3_assumptions()


def rcv(
    cv_analytical: float,
    cv_within: float,
    z: float = DEFAULT_M3_ASSUMPTIONS.rcv_z,
    log_normal: bool = False,
) -> Union[float, Tuple[float, float]]:
    """Calculate Reference Change Value (RCV).

    Args:
        cv_analytical: Analytical coefficient of variation (s_A / mean).
        cv_within: Within-subject biological coefficient of variation (s_I / mean).
        z: Z-score multiplier; defaults to the versioned M3 research configuration.
        log_normal: If True, computes asymmetrical log-normal RCV (up, down).
                    If False, computes classical symmetrical Gaussian RCV.

    Returns:
        float if log_normal=False: sqrt(2) * z * sqrt(cva^2 + cvi^2)
        tuple (up, down) if log_normal=True:
            up = exp(z * sqrt(2) * s) - 1
            down = exp(-z * sqrt(2) * s) - 1
            where s = sqrt(ln(1 + cva^2) + ln(1 + cvi^2))
    """
    for name, value in (("cv_analytical", cv_analytical), ("cv_within", cv_within), ("z", z)):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite, got {value}")
    if cv_analytical < 0.0 or cv_within < 0.0:
        raise ValueError("Coefficient of variation values must be nonnegative")
    if z <= 0.0:
        raise ValueError("z must be positive")
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


def abstain(
    reason: Literal["insufficient_history", "clinical_validation_unavailable"],
) -> Dict[str, Any]:
    """Return an explicit M3 abstention without manufacturing component scores."""
    return {
        "p_real": None,
        "p_error": None,
        "p_stable": None,
        "action": "abstain",
        "abstention": True,
        "abstention_reason": reason,
        "rationale_facts": [],
    }


def adjudicate(
    history: List[Tuple[float, float]],
    new_day: float,
    new_value: float,
    cv_analytical: float,
    cv_within: float,
    lab_changed: bool = False,
    inter_lab_cv: float = DEFAULT_M3_ASSUMPTIONS.inter_lab_cv,
    p_error_prior: float = DEFAULT_M3_ASSUMPTIONS.p_error_prior,
    p_real_prior: float = DEFAULT_M3_ASSUMPTIONS.p_real_prior,
    assumptions: M3Assumptions | None = None,
) -> Dict[str, Any]:
    """Adjudicate marker plausibility via 3-way Bayesian generative mixture model.

    Evaluates whether the newly observed marker measurement represents:
      1. Real change: persistent increase over the configured ratio support
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
        p_error_prior: Synthetic prior override; otherwise the versioned config value is used.
        p_real_prior: Synthetic prior override; otherwise the versioned config value is used.
        assumptions: Optional full versioned config; when supplied it takes precedence over scalar overrides.

    Returns:
        dict containing:
            "p_real": Posterior model weight for the assumed real-change component.
            "p_error": Posterior model weight for the assumed gross-error component.
            "p_stable": Posterior model weight for the assumed stable component.
            "action": "abstain" when history is unavailable, otherwise one of the three adjudications.
            "rationale_facts": Provenance-traceable structured facts for downstream narrative.
    """
    if assumptions is not None:
        config = assumptions
    elif (inter_lab_cv, p_error_prior, p_real_prior) == (
        DEFAULT_M3_ASSUMPTIONS.inter_lab_cv,
        DEFAULT_M3_ASSUMPTIONS.p_error_prior,
        DEFAULT_M3_ASSUMPTIONS.p_real_prior,
    ):
        config = DEFAULT_M3_ASSUMPTIONS
    else:
        config = replace(
            DEFAULT_M3_ASSUMPTIONS,
            inter_lab_cv=inter_lab_cv,
            p_error_prior=p_error_prior,
            p_real_prior=p_real_prior,
        )
    inter_lab_cv = config.inter_lab_cv
    p_error_prior = config.p_error_prior
    p_real_prior = config.p_real_prior
    inputs = {
        "new_day": new_day,
        "new_value": new_value,
        "cv_analytical": cv_analytical,
        "cv_within": cv_within,
        "inter_lab_cv": inter_lab_cv,
        "p_error_prior": p_error_prior,
        "p_real_prior": p_real_prior,
    }
    for name, value in inputs.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite, got {value}")
    if new_value <= 0.0:
        raise ValueError(f"Observed value must be positive, got {new_value}")
    for name, value in (("cv_analytical", cv_analytical), ("cv_within", cv_within), ("inter_lab_cv", inter_lab_cv)):
        if value < 0.0:
            raise ValueError(f"{name} must be nonnegative, got {value}")
    if p_error_prior < 0.0 or p_real_prior < 0.0 or p_error_prior + p_real_prior >= 1.0:
        raise ValueError("p_error_prior and p_real_prior must be nonnegative and sum to less than 1")
    if cv_analytical == 0.0 and cv_within == 0.0:
        raise ValueError("cv_analytical and cv_within cannot both be zero")

    for day, value in history:
        if not math.isfinite(day) or not math.isfinite(value):
            raise ValueError("Historical days and values must be finite")
        if value <= 0.0:
            raise ValueError("Historical values must be positive")
        if day >= new_day:
            raise ValueError("Historical observations must precede the current observation")

    # A current result cannot supply its own baseline. With no prior draw, abstain
    # instead of manufacturing a stable posterior from the observation itself.
    if not history:
        return abstain("insufficient_history")

    # Compute personalized baseline from historical draws (geometric mean)
    log_history = [math.log(val) for _, val in history]
    n_hist = len(log_history)
    if n_hist > 0:
        log_base = sum(log_history) / n_hist
    else:  # guarded above; retained as a defensive invariant
        raise RuntimeError("M3 baseline requires at least one prior observation")

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

    # 2. Likelihood given real change: configured log-uniform ratio convolved with N(0, sig^2).
    a, b = math.log(config.real_change_ratio_min), math.log(config.real_change_ratio_max)
    phi_a = _norm_cdf((log_ratio - a) / sig)
    phi_b = _norm_cdf((log_ratio - b) / sig)
    lik_real = max((phi_a - phi_b) / (b - a), 1e-300)

    # 3. Likelihood given gross error (configured mixture of three error mechanisms):
    # Mode 0: Population draw / sample mixup using the configured log median and standard deviation.
    sig_pop_sq = config.population_error_log_sd**2 + (inter_lab_cv**2 if lab_changed else 0.0)
    sig_pop = math.sqrt(sig_pop_sq)
    lik_err_pop = _norm_pdf(log_y, math.log(config.population_error_log_median), sig_pop)

    # Mode 1: Configured decimal shift up: log(y / L) ~ N(ln(factor), sig^2)
    lik_err_x10 = _norm_pdf(log_ratio, math.log(config.decimal_shift_factor), sig)

    # Mode 2: Configured decimal shift down: log(y / L) ~ N(-ln(factor), sig^2)
    lik_err_div10 = _norm_pdf(log_ratio, -math.log(config.decimal_shift_factor), sig)

    lik_error = (
        config.gross_error_mode_weights[0] * lik_err_pop
        + config.gross_error_mode_weights[1] * lik_err_x10
        + config.gross_error_mode_weights[2] * lik_err_div10
    )

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
    if p_error >= config.error_needs_repeat_threshold:
        action = "needs_repeat"
    elif p_real >= config.real_change_escalate_threshold:
        action = "escalate"
    elif p_stable >= config.stable_explained_threshold:
        action = "explained"
    else:
        action = "needs_repeat"

    rcv_metric = cast(float, rcv(cv_analytical, cv_within, z=config.rcv_z, log_normal=False))

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
        "abstention": False,
        "abstention_reason": None,
        "assumption_config_id": config.config_id,
        "assumption_status": config.status,
        "assumption_config_sha256": config.effective_config_sha256,
        "assumption_source_sha256": config.config_sha256,
        "rationale_facts": rationale_facts,
    }
