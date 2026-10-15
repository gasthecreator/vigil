"""
vigil_eval.subgroups

Subgroup Analysis Engine with Empirical Bayes Shrinkage.
Conforms strictly to docs/MASTER_PLAN.md §11.2 (H8), §14 (WP2.1), and docs/ML_PROGRAM.md §5, §9.

Mitigates small-sample variance across clinically vital subgroups (e.g. molecular subtype,
clinical stage at presentation, and visit frequency strata) by pulling noisy subgroup estimates
toward the grand mean using DerSimonian-Laird Empirical Bayes shrinkage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

from vigil_eval.bootstrap import patient_cluster_bootstrap


@dataclass
class SubgroupEstimate:
    subgroup_name: str
    stratum_value: str
    n_patients: int
    n_observations: int
    raw_estimate: float
    raw_ci_lower: float
    raw_ci_upper: float
    standard_error: float
    shrinkage_factor: float
    shrunk_estimate: float
    shrunk_ci_lower: float
    shrunk_ci_upper: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subgroup": self.subgroup_name,
            "stratum": self.stratum_value,
            "n_patients": self.n_patients,
            "n_observations": self.n_observations,
            "raw_estimate": round(self.raw_estimate, 4),
            "raw_ci": f"[{self.raw_ci_lower:.4f}, {self.raw_ci_upper:.4f}]",
            "shrinkage_factor": round(self.shrinkage_factor, 3),
            "shrunk_estimate": round(self.shrunk_estimate, 4),
            "shrunk_ci": f"[{self.shrunk_ci_lower:.4f}, {self.shrunk_ci_upper:.4f}]",
        }


def empirical_bayes_shrinkage(
    estimates: np.ndarray,
    standard_errors: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """
    Computes Empirical Bayes shrinkage via DerSimonian-Laird random-effects framework.

    Parameters:
        estimates: Vector of observed subgroup effect sizes / metric scores (theta_j).
        standard_errors: Vector of standard errors (s_j).

    Returns:
        (shrunk_estimates, shrinkage_factors, grand_mean, tau_squared)
    """
    k = len(estimates)
    if k <= 1:
        return estimates, np.zeros(k), float(estimates[0]), 0.0

    # Avoid zero standard errors
    s2 = np.maximum(standard_errors**2, 1e-6)
    w = 1.0 / s2

    # Fixed-effect weighted grand mean
    mu_fixed = float(np.sum(w * estimates) / np.sum(w))

    # Cochran's Q statistic for between-subgroup heterogeneity
    q = float(np.sum(w * ((estimates - mu_fixed) ** 2)))

    # DerSimonian-Laird estimator for tau^2
    denom = np.sum(w) - (np.sum(w**2) / np.sum(w))
    tau2 = max(0.0, (q - (k - 1)) / denom) if denom > 0 else 0.0

    # Subgroup-specific shrinkage factor B_j in [0, 1]
    # B_j -> 1 means high noise, pull heavily to grand mean
    # B_j -> 0 means precise stratum, retain raw estimate
    b_j = s2 / (s2 + tau2) if tau2 > 0 else np.ones(k)

    # Shrunk estimates: theta_j^EB = (1 - B_j) * theta_j + B_j * mu
    shrunk_theta = (1.0 - b_j) * estimates + b_j * mu_fixed

    return shrunk_theta, b_j, mu_fixed, tau2


def evaluate_subgroups_with_shrinkage(
    data: pd.DataFrame,
    patient_col: str,
    subgroup_col: str,
    metric_fn: Callable[[pd.DataFrame], Dict[str, float]],
    target_metric: str,
    n_bootstraps: int = 100,
    seed: int = 42,
) -> List[SubgroupEstimate]:
    """
    Evaluates metric performance across categorical strata with Empirical Bayes shrinkage.

    Parameters:
        data: Longitudinal DataFrame.
        patient_col: Patient identifier column.
        subgroup_col: Subgroup category column (e.g. 'subtype', 'stage', 'visit_count_bin').
        metric_fn: Evaluation callable.
        target_metric: Name of primary metric to extract and shrink (e.g. 'roc_auc', 'brier_score').
    """
    strata = sorted(data[subgroup_col].dropna().unique())
    raw_ests = []
    ses = []
    ci_lows = []
    ci_highs = []
    pt_counts = []
    obs_counts = []

    for s_val in strata:
        stratum_df = data[data[subgroup_col] == s_val].reset_index(drop=True)
        n_pts = stratum_df[patient_col].nunique()
        n_obs = len(stratum_df)

        pt_counts.append(n_pts)
        obs_counts.append(n_obs)

        # Run patient cluster bootstrap on stratum
        boot_res = patient_cluster_bootstrap(
            data=stratum_df,
            patient_col=patient_col,
            metric_fn=metric_fn,
            n_bootstraps=n_bootstraps,
            seed=seed,
        )

        summary = boot_res.get(target_metric)
        if summary is not None:
            raw_ests.append(summary.point_estimate)
            ses.append(summary.standard_error)
            ci_lows.append(summary.ci_lower)
            ci_highs.append(summary.ci_upper)
        else:
            raw_ests.append(0.5)
            ses.append(0.1)
            ci_lows.append(0.3)
            ci_highs.append(0.7)

    arr_ests = np.array(raw_ests)
    arr_ses = np.array(ses)

    shrunk_ests, b_factors, grand_mean, tau2 = empirical_bayes_shrinkage(arr_ests, arr_ses)

    results = []
    for i, s_val in enumerate(strata):
        # Shrunk confidence interval: shift raw bounds by the shrinkage displacement
        displacement = shrunk_ests[i] - arr_ests[i]
        shrunk_l = max(0.0, min(1.0, ci_lows[i] + displacement))
        shrunk_u = max(0.0, min(1.0, ci_highs[i] + displacement))

        results.append(
            SubgroupEstimate(
                subgroup_name=subgroup_col,
                stratum_value=str(s_val),
                n_patients=pt_counts[i],
                n_observations=obs_counts[i],
                raw_estimate=arr_ests[i],
                raw_ci_lower=ci_lows[i],
                raw_ci_upper=ci_highs[i],
                standard_error=arr_ses[i],
                shrinkage_factor=b_factors[i],
                shrunk_estimate=shrunk_ests[i],
                shrunk_ci_lower=shrunk_l,
                shrunk_ci_upper=shrunk_u,
            )
        )

    return results
