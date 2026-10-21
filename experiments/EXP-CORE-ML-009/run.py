#!/usr/bin/env python3
"""One-time MCAR/MAR/MNAR validation of the registered verification estimators."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
from scipy.special import expit  # type: ignore[import-untyped]
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "vigil-eval"))

from vigil_eval.verification_bias import (  # noqa: E402
    evaluate_complete_case,
    evaluate_ipw_verification,
)

EXP = Path(__file__).resolve().parent
N = 2_500
REPLICATES = range(100)
CUTOFF = 0.5
SEED_BASE = 20_261_021
CONDITION_OFFSETS = {"MCAR": 0, "MAR": 100_000, "MNAR": 200_000}
METRICS = (
    "empirical_sensitivity",
    "empirical_specificity",
    "apparent_prevalence",
    "brier_score",
    "roc_auc",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_for(condition: str, replicate: int) -> int:
    return SEED_BASE + CONDITION_OFFSETS[condition] + replicate


def generate_replicate(condition: str, seed: int, n: int = N) -> dict[str, np.ndarray]:
    """Generate exactly one registered cohort, including truth for reference metrics."""
    if condition not in CONDITION_OFFSETS:
        raise ValueError(f"Unknown verification condition: {condition}")
    if n < 2:
        raise ValueError("n must be at least two")
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, 1.0, n)
    risk = expit(-1.0 + 1.2 * x)
    y = rng.binomial(1, risk).astype(int)
    if condition == "MCAR":
        p_verify = np.full(n, 0.60, dtype=float)
    elif condition == "MAR":
        p_verify = expit(-0.5 + x)
    else:
        p_verify = expit(-0.5 + x + (2.0 * y - 1.0))
    verified = rng.binomial(1, p_verify).astype(bool)
    observed_y = np.full(n, np.nan, dtype=float)
    observed_y[verified] = y[verified]
    return {
        "x": x,
        "risk": risk,
        "truth": y,
        "p_verify": p_verify,
        "verified": verified,
        "observed_y": observed_y,
    }


def full_cohort_metrics(risk: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    predicted = risk >= CUTOFF
    positive = truth == 1
    negative = ~positive
    return {
        "empirical_sensitivity": float(np.mean(predicted[positive])) if positive.any() else float("nan"),
        "empirical_specificity": float(np.mean(~predicted[negative])) if negative.any() else float("nan"),
        "apparent_prevalence": float(np.mean(truth)),
        "brier_score": float(np.mean((risk - truth) ** 2)),
        "roc_auc": float(roc_auc_score(truth, risk)) if np.unique(truth).size == 2 else float("nan"),
    }


def evaluate_replicate(condition: str, replicate: int) -> dict[str, Any]:
    seed = seed_for(condition, replicate)
    data = generate_replicate(condition, seed)
    truth_metrics = full_cohort_metrics(data["risk"], data["truth"])
    complete_case = evaluate_complete_case(
        data["risk"], data["observed_y"], data["verified"], CUTOFF
    )
    ipw = evaluate_ipw_verification(
        data["risk"],
        data["observed_y"],
        data["verified"],
        data["x"].reshape(-1, 1),
        CUTOFF,
    )
    if not ipw.details.get("metrics_defined", False):
        raise RuntimeError(f"Registered IPW estimator undefined for {condition} replicate {replicate}")
    estimates = {
        "complete_case": {metric: float(getattr(complete_case, metric)) for metric in METRICS},
        "ipw": {metric: float(getattr(ipw, metric)) for metric in METRICS},
    }
    errors = {
        estimator: {
            metric: estimates[estimator][metric] - truth_metrics[metric]
            for metric in METRICS
        }
        for estimator in estimates
    }
    return {
        "condition": condition,
        "replicate": replicate,
        "seed": seed,
        "n": N,
        "n_verified": int(data["verified"].sum()),
        "truth": truth_metrics,
        "estimates": estimates,
        "errors": errors,
        "ipw_diagnostics": {
            "maximum_inverse_weight": ipw.details["maximum_verified_inverse_weight"],
            "effective_sample_size": ipw.details["effective_sample_size"],
            "minimum_verified_propensity": ipw.details["minimum_verified_propensity"],
        },
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for condition in CONDITION_OFFSETS:
        summary[condition] = {}
        selected = [row for row in rows if row["condition"] == condition]
        for estimator in ("complete_case", "ipw"):
            summary[condition][estimator] = {}
            for metric in METRICS:
                errors = np.asarray(
                    [row["errors"][estimator][metric] for row in selected], dtype=float
                )
                estimates = np.asarray(
                    [row["estimates"][estimator][metric] for row in selected], dtype=float
                )
                summary[condition][estimator][metric] = {
                    "mean_estimate": float(np.mean(estimates)),
                    "mean_error": float(np.mean(errors)),
                    "error_sd": float(np.std(errors, ddof=1)),
                    "error_percentiles_2_5_97_5": [
                        float(np.quantile(errors, 0.025)),
                        float(np.quantile(errors, 0.975)),
                    ],
                    "n_defined": int(np.isfinite(errors).sum()),
                    "n_total": int(len(errors)),
                }
    return summary


def render_report(results: dict[str, Any]) -> str:
    lines = [
        "# EXP-CORE-ML-009: Verification-bias estimator validation",
        "",
        "Synthetic method-validation results only; no clinical or real-cohort claim.",
        "",
        f"Source commit: `{results['source_commit']}`",
        f"Cohort design: {results['design']['replicates']} replicates × {results['design']['n']} per condition.",
        "",
        "Mean estimate-minus-full-cohort error (with replicate SD), by verification mechanism:",
        "",
        "| Mechanism | Estimator | Metric | Mean error | Replicate SD | 95% error percentiles |",
        "|---|---|---|---:|---:|---:|",
    ]
    for condition in CONDITION_OFFSETS:
        for estimator in ("complete_case", "ipw"):
            for metric in METRICS:
                item = results["summary"][condition][estimator][metric]
                low, high = item["error_percentiles_2_5_97_5"]
                lines.append(
                    f"| {condition} | {estimator} | {metric} | {item['mean_error']:.6f} "
                    f"| {item['error_sd']:.6f} | [{low:.6f}, {high:.6f}] |"
                )
    lines.extend(
        [
            "",
            "All replicate records, full-cohort references, estimates, weights, and diagnostics are in `results.json`.",
            "MCAR/MAR estimates are conditional on the registered one-covariate logistic design. MNAR intentionally omits the outcome from the propensity model; its bias is an identification-boundary result.",
            "",
        ]
    )
    return "\n".join(lines)


def require_clean_committed_tree() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    if status:
        raise RuntimeError("Refusing EXP-CORE-ML-009 from a dirty working tree")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    access_path = EXP / "ACCESS_LOG.json"
    results_path = EXP / "results.json"
    report_path = EXP / "REPORT.md"
    if any(path.exists() for path in (access_path, results_path, report_path)):
        raise RuntimeError("EXP-CORE-ML-009 is one-time; an access or result artifact already exists")
    source_commit = require_clean_committed_tree()
    access: dict[str, Any] = {
        "experiment_id": "EXP-CORE-ML-009",
        "protocol_version": "1.0",
        "source_commit": source_commit,
        "preregistration_sha256": sha256(EXP / "PREREG.md"),
        "runner_sha256": sha256(Path(__file__)),
        "estimator_source_sha256": sha256(
            ROOT / "packages/vigil-eval/vigil_eval/verification_bias.py"
        ),
        "environment_lock_sha256": sha256(ROOT / "uv.lock"),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scikit_learn_version": sklearn.__version__,
        "started_utc_epoch": time.time(),
        "completed": False,
        "design": {"n": N, "replicates": len(REPLICATES), "conditions": CONDITION_OFFSETS},
        "seed_formula": "20261021 + condition_offset + replicate; offsets MCAR=0, MAR=100000, MNAR=200000",
    }
    write_json(access_path, access)
    try:
        rows = [
            evaluate_replicate(condition, replicate)
            for condition in CONDITION_OFFSETS
            for replicate in REPLICATES
        ]
        results: dict[str, Any] = {
            "experiment_id": "EXP-CORE-ML-009",
            "source_commit": source_commit,
            "design": access["design"],
            "conditions": {
                "MCAR": "constant verification probability 0.60",
                "MAR": "logistic(-0.5 + X)",
                "MNAR": "logistic(-0.5 + X + (2Y - 1)); outcome omitted from propensity features",
            },
            "metric_names": list(METRICS),
            "summary": aggregate(rows),
            "replicates": rows,
        }
        write_json(results_path, results)
        report_path.write_text(render_report(results), encoding="utf-8")
        access.update(
            {
                "completed": True,
                "completed_utc_epoch": time.time(),
                "results_sha256": sha256(results_path),
                "report_sha256": sha256(report_path),
            }
        )
    except Exception as exc:
        access.update(
            {
                "completed": False,
                "failed_utc_epoch": time.time(),
                "failure": f"{type(exc).__name__}: {exc}",
            }
        )
        raise
    finally:
        write_json(access_path, access)


if __name__ == "__main__":
    main()
