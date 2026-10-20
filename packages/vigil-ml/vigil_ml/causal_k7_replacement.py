"""Cross-fitted synthetic causal estimators for EXP-S8-K7-002.

This module is a separately registered replacement for the retired S8-K7-001
implementation. It is synthetic research code and is not a clinical estimator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class NonEstimableError(ValueError):
    """Raised when a registered estimator's support or data contract fails."""


@dataclass(frozen=True)
class SyntheticCohort:
    patient_ids: tuple[str, ...]
    covariates: FloatArray
    covariate_names: tuple[str, ...]
    treatment: IntArray
    outcome: IntArray
    delay_days: IntArray
    potential_outcome_probability_0: FloatArray
    potential_outcome_probability_1: FloatArray
    potential_outcome_0: IntArray
    potential_outcome_1: IntArray
    assignment_probability: FloatArray
    unmeasured_confounder: IntArray | None
    seed: int

    @property
    def true_risks(self) -> tuple[float, float]:
        return (
            float(np.mean(self.potential_outcome_probability_1)),
            float(np.mean(self.potential_outcome_probability_0)),
        )

    @property
    def true_effects(self) -> dict[str, float]:
        risk1, risk0 = self.true_risks
        return {
            "risk_treated": risk1,
            "risk_control": risk0,
            "risk_difference": risk1 - risk0,
            "risk_ratio": risk1 / risk0,
        }


def generate_cohort(
    *, n_patients: int = 5000, seed: int, unmeasured_confounding: bool
) -> SyntheticCohort:
    """Generate a cohort from the equations frozen in EXP-S8-K7-002/PREREG.md."""
    if isinstance(n_patients, bool) or not isinstance(n_patients, int) or n_patients < 100:
        raise ValueError("n_patients must be an integer of at least 100")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(6)]
    baseline_rng, u_rng, treatment_rng, y0_rng, y1_rng, delay_rng = streams

    subtype = baseline_rng.choice(3, size=n_patients, p=(0.35, 0.40, 0.25))
    age = np.clip(baseline_rng.normal(52.0, 10.0, size=n_patients), 25.0, 80.0)
    stage = baseline_rng.choice(3, size=n_patients, p=(0.30, 0.45, 0.25)) + 1
    distance = 5.0 + baseline_rng.exponential(35.0, size=n_patients)
    breakdowns = baseline_rng.poisson(0.4, size=n_patients)
    u = (
        u_rng.binomial(1, 0.30, size=n_patients)
        if unmeasured_confounding
        else np.zeros(n_patients, dtype=np.int64)
    )

    subtype_pmrt = (subtype == 1).astype(np.float64)
    subtype_tnbc = (subtype == 2).astype(np.float64)
    z = (
        -1.2
        + 0.5 * subtype_pmrt
        + 0.7 * subtype_tnbc
        + 0.015 * (distance - 40.0)
        + 0.4 * breakdowns
        + 0.02 * (age - 50.0)
        + 1.2 * u
    )
    expit_z = 1.0 / (1.0 + np.exp(-z))
    assignment_probability = 0.15 + 0.70 * expit_z
    treatment = treatment_rng.binomial(1, assignment_probability).astype(np.int64)
    delay_days = np.where(
        treatment == 1,
        delay_rng.integers(57, 181, size=n_patients),
        delay_rng.integers(14, 57, size=n_patients),
    ).astype(np.int64)
    if not np.array_equal(treatment, (delay_days > 56).astype(np.int64)):
        raise RuntimeError("generated treatment and delay definition disagree")

    logit_p0 = (
        -2.5
        + 0.4 * subtype_pmrt
        + 0.9 * subtype_tnbc
        + 0.35 * (stage - 1)
        + 0.01 * (age - 50.0)
        + 1.1 * u
    )
    p0 = 1.0 / (1.0 + np.exp(-logit_p0))
    p1 = 1.0 / (1.0 + np.exp(-(logit_p0 + np.log(1.18))))
    y0 = y0_rng.binomial(1, p0, size=n_patients).astype(np.int64)
    y1 = y1_rng.binomial(1, p1, size=n_patients).astype(np.int64)
    outcome = np.where(treatment == 1, y1, y0).astype(np.int64)
    covariates = np.column_stack(
        (subtype_pmrt, subtype_tnbc, age, stage, distance, breakdowns)
    ).astype(np.float64)

    cohort = SyntheticCohort(
        patient_ids=tuple(f"K7-002-{seed}-{i}" for i in range(n_patients)),
        covariates=covariates,
        covariate_names=(
            "subtype_pmrt",
            "subtype_tnbc",
            "age_years",
            "stage",
            "travel_distance_km",
            "breakdown_count",
        ),
        treatment=treatment,
        outcome=outcome,
        delay_days=delay_days,
        potential_outcome_probability_0=p0.astype(np.float64),
        potential_outcome_probability_1=p1.astype(np.float64),
        potential_outcome_0=y0,
        potential_outcome_1=y1,
        assignment_probability=assignment_probability.astype(np.float64),
        unmeasured_confounder=u.copy() if unmeasured_confounding else None,
        seed=seed,
    )
    _validate_cohort(cohort)
    return cohort


