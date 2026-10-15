"""
vigil_eval.regression_gate

Automated Model Evaluation Regression Gate and Benchmark Report Renderer.
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.1) and docs/ML_PROGRAM.md §9.

Prevents performance regressions and ensures that every model's metrics are checked
against pre-registered baseline thresholds prior to merging or phase advancement.
"""

from __future__ import annotations

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

        cand_auc = candidate_metrics.get("roc_auc", 0.0)
        cand_brier = candidate_metrics.get("brier_score", 1.0)
        cand_ece = candidate_metrics.get("ece", 1.0)

        # 1. Absolute quality thresholds
        if cand_auc < self.min_auc:
            failures.append(
                f"Candidate ROC-AUC {cand_auc:.4f} is below minimum acceptable threshold {self.min_auc:.4f}"
            )
        if cand_brier > self.max_brier:
            failures.append(
                f"Candidate Brier score {cand_brier:.4f} exceeds maximum threshold {self.max_brier:.4f}"
            )
        if cand_ece > self.max_ece:
            failures.append(
                f"Candidate ECE {cand_ece:.4f} exceeds maximum calibration threshold {self.max_ece:.4f}"
            )

        # 2. Check for suspicious near-perfect scores (Defect A2 / Stop-and-think trigger 1)
        if cand_auc > 0.97:
            failures.append(
                f"STOP-AND-THINK TRIGGER: Candidate ROC-AUC {cand_auc:.4f} > 0.97 indicates probable data leakage"
            )

        # 3. Relative non-regression against baseline
        if baseline_metrics is not None:
            base_auc = baseline_metrics.get("roc_auc", 0.5)
            base_brier = baseline_metrics.get("brier_score", 0.20)

            if cand_auc < (base_auc - self.max_auc_drop):
                failures.append(
                    f"Candidate ROC-AUC {cand_auc:.4f} dropped by > {self.max_auc_drop:.4f} below baseline {base_auc:.4f}"
                )
            if cand_brier > (base_brier + self.max_brier_increase):
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
        auc = r.get("auc_ci", f"{r.get('roc_auc', 0.0):.4f}")
        brier = f"{r.get('brier_score', 0.0):.4f}"
        ece = f"{r.get('ece', 0.0):.4f}"
        nb = f"{r.get('net_benefit_at_015', 0.0):.4f}"
        lead = r.get("lead_time", "-")

        lines.append(f"| **{m_id}** | {arch} | {auc} | {brier} | {ece} | {nb} | {lead} |")

    lines.append("")
    return "\n".join(lines)
