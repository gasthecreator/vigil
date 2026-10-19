"""
vigil_eval.bootstrap

Clustered Patient-Level Bootstrap Resampling Engine.
Conforms strictly to docs/MASTER_PLAN.md §11, §14 (WP2.1), and docs/ML_PROGRAM.md §5.

RULE: Never resample observations independently across patients; resampling MUST always be performed
at the patient cluster level to preserve intra-individual longitudinal correlation structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd


@dataclass
class BootstrapMetricSummary:
    metric_name: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    standard_error: float
    valid_replicates: int
    confidence_level: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric_name,
            "point_estimate": self.point_estimate,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "standard_error": self.standard_error,
            "valid_replicates": self.valid_replicates,
            "confidence_interval": f"[{self.ci_lower:.4f}, {self.ci_upper:.4f}]",
        }


def patient_cluster_bootstrap(
    data: pd.DataFrame,
    patient_col: str,
    metric_fn: Callable[[pd.DataFrame], Dict[str, float]],
    n_bootstraps: int = 200,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Dict[str, BootstrapMetricSummary]:
    """
    Performs patient-level cluster bootstrap resampling.

    Parameters:
        data: DataFrame containing patient longitudinal records.
        patient_col: Name of column containing unique patient identifier.
        metric_fn: Function that accepts a DataFrame and returns a dictionary of named metric values.
        n_bootstraps: Number of bootstrap resamples (default: 200 for smoke/eval, 500+ for final reports).
        ci_level: Confidence level (default: 0.95).
        seed: Random seed for reproducibility.

    Returns:
        Dictionary mapping metric names to BootstrapMetricSummary objects.
    """
    rng = np.random.default_rng(seed)
    unique_patients = np.array(data[patient_col].unique())
    n_patients = len(unique_patients)

    # 1. Point estimate on full original data
    point_estimates = metric_fn(data)

    # 2. Pre-index dataframe by patient for high-speed bootstrap drawing
    grouped = {pt_id: group for pt_id, group in data.groupby(patient_col)}

    boot_samples: Dict[str, List[float]] = {m: [] for m in point_estimates}

    alpha = 1.0 - ci_level
    lower_pct = (alpha / 2.0) * 100.0
    upper_pct = (1.0 - (alpha / 2.0)) * 100.0

    for _ in range(n_bootstraps):
        sampled_pt_ids = rng.choice(unique_patients, size=n_patients, replace=True)
        # Assemble bootstrapped dataframe
        resampled_dfs = [grouped[pt] for pt in sampled_pt_ids]
        resampled_data = pd.concat(resampled_dfs, ignore_index=True)

        try:
            sample_metrics = metric_fn(resampled_data)
            for m, val in sample_metrics.items():
                if np.isfinite(val):
                    boot_samples[m].append(val)
        except Exception:
            # Skip degenerate draws (e.g. all 0 labels)
            continue

    summaries = {}
    for m, pt_est in point_estimates.items():
        vals = np.array(boot_samples[m])
        if len(vals) > 5:
            ci_l = float(np.percentile(vals, lower_pct))
            ci_u = float(np.percentile(vals, upper_pct))
            se = float(np.std(vals, ddof=1))
        else:
            ci_l = float("nan")
            ci_u = float("nan")
            se = float("nan")

        summaries[m] = BootstrapMetricSummary(
            metric_name=m,
            point_estimate=float(pt_est),
            ci_lower=ci_l,
            ci_upper=ci_u,
            standard_error=se,
            valid_replicates=len(vals),
            confidence_level=ci_level,
        )

    return summaries