def _validate_cohort(cohort: SyntheticCohort) -> None:
    n = len(cohort.patient_ids)
    if not n or len(set(cohort.patient_ids)) != n:
        raise ValueError("patient IDs must be non-empty and unique")
    if cohort.covariates.ndim != 2 or cohort.covariates.shape != (n, 6):
        raise ValueError("covariates must have shape (n_patients, 6)")
    for name, values in (
        ("treatment", cohort.treatment),
        ("outcome", cohort.outcome),
        ("delay_days", cohort.delay_days),
        ("potential outcome 0", cohort.potential_outcome_0),
        ("potential outcome 1", cohort.potential_outcome_1),
    ):
        if values.shape != (n,):
            raise ValueError(f"{name} must have shape (n_patients,)")
    if not np.all(np.isfinite(cohort.covariates)):
        raise ValueError("covariates must be finite")
    for name, values in (
        ("treatment", cohort.treatment),
        ("outcome", cohort.outcome),
        ("potential outcome 0", cohort.potential_outcome_0),
        ("potential outcome 1", cohort.potential_outcome_1),
    ):
        if not np.all(np.isin(values, (0, 1))):
            raise ValueError(f"{name} must be binary")
    if not np.array_equal(cohort.treatment, (cohort.delay_days > 56).astype(np.int64)):
        raise ValueError("treatment must equal delay_days > 56")
    for name, probability_values in (
        ("assignment probability", cohort.assignment_probability),
        ("potential outcome probability 0", cohort.potential_outcome_probability_0),
        ("potential outcome probability 1", cohort.potential_outcome_probability_1),
    ):
        if probability_values.shape != (n,) or not np.all(np.isfinite(probability_values)):
            raise ValueError(f"{name} must be a finite vector of length n_patients")
        if np.any((probability_values <= 0.0) | (probability_values >= 1.0)):
            raise ValueError(f"{name} must be strictly between zero and one")
    if cohort.unmeasured_confounder is not None and (
        cohort.unmeasured_confounder.shape != (n,)
        or not np.all(np.isin(cohort.unmeasured_confounder, (0, 1)))
    ):
        raise ValueError("unmeasured confounder must be a binary vector of length n_patients")


def _ratio(risk_treated: float, risk_control: float) -> float | None:
    if not np.isfinite(risk_treated) or not np.isfinite(risk_control) or risk_control <= 0:
        return None
    value = risk_treated / risk_control
    return float(value) if np.isfinite(value) and value > 0 else None


def compute_e_value(rr: float, ci_95: tuple[float, float] | None = None) -> dict[str, float]:
    """Compute E-values for an RR and the confidence limit nearest the null."""
    if not np.isfinite(rr) or rr <= 0:
        raise ValueError("risk ratio must be finite and positive")

    def value(ratio: float) -> float:
        risk_ratio = ratio if ratio >= 1.0 else 1.0 / ratio
        return float(risk_ratio + np.sqrt(risk_ratio * (risk_ratio - 1.0)))

    result = {"point_estimate": value(rr), "confidence_limit_nearest_null": 1.0}
    if ci_95 is not None:
        low, high = ci_95
        if not (np.isfinite(low) and np.isfinite(high) and 0 < low <= high):
            raise ValueError(
                "confidence interval must be an ordered pair of finite positive values"
            )
        nearest = low if rr >= 1.0 else high
        if (rr >= 1.0 and nearest > 1.0) or (rr < 1.0 and nearest < 1.0):
            result["confidence_limit_nearest_null"] = value(nearest)
    return result


