"""Causal Analysis of Treatment Delay and Recurrence (K7 / Study S8-K7).

Implements Target-Trial Emulation for Radiotherapy Treatment Delay:
- Pre-Registration: docs/studies/PREREG-S8-K7.md
- Master Plan §3, §6.7 (M7), §11; ML_PROGRAM §3.7, §6 (Study S8)

Methods:
- Doubly-Robust Augmented Inverse Probability Weighting (AIPW)
- Inverse Probability of Treatment Weighting (IPTW with stabilized weights)
- G-computation (Outcome Regression)
- Naive unadjusted observational baseline
- Covariate balance diagnostics (Standardized Mean Differences, SMD)
- Sensitivity analysis for unmeasured confounding (VanderWeele & Ding E-values)
- Synthetic ground-truth validation cohort generator
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass
class CausalCohort:
    patient_ids: List[str]
    covariate_matrix: np.ndarray  # Shape: (N, P)
    covariate_names: List[str]
    treatment: np.ndarray  # Shape: (N,) binary 0 = timely (<=56d), 1 = delayed (>56d)
    outcome: np.ndarray  # Shape: (N,) binary 0 = no recurrence, 1 = 5-year recurrence
    delays_days: np.ndarray  # Shape: (N,) continuous delay days
    true_rr: Optional[float] = None
    unmeasured_u: Optional[np.ndarray] = None


def compute_e_value(rr: float, rr_ci_lower: Optional[float] = None) -> Dict[str, float]:
    """Computes VanderWeele & Ding (2017) E-value for Risk Ratio point estimate and 95% CI bound."""
    if math.isnan(rr) or rr <= 0.0:
        return {"e_value_estimate": 1.0, "e_value_ci_lower": 1.0}

    # If RR < 1.0, invert to RR* = 1 / RR
    eff_rr = rr if rr >= 1.0 else (1.0 / rr)
    e_val_est = eff_rr + math.sqrt(eff_rr * (eff_rr - 1.0))

    e_val_ci = 1.0
    if rr_ci_lower is not None and not math.isnan(rr_ci_lower) and rr_ci_lower > 0.0:
        if rr >= 1.0:
            if rr_ci_lower > 1.0:
                e_val_ci = rr_ci_lower + math.sqrt(rr_ci_lower * (rr_ci_lower - 1.0))
            else:
                e_val_ci = 1.0
        else:
            # Protective effect
            if rr_ci_lower < 1.0:
                inv_ci = 1.0 / rr_ci_lower
                e_val_ci = inv_ci + math.sqrt(inv_ci * (inv_ci - 1.0))
            else:
                e_val_ci = 1.0

    return {
        "e_value_estimate": round(float(e_val_est), 4),
        "e_value_ci_lower": round(float(e_val_ci), 4),
    }


def compute_smd(x: np.ndarray, a: np.ndarray, weights: Optional[np.ndarray] = None) -> float:
    """Computes absolute Standardized Mean Difference (SMD) for a single covariate."""
    if weights is None:
        x1 = x[a == 1]
        x0 = x[a == 0]
        if len(x1) == 0 or len(x0) == 0:
            return 0.0
        mean1 = float(np.mean(x1))
        mean0 = float(np.mean(x0))
        var1 = float(np.var(x1, ddof=1)) if len(x1) > 1 else 0.0
        var0 = float(np.var(x0, ddof=1)) if len(x0) > 1 else 0.0
    else:
        w1 = weights[a == 1]
        w0 = weights[a == 0]
        x1 = x[a == 1]
        x0 = x[a == 0]
        if np.sum(w1) == 0 or np.sum(w0) == 0:
            return 0.0
        mean1 = float(np.average(x1, weights=w1))
        mean0 = float(np.average(x0, weights=w0))
        var1 = float(np.average((x1 - mean1) ** 2, weights=w1))
        var0 = float(np.average((x0 - mean0) ** 2, weights=w0))

    pooled_sd = math.sqrt(max(1e-8, (var1 + var0) / 2.0))
    return round(float(abs(mean1 - mean0) / pooled_sd), 4)


class TargetTrialEmulation:
    """Causal inference engine implementing IPTW, AIPW, and E-value sensitivity."""

    def __init__(self, clip_propensity: Tuple[float, float] = (0.02, 0.98)):
        self.clip_propensity = clip_propensity

    def estimate_effects(self, cohort: CausalCohort) -> Dict[str, Any]:
        """Calculates point estimates for Naive, IPTW, AIPW, and G-computation."""
        X = cohort.covariate_matrix
        A = cohort.treatment
        Y = cohort.outcome
        n = len(A)

        # 1. Naive Observational Estimator
        y1_raw = float(np.mean(Y[A == 1])) if np.sum(A == 1) > 0 else 0.0
        y0_raw = float(np.mean(Y[A == 0])) if np.sum(A == 0) > 0 else 0.0
        rr_naive = (y1_raw / y0_raw) if y0_raw > 0 else 1.0
        risk_diff_naive = y1_raw - y0_raw

        # 2. Propensity Score Estimation
        ps_model = LogisticRegression(max_iter=1000, C=1.0)
        ps_model.fit(X, A)
        e_hat = ps_model.predict_proba(X)[:, 1]
        e_hat = np.clip(e_hat, self.clip_propensity[0], self.clip_propensity[1])

        # Stabilized weights
        p_a1 = float(np.mean(A))
        p_a0 = 1.0 - p_a1
        weights = np.where(A == 1, p_a1 / e_hat, p_a0 / (1.0 - e_hat))
        # 99th percentile truncation
        w_p99 = float(np.percentile(weights, 99))
        weights = np.clip(weights, None, w_p99)

        # 3. Covariate Balance (SMD before and after IPTW)
        smd_unweighted = {}
        smd_weighted = {}
        for idx, name in enumerate(cohort.covariate_names):
            smd_unweighted[name] = compute_smd(X[:, idx], A, weights=None)
            smd_weighted[name] = compute_smd(X[:, idx], A, weights=weights)

        # 4. IPTW Risk Ratio
        y1_weighted = float(np.average(Y[A == 1], weights=weights[A == 1]))
        y0_weighted = float(np.average(Y[A == 0], weights=weights[A == 0]))
        rr_iptw = (y1_weighted / y0_weighted) if y0_weighted > 0 else 1.0
        risk_diff_iptw = y1_weighted - y0_weighted

        # 5. Outcome Regression (G-computation)
        out_model_1 = LogisticRegression(max_iter=1000, C=1.0)
        out_model_0 = LogisticRegression(max_iter=1000, C=1.0)
        out_model_1.fit(X[A == 1], Y[A == 1])
        out_model_0.fit(X[A == 0], Y[A == 0])

        mu1_hat = out_model_1.predict_proba(X)[:, 1]
        mu0_hat = out_model_0.predict_proba(X)[:, 1]

        y1_gcomp = float(np.mean(mu1_hat))
        y0_gcomp = float(np.mean(mu0_hat))
        rr_gcomp = (y1_gcomp / y0_gcomp) if y0_gcomp > 0 else 1.0
        risk_diff_gcomp = y1_gcomp - y0_gcomp

        # 6. Doubly-Robust AIPW
        # Efficient influence function components
        gamma1 = (A * Y) / e_hat - ((A - e_hat) / e_hat) * mu1_hat
        gamma0 = ((1.0 - A) * Y) / (1.0 - e_hat) + ((A - e_hat) / (1.0 - e_hat)) * mu0_hat

        mu1_aipw = float(np.mean(gamma1))
        mu0_aipw = float(np.mean(gamma0))
        rr_aipw = (mu1_aipw / mu0_aipw) if mu0_aipw > 0 else 1.0
        risk_diff_aipw = mu1_aipw - mu0_aipw

        return {
            "n_patients": n,
            "timely_count": int(np.sum(A == 0)),
            "delayed_count": int(np.sum(A == 1)),
            "estimates": {
                "naive": {"rr": round(rr_naive, 4), "risk_difference": round(risk_diff_naive, 4)},
                "iptw": {"rr": round(rr_iptw, 4), "risk_difference": round(risk_diff_iptw, 4)},
                "gcomp": {"rr": round(rr_gcomp, 4), "risk_difference": round(risk_diff_gcomp, 4)},
                "aipw": {"rr": round(rr_aipw, 4), "risk_difference": round(risk_diff_aipw, 4)},
            },
            "weights_diagnostics": {
                "mean": round(float(np.mean(weights)), 3),
                "min": round(float(np.min(weights)), 3),
                "max": round(float(np.max(weights)), 3),
                "p99": round(w_p99, 3),
            },
            "covariate_balance": {
                "unweighted_smd": smd_unweighted,
                "weighted_smd": smd_weighted,
                "max_weighted_smd": round(max(smd_weighted.values()), 4) if smd_weighted else 0.0,
            },
        }

    def bootstrap_inference(
        self, cohort: CausalCohort, n_boot: int = 1000, alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Performs percentile bootstrap over patient records for robust confidence intervals."""
        n = len(cohort.treatment)
        boot_rr_naive = np.empty(n_boot)
        boot_rr_iptw = np.empty(n_boot)
        boot_rr_aipw = np.empty(n_boot)
        boot_rr_gcomp = np.empty(n_boot)

        boot_rng = np.random.default_rng(20261017)
        for b in range(n_boot):
            idx = boot_rng.choice(n, size=n, replace=True)
            b_cohort = CausalCohort(
                patient_ids=[cohort.patient_ids[i] for i in idx],
                covariate_matrix=cohort.covariate_matrix[idx],
                covariate_names=cohort.covariate_names,
                treatment=cohort.treatment[idx],
                outcome=cohort.outcome[idx],
                delays_days=cohort.delays_days[idx],
                true_rr=cohort.true_rr,
            )
            res = self.estimate_effects(b_cohort)
            boot_rr_naive[b] = res["estimates"]["naive"]["rr"]
            boot_rr_iptw[b] = res["estimates"]["iptw"]["rr"]
            boot_rr_aipw[b] = res["estimates"]["aipw"]["rr"]
            boot_rr_gcomp[b] = res["estimates"]["gcomp"]["rr"]

        def _ci(arr: np.ndarray) -> Tuple[float, float, float]:
            m = float(np.nanmean(arr))
            low = float(np.nanpercentile(arr, 100 * (alpha / 2)))
            high = float(np.nanpercentile(arr, 100 * (1 - alpha / 2)))
            return round(m, 4), round(low, 4), round(high, 4)

        ci_naive = _ci(boot_rr_naive)
        ci_iptw = _ci(boot_rr_iptw)
        ci_aipw = _ci(boot_rr_aipw)
        ci_gcomp = _ci(boot_rr_gcomp)

        # Sensitivity Analysis (E-values) based on AIPW point estimate and CI lower bound
        e_vals = compute_e_value(ci_aipw[0], ci_aipw[1])

        return {
            "bootstrap_replications": n_boot,
            "confidence_intervals": {
                "naive": {"mean": ci_naive[0], "ci_95": [ci_naive[1], ci_naive[2]]},
                "iptw": {"mean": ci_iptw[0], "ci_95": [ci_iptw[1], ci_iptw[2]]},
                "gcomp": {"mean": ci_gcomp[0], "ci_95": [ci_gcomp[1], ci_gcomp[2]]},
                "aipw": {"mean": ci_aipw[0], "ci_95": [ci_aipw[1], ci_aipw[2]]},
            },
            "sensitivity_e_values": e_vals,
        }


