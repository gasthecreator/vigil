#!/usr/bin/env python3
"""Render EXP-010 Markdown from its immutable saved results in preregistered metric order."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
METRICS = (
    "empirical_sensitivity",
    "empirical_specificity",
    "apparent_prevalence",
    "brier_score",
    "roc_auc",
)
CONDITIONS = ("MCAR", "MAR", "MNAR")
ESTIMATORS = ("complete_case", "development_fit_ipw")


def render(result: dict[str, Any]) -> str:
    lines = [
        "# EXP-CORE-ML-010: Development-fit verification propensity validation",
        "",
        "Synthetic method-validation only; no clinical or partner-data inference.",
        f"Source commit: `{result['source_commit']}`",
        "",
        "| Condition | Estimator | Metric | Mean error | Error SD | 95% error percentiles |",
        "|---|---|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        for estimator in ESTIMATORS:
            for metric in METRICS:
                item = result["summary"][condition][estimator][metric]
                low, high = item["error_percentiles_2_5_97_5"]
                lines.append(
                    f"| {condition} | {estimator} | {metric} | {item['mean_error']:.6f} "
                    f"| {item['error_sd']:.6f} | [{low:.6f}, {high:.6f}] |"
                )
    lines.extend(
        [
            "",
            "All replicate-level truth, estimates, errors and diagnostics are preserved in `results.json`. MCAR/MAR are the specified synthetic identification designs; MNAR is a negative control. Results do not validate exchangeability, positivity or mechanism stability in real cohorts.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    result = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    print(render(result), end="")


if __name__ == "__main__":
    main()