def _contrast(risk_treated: float, risk_control: float) -> dict[str, float | str | None]:
    rr = _ratio(risk_treated, risk_control)
    rd = risk_treated - risk_control
    return {
        "risk_treated": float(risk_treated) if np.isfinite(risk_treated) else None,
        "risk_control": float(risk_control) if np.isfinite(risk_control) else None,
        "risk_ratio": rr,
        "risk_difference": float(rd) if np.isfinite(rd) else None,
        "undefined_reason": "non_positive_or_non_finite_control_risk" if rr is None else None,
    }


def compute_smd(
    x: FloatArray, treatment: IntArray, weights: FloatArray | None = None
) -> float | None:
    """Absolute SMD using the unweighted pooled sample SD as denominator."""
    x = np.asarray(x, dtype=np.float64)
    a = np.asarray(treatment)
    if x.ndim != 1 or a.ndim != 1 or x.shape != a.shape or not np.all(np.isfinite(x)):
        raise ValueError("x and treatment must be finite one-dimensional arrays of equal length")
    if not np.all(np.isin(a, (0, 1))) or not np.any(a == 0) or not np.any(a == 1):
        raise ValueError("both binary treatment groups must be represented")
    x1, x0 = x[a == 1], x[a == 0]
    mean1 = (
        float(np.mean(x1)) if weights is None else float(np.average(x1, weights=weights[a == 1]))
    )
    mean0 = (
        float(np.mean(x0)) if weights is None else float(np.average(x0, weights=weights[a == 0]))
    )
    var1 = float(np.var(x1, ddof=1)) if len(x1) > 1 else 0.0
    var0 = float(np.var(x0, ddof=1)) if len(x0) > 1 else 0.0
    pooled_sd = float(np.sqrt((var1 + var0) / 2.0))
    difference = abs(mean1 - mean0)
    if pooled_sd == 0.0:
        return 0.0 if difference == 0.0 else None
    return difference / pooled_sd


def _model() -> Any:
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(solver="lbfgs", C=1.0, max_iter=1000),
    )


def _crossfit_nuisance(
    x: FloatArray, a: IntArray, y: IntArray, *, fold_seed: int
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    n = len(a)
    raw_e = np.full(n, np.nan, dtype=np.float64)
    mu1 = np.full(n, np.nan, dtype=np.float64)
    mu0 = np.full(n, np.nan, dtype=np.float64)
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=fold_seed)
    for train_idx, heldout_idx in splitter.split(x, a):
        if len(np.unique(a[train_idx])) != 2:
            raise NonEstimableError("fold training partition lacks a treatment arm")
        propensity = _model().fit(x[train_idx], a[train_idx])
        raw_e[heldout_idx] = propensity.predict_proba(x[heldout_idx])[:, 1]
        for arm, prediction in ((1, mu1), (0, mu0)):
            arm_train = train_idx[a[train_idx] == arm]
            if len(np.unique(y[arm_train])) != 2:
                raise NonEstimableError(f"fold training arm {arm} lacks an outcome class")
            model = _model().fit(x[arm_train], y[arm_train])
            prediction[heldout_idx] = model.predict_proba(x[heldout_idx])[:, 1]
    if not all(np.all(np.isfinite(arr)) for arr in (raw_e, mu1, mu0)):
        raise NonEstimableError("cross-fitted nuisance predictions are incomplete or non-finite")
    return raw_e, np.clip(raw_e, 0.15, 0.85), mu1, mu0


