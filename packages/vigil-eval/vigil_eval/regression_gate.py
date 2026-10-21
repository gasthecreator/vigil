"""
vigil_eval.regression_gate

Automated Model Evaluation Regression Gate and Benchmark Report Renderer.
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.1) and docs/ML_PROGRAM.md §9.

Prevents performance regressions and ensures that every model's metrics are checked
against pre-registered baseline thresholds prior to merging or phase advancement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class GateCheckResult:
    passed: bool
    failures: List[str]
    details: Dict[str, Any]


class ModelRegressionGate:
    """Evaluates whether candidate model metrics satisfy non-regression constraints."""

    def __init__(
        self,
        min_auc: float = 0.65,
        max_brier: float = 0.22,
        max_ece: float = 0.15,
        max_auc_drop_vs_baseline: float = 0.03,
        max_brier_increase_vs_baseline: float = 0.02,
    ):
        self.min_auc = min_auc
        self.max_brier = max_brier
        self.max_ece = max_ece
        self.max_auc_drop = max_auc_drop_vs_baseline
        self.max_brier_increase = max_brier_increase_vs_baseline

    def evaluate(
        self,
        candidate_metrics: Dict[str, float],
        baseline_metrics: Optional[Dict[str, float]] = None,
    ) -> GateCheckResult:
        failures = []

        def metric(metrics: Dict[str, float], name: str, role: str) -> float | None:
            value = metrics.get(name)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                failures.append(f"{role} {name} is missing or non-finite; comparison is undefined")
                return None
            if not 0.0 <= value <= 1.0:
                failures.append(f"{role} {name} is outside its [0, 1] metric range")
                return None
            return value

        cand_auc = metric(candidate_metrics, "roc_auc", "Candidate")
        cand_brier = metric(candidate_metrics, "brier_score", "Candidate")
        cand_ece = metric(candidate_metrics, "ece", "Candidate")

        # 1. Absolute quality thresholds
        if cand_auc is not None and cand_auc < self.min_auc:
            failures.append(
                f"Candidate ROC-AUC {cand_auc:.4f} is below minimum acceptable threshold {self.min_auc:.4f}"
            )
        if cand_brier is not None and cand_brier > self.max_brier:
            failures.append(
                f"Candidate Brier score {cand_brier:.4f} exceeds maximum threshold {self.max_brier:.4f}"
            )
        if cand_ece is not None and cand_ece > self.max_ece:
            failures.append(
                f"Candidate ECE {cand_ece:.4f} exceeds maximum calibration threshold {self.max_ece:.4f}"
            )

        # 2. Check for suspicious near-perfect scores (Defect A2 / Stop-and-think trigger 1)
        if cand_auc is not None and cand_auc > 0.97:
            failures.append(
                f"STOP-AND-THINK TRIGGER: Candidate ROC-AUC {cand_auc:.4f} > 0.97 indicates probable data leakage"
            )

        # 3. Relative non-regression against baseline
        if baseline_metrics is not None:
            base_auc = metric(baseline_metrics, "roc_auc", "Baseline")
            base_brier = metric(baseline_metrics, "brier_score", "Baseline")

            if cand_auc is not None and base_auc is not None and cand_auc < (base_auc - self.max_auc_drop):
                failures.append(
                    f"Candidate ROC-AUC {cand_auc:.4f} dropped by > {self.max_auc_drop:.4f} below baseline {base_auc:.4f}"
                )
            if (
                cand_brier is not None
                and base_brier is not None
                and cand_brier > (base_brier + self.max_brier_increase)
            ):
                failures.append(
                    f"Candidate Brier {cand_brier:.4f} increased by > {self.max_brier_increase:.4f} above baseline {base_brier:.4f}"
                )

        return GateCheckResult(
            passed=len(failures) == 0,
            failures=failures,
            details={
                "candidate": candidate_metrics,
                "baseline": baseline_metrics,
            },
        )


def render_benchmark_table_markdown(
    results: List[Dict[str, Any]],
    title: str = "Vigil Benchmark Leaderboard",
) -> str:
    """
    Renders structured GitHub Flavored Markdown leaderboard table from model evaluation results.
    """
    lines = [
        f"### {title}",
        "",
        "| Model ID | Architecture / Family | IPCW ROC-AUC (95% CI) | IPCW Brier Score | ECE | Net Benefit (pt=0.15) | Mean Lead Time |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in results:
        m_id = r.get("model_id", "Unknown")
        arch = r.get("architecture", "-")

        def format_metric(name: str) -> str:
            value = r.get(name)
            return f"{value:.4f}" if isinstance(value, (int, float)) and math.isfinite(value) else "N/A"

        auc = r.get("auc_ci") or format_metric("roc_auc")
        brier = format_metric("brier_score")
        ece = format_metric("ece")
        nb = format_metric("net_benefit_at_015")
        lead = r.get("lead_time", "-")

        lines.append(f"| **{m_id}** | {arch} | {auc} | {brier} | {ece} | {nb} | {lead} |")

    lines.append("")
    return "\n".join(lines)