def generate_synthetic_causal_cohort(
    n_patients: int = 5000,
    seed: int = 20261017,
    true_causal_rr: float = 1.15,
    inject_unmeasured_confounder: bool = False,
) -> CausalCohort:
    """Generates synthetic observational cohort with known ground-truth delay effect and confounding."""
    rng = np.random.default_rng(seed)

    # 1. Baseline Covariates
    # Subtype: 0=Lumpectomy, 1=PMRT, 2=TNBC
    subtype = rng.choice([0, 1, 2], size=n_patients, p=[0.35, 0.40, 0.25])
    age = np.clip(rng.normal(52.0, 10.0, size=n_patients), 25.0, 80.0)
    # Stage: 1=Stage I, 2=Stage II, 3=Stage III
    stage = rng.choice([1, 2, 3], size=n_patients, p=[0.30, 0.45, 0.25])
    # Travel distance in km
    distance_km = rng.exponential(35.0, size=n_patients) + 5.0
    # Exposure to machine breakdowns (operational delay factor)
    breakdown_exposure = rng.poisson(0.4, size=n_patients)

    # Injected unmeasured confounder U (e.g. unobserved genomic aggressiveness & frail socio-economic status)
    u_unmeasured = (
        rng.binomial(1, 0.30, size=n_patients)
        if inject_unmeasured_confounder
        else np.zeros(n_patients)
    )

    # 2. Confounded Treatment Assignment Mechanism
    # Delayed RT (> 56 days) is more common in PMRT/TNBC, high distance, high breakdown exposure
    # Under unmeasured confounding, U also substantially delays treatment
    logits_a = (
        -1.2
        + 0.5 * (subtype == 1)
        + 0.7 * (subtype == 2)
        + 0.015 * (distance_km - 40.0)
        + 0.4 * breakdown_exposure
        + 0.02 * (age - 50.0)
        + (1.2 * u_unmeasured if inject_unmeasured_confounder else 0.0)
    )
    p_delayed = 1.0 / (1.0 + np.exp(-logits_a))
    treatment = rng.binomial(1, p_delayed)

    # Continuous delay distribution
    delays = np.where(
        treatment == 1,
        rng.normal(85.0, 15.0, size=n_patients),  # delayed: ~85 days
        rng.normal(40.0, 8.0, size=n_patients),  # timely: ~40 days
    )
    delays = np.clip(delays, 14.0, 180.0)

    # Compute exact marginal potential outcome risk ratio
    beta_delay = math.log(true_causal_rr)
    logits_y_0 = (
        -2.5
        + 0.4 * (subtype == 1)
        + 0.9 * (subtype == 2)
        + 0.35 * (stage - 1)
        + 0.01 * (age - 50.0)
        + (1.1 * u_unmeasured if inject_unmeasured_confounder else 0.0)
    )
    logits_y_1 = logits_y_0 + beta_delay

    p_recurrence_1 = 1.0 / (1.0 + np.exp(-logits_y_1))
    p_recurrence_0 = 1.0 / (1.0 + np.exp(-logits_y_0))
    exact_marginal_rr = float(np.mean(p_recurrence_1) / np.mean(p_recurrence_0))

    p_recurrence = np.where(treatment == 1, p_recurrence_1, p_recurrence_0)
    outcome = rng.binomial(1, p_recurrence)

    # Pack covariate matrix (excluding unmeasured U from measured set)
    cov_names = [
        "subtype_pmrt",
        "subtype_tnbc",
        "age",
        "stage",
        "travel_distance_km",
        "breakdown_exposure",
    ]
    cov_matrix = np.column_stack(
        [
            (subtype == 1).astype(float),
            (subtype == 2).astype(float),
            age,
            stage.astype(float),
            distance_km,
            breakdown_exposure.astype(float),
        ]
    )

    return CausalCohort(
        patient_ids=[f"PAT-K7-{i:05d}" for i in range(n_patients)],
        covariate_matrix=cov_matrix,
        covariate_names=cov_names,
        treatment=treatment,
        outcome=outcome,
        delays_days=delays,
        true_rr=round(exact_marginal_rr, 4),
        unmeasured_u=u_unmeasured if inject_unmeasured_confounder else None,
    )