def estimate_effects(
    covariates: FloatArray,
    treatment: IntArray,
    outcome: IntArray,
    covariate_names: tuple[str, ...],
    *,
    fold_seed: int,
) -> dict[str, Any]:
    """Estimate marginal contrasts using the registered cross-fitting contract."""
    x = np.asarray(covariates, dtype=np.float64)
    a = np.asarray(treatment, dtype=np.int64)
    y = np.asarray(outcome, dtype=np.int64)
    if (
        x.ndim != 2
        or x.shape[1] != len(covariate_names)
        or x.shape[0] != len(a)
        or y.shape != a.shape
    ):
        raise ValueError("covariate, treatment, outcome, and name dimensions must align")
    if (
        len(a) < 100
        or not np.all(np.isfinite(x))
        or not np.all(np.isin(a, (0, 1)))
        or not np.all(np.isin(y, (0, 1)))
    ):
        raise ValueError("estimator inputs must be finite binary vectors and at least 100 rows")
    if len(np.unique(a)) != 2:
        raise NonEstimableError("cohort lacks a treatment arm")
    for arm in (0, 1):
        if len(np.unique(y[a == arm])) != 2:
            raise NonEstimableError(f"treatment arm {arm} lacks an outcome class")

    raw_e, e_hat, mu1, mu0 = _crossfit_nuisance(x, a, y, fold_seed=fold_seed)
    p1 = float(np.mean(a))
    weights = np.where(a == 1, p1 / e_hat, (1.0 - p1) / (1.0 - e_hat))
    max_weight = float(np.max(weights))
    if not np.all(np.isfinite(weights)) or max_weight > 10.0:
        raise NonEstimableError("maximum stabilized weight exceeds 10 or is non-finite")

    risks: dict[str, tuple[float, float]] = {}
    risks["naive"] = (
        float(np.mean(y[a == 1])),
        float(np.mean(y[a == 0])),
    )
    risks["iptw"] = (
        float(np.average(y[a == 1], weights=weights[a == 1])),
        float(np.average(y[a == 0], weights=weights[a == 0])),
    )
    risks["gcomp"] = (float(np.mean(mu1)), float(np.mean(mu0)))
    aipw1 = mu1 + (a / e_hat) * (y - mu1)
    aipw0 = mu0 + ((1 - a) / (1.0 - e_hat)) * (y - mu0)
    risks["aipw"] = (float(np.mean(aipw1)), float(np.mean(aipw0)))

    smd_unweighted = {name: compute_smd(x[:, idx], a) for idx, name in enumerate(covariate_names)}
    smd_weighted = {
        name: compute_smd(x[:, idx], a, weights) for idx, name in enumerate(covariate_names)
    }
    valid_weighted_smd = [v for v in smd_weighted.values() if v is not None]
    max_smd = max(valid_weighted_smd) if len(valid_weighted_smd) == len(smd_weighted) else None
    return {
        "n_patients": len(a),
        "timely_count": int(np.sum(a == 0)),
        "delayed_count": int(np.sum(a == 1)),
        "estimates": {name: _contrast(r1, r0) for name, (r1, r0) in risks.items()},
        "weight_diagnostics": {
            "minimum_raw_propensity": float(np.min(raw_e)),
            "maximum_raw_propensity": float(np.max(raw_e)),
            "raw_predictions_outside_registered_bounds": int(
                np.sum((raw_e < 0.15) | (raw_e > 0.85))
            ),
            "minimum_stabilized_weight": float(np.min(weights)),
            "maximum_stabilized_weight": max_weight,
        },
        "covariate_balance": {
            "unweighted_smd": smd_unweighted,
            "weighted_smd": smd_weighted,
            "maximum_weighted_smd": max_smd,
        },
    }


def bootstrap_inference(
    covariates: FloatArray,
    treatment: IntArray,
    outcome: IntArray,
    covariate_names: tuple[str, ...],
    *,
    fold_seed: int,
    bootstrap_seed: int,
    n_bootstrap: int = 1000,
) -> dict[str, Any]:
    """Patient bootstrap with complete nuisance refitting for each resample."""
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap != 1000:
        raise ValueError("registered bootstrap count is exactly 1000")
    n = len(treatment)
    rng = np.random.default_rng(bootstrap_seed)
    names = ("naive", "iptw", "gcomp", "aipw")
    replicates: dict[str, list[float]] = {name: [] for name in names}
    failures = {name: 0 for name in names}
    for replicate in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        try:
            estimate = estimate_effects(
                covariates[idx],
                treatment[idx],
                outcome[idx],
                covariate_names,
                fold_seed=fold_seed + replicate + 1,
            )
            for name in names:
                rr = estimate["estimates"][name]["risk_ratio"]
                if rr is None:
                    failures[name] += 1
                else:
                    replicates[name].append(rr)
        except NonEstimableError:
            for name in names:
                failures[name] += 1

    intervals: dict[str, Any] = {}
    for name in names:
        count = failures[name]
        if count / n_bootstrap > 0.05 or not replicates[name]:
            intervals[name] = {
                "ci_95": None,
                "non_estimable_resamples": count,
                "reason": "more_than_five_percent_non_estimable"
                if count / n_bootstrap > 0.05
                else "no_defined_resamples",
            }
        else:
            low, high = np.percentile(np.asarray(replicates[name]), (2.5, 97.5))
            intervals[name] = {
                "ci_95": [float(low), float(high)],
                "non_estimable_resamples": count,
                "defined_resamples": len(replicates[name]),
                "reason": None,
            }
    return {"bootstrap_replications": n_bootstrap, "confidence_intervals": intervals}
