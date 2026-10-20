#!/usr/bin/env python3
"""One-time, source-bound execution of the registered K7 replacement."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments" / "EXP-S8-K7-002"
sys.path.insert(0, str(ROOT / "packages" / "vigil-ml"))

from vigil_ml.causal_k7_replacement import (  # noqa: E402
    NonEstimableError,
    bootstrap_inference,
    compute_e_value,
    estimate_effects,
    generate_cohort,
)

ACCESS_LOG = EXPERIMENT / "ACCESS_LOG.jsonl"
RESULTS = EXPERIMENT / "results.json"
REPORT = EXPERIMENT / "REPORT.md"
COMPLETION = EXPERIMENT / "RUN_COMPLETION.json"
PREREG = EXPERIMENT / "PREREG.md"
IMPLEMENTATION = ROOT / "packages" / "vigil-ml" / "vigil_ml" / "causal_k7_replacement.py"
RUNNER = Path(__file__).resolve()
VERIFIER = EXPERIMENT / "verify.py"
PROJECT_CONFIG = ROOT / "pyproject.toml"
DEPENDENCY_LOCK = ROOT / "uv.lock"
SEEDS = tuple(range(620261101, 620261121))
CONDITIONS = (("measured_confounding", False), ("unmeasured_confounding", True))
BOOTSTRAP_REPLICATES = 1000
RUNTIME_VERSIONS = {
    "python": platform.python_version(),
    "numpy": importlib.metadata.version("numpy"),
    "scikit_learn": importlib.metadata.version("scikit-learn"),
}
COVARIATE_NAMES = (
    "subtype_pmrt",
    "subtype_tnbc",
    "age_years",
    "stage",
    "travel_distance_km",
    "breakdown_count",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _atomic_write(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(data)
        temporary.flush()
        os.fsync(temporary.fileno())
        temp_path = Path(temporary.name)
    os.replace(temp_path, path)


def validate_access() -> dict[str, Any]:
    if COMPLETION.exists() or RESULTS.exists() or REPORT.exists():
        raise RuntimeError("EXP-S8-K7-002 is one-time; output already exists")
    if not ACCESS_LOG.is_file():
        raise RuntimeError("EXP-S8-K7-002 is not authorized: access log is missing")
    if _git("status", "--porcelain"):
        raise RuntimeError("working tree must be clean before the registered run")
    entries = [
        json.loads(line)
        for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matching = [entry for entry in entries if entry.get("experiment_id") == "EXP-S8-K7-002"]
    if len(matching) != 1:
        raise RuntimeError("access log must contain exactly one K7-002 authorization")
    entry: dict[str, Any] = matching[0]
    if entry.get("status") != "pre_run_record_committed":
        raise RuntimeError("K7-002 pre-run access record has an invalid status")
    source_hashes = {
        "preregistration_sha256": sha256(PREREG),
        "implementation_sha256": sha256(IMPLEMENTATION),
        "runner_sha256": sha256(RUNNER),
        "verifier_sha256": sha256(VERIFIER),
        "project_config_sha256": sha256(PROJECT_CONFIG),
        "dependency_lock_sha256": sha256(DEPENDENCY_LOCK),
    }
    for key, expected in source_hashes.items():
        if entry.get(key) != expected:
            raise RuntimeError(f"K7-002 access record does not match {key}")
    implementation_commit = entry.get("implementation_commit")
    if not isinstance(implementation_commit, str) or not implementation_commit:
        raise RuntimeError("access log does not bind the implementation commit")
    _git("merge-base", "--is-ancestor", implementation_commit, "HEAD")
    registration_commit = entry.get("registration_commit")
    if not isinstance(registration_commit, str) or not registration_commit:
        raise RuntimeError("access log does not bind the preregistration commit")
    _git("merge-base", "--is-ancestor", registration_commit, implementation_commit)
    if tuple(entry.get("evaluation_seeds", ())) != SEEDS:
        raise RuntimeError("access log seed allocation does not match the preregistration")
    return entry


def _safe_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_safe_json(item) for item in value]
    if hasattr(value, "item"):
        return _safe_json(value.item())
    return value


def _run_replicate(seed: int, condition: str, has_u: bool) -> dict[str, Any]:
    cohort = generate_cohort(seed=seed, unmeasured_confounding=has_u)
    point: dict[str, Any] = {
        "seed": seed,
        "condition": condition,
        "n_patients": len(cohort.patient_ids),
        "truth": cohort.true_effects,
    }
    try:
        estimates = estimate_effects(
            cohort.covariates,
            cohort.treatment,
            cohort.outcome,
            cohort.covariate_names,
            fold_seed=seed + 1_000_000,
        )
    except NonEstimableError as exc:
        point.update({"status": "non_estimable", "reason": str(exc)})
        return point

    bootstrap = bootstrap_inference(
        cohort.covariates,
        cohort.treatment,
        cohort.outcome,
        cohort.covariate_names,
        fold_seed=seed + 1_000_000,
        bootstrap_seed=seed + 2_000_000,
        n_bootstrap=BOOTSTRAP_REPLICATES,
    )
    aipw = estimates["estimates"]["aipw"]
    interval = bootstrap["confidence_intervals"]["aipw"]["ci_95"]
    e_values = (
        compute_e_value(aipw["risk_ratio"], tuple(interval))
        if aipw["risk_ratio"] is not None and interval is not None
        else None
    )
    point.update(
        {
            "status": "estimable",
            "estimates": estimates,
            "bootstrap": bootstrap,
            "aipw_e_values": e_values,
            "aipw_interval_covers_truth": (
                interval[0] <= cohort.true_effects["risk_ratio"] <= interval[1]
                if interval is not None
                else None
            ),
        }
    )
    return point


def _summarize(rows: list[dict[str, Any]], condition: str) -> dict[str, Any]:
    selected = [row for row in rows if row["condition"] == condition]
    estimable = [row for row in selected if row["status"] == "estimable"]
    truth = [row["truth"]["risk_ratio"] for row in selected]
    estimates = [row["estimates"]["aipw"]["risk_ratio"] for row in estimable]
    coverage = [row["aipw_interval_covers_truth"] for row in estimable]
    finite_estimates = [float(value) for value in estimates if value is not None]
    finite_truth = [float(row["truth"]["risk_ratio"]) for row in estimable]
    bias = (
        sum(finite_estimates) / len(finite_estimates) - sum(finite_truth) / len(finite_truth)
        if finite_estimates and len(finite_estimates) == len(finite_truth)
        else None
    )
    absolute_mean_error = abs(bias) if bias is not None else None
    covered = [value for value in coverage if value is not None]
    smd_values = [
        row["estimates"]["covariate_balance"]["maximum_weighted_smd"] for row in estimable
    ]
    defined_smd = [float(value) for value in smd_values if value is not None]
    return {
        "replicates": len(selected),
        "estimable_replicates": len(estimable),
        "truth_risk_ratio_mean": sum(truth) / len(truth) if truth else None,
        "aipw_risk_ratio_mean": sum(finite_estimates) / len(finite_estimates)
        if finite_estimates
        else None,
        "aipw_risk_ratio_sd": float(np.std(finite_estimates, ddof=1))
        if len(finite_estimates) > 1
        else None,
        "aipw_risk_ratio_median": float(np.median(finite_estimates)) if finite_estimates else None,
        "aipw_risk_ratio_min": min(finite_estimates) if finite_estimates else None,
        "aipw_risk_ratio_max": max(finite_estimates) if finite_estimates else None,
        "absolute_mean_point_estimate_error": absolute_mean_error,
        "mean_bias": bias,
        "cohort_interval_coverage_count": sum(bool(value) for value in covered),
        "cohort_interval_coverage_denominator": len(covered),
        "weighted_smd_below_0_10_count": sum(value < 0.10 for value in defined_smd),
        "weighted_smd_denominator": len(defined_smd),
    }


def _render_report(results: dict[str, Any]) -> str:
    a = results["summaries"]["measured_confounding"]
    b = results["summaries"]["unmeasured_confounding"]
    h1 = results["hypotheses"]["H1_recovery"]
    lines = [
        "# EXP-S8-K7-002: Cross-Fitted Causal Estimator Recovery",
        "",
        "**Evidence class:** synthetic only; this is not clinical validation or a treatment recommendation.",
        "",
        f"- Run timestamp: `{results['timestamp_utc']}`",
        f"- Implementation commit: `{results['implementation_commit']}`",
        f"- Cohort size per condition and seed: {results['sample_size']}",
        f"- Cohort seeds: {results['evaluation_seeds'][0]}–{results['evaluation_seeds'][-1]} ({len(results['evaluation_seeds'])} per condition)",
        f"- Bootstrap: {results['bootstrap_replications']} patient resamples per cohort-condition",
        "- Treatment is delayed only when radiotherapy starts more than 56 days after surgery.",
        "- The primary estimate is cross-fitted AIPW for the finite-cohort marginal RR.",
        "",
        "## Condition summaries",
        "",
        "| Condition | Estimable | Mean truth RR | Mean AIPW RR | Mean absolute error | 95% interval coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, summary in (("Measured confounding", a), ("Unmeasured U", b)):
        lines.append(
            f"| {name} | {summary['estimable_replicates']}/{summary['replicates']} | "
            f"{summary['truth_risk_ratio_mean']} | {summary['aipw_risk_ratio_mean']} | "
            f"{summary['absolute_mean_point_estimate_error']} | "
            f"{summary['cohort_interval_coverage_count']}/{summary['cohort_interval_coverage_denominator']} |"
        )
    lines.extend(
        [
            "",
            "## Registered hypotheses",
            "",
            f"- H1 measured-confounding recovery: **{h1['verdict']}**. Registered criteria require at least 18 of 20 cohort intervals to cover their finite-cohort truth and absolute across-seed mean point-estimate error at most 0.02.",
            f"- H2 weighted balance: {results['hypotheses']['H2_balance']['description']}",
            f"- H3 unmeasured confounding: {results['hypotheses']['H3_unmeasured_confounding']['description']}",
            "",
            "The E-value quantifies a sensitivity association strength for a defined risk ratio; it does not detect whether U exists. Undefined estimates and intervals remain null with explicit reasons in `results.json`.",
            "",
            "## Provenance",
            "",
            f"- Registration SHA-256: `{results['provenance']['preregistration_sha256']}`",
            f"- Implementation SHA-256: `{results['provenance']['implementation_sha256']}`",
            f"- Runner SHA-256: `{results['provenance']['runner_sha256']}`",
            "- Full per-seed results, denominators, source hashes, and run completion manifest are committed beside this report.",
            "",
        ]
    )
    return "\n".join(lines)


def run() -> dict[str, Any]:
    access = validate_access()
    implementation_commit = access["implementation_commit"]
    rows: list[dict[str, Any]] = []
    for condition, has_u in CONDITIONS:
        for seed in SEEDS:
            print(f"Running {condition}, seed {seed}", flush=True)
            rows.append(_run_replicate(seed, condition, has_u))

    summaries = {name: _summarize(rows, name) for name, _ in CONDITIONS}
    measured = summaries["measured_confounding"]
    h1_met = (
        measured["cohort_interval_coverage_count"] >= 18
        and measured["absolute_mean_point_estimate_error"] is not None
        and measured["absolute_mean_point_estimate_error"] <= 0.02
        and measured["cohort_interval_coverage_denominator"] == 20
    )
    unmeasured = summaries["unmeasured_confounding"]
    results: dict[str, Any] = {
        "experiment_id": "EXP-S8-K7-002",
        "description": "Cross-fitted recovery of synthetic marginal treatment-delay effects",
        "evidence_class": "synthetic_only",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "implementation_commit": implementation_commit,
        "sample_size": 5000,
        "bootstrap_replications": BOOTSTRAP_REPLICATES,
        "evaluation_seeds": list(SEEDS),
        "runtime_versions": RUNTIME_VERSIONS,
        "conditions": [name for name, _ in CONDITIONS],
        "estimand": "finite_cohort_marginal_risk_ratio_and_risk_difference",
        "hypotheses": {
            "H1_recovery": {"verdict": "MET" if h1_met else "NOT MET", "criteria_met": h1_met},
            "H2_balance": {
                "description": f"{measured['weighted_smd_below_0_10_count']}/{measured['weighted_smd_denominator']} measured-confounding replicates have maximum weighted SMD < 0.10; descriptive only."
            },
            "H3_unmeasured_confounding": {
                "description": f"mean AIPW bias under hidden U is {unmeasured['mean_bias']}; E-values are descriptive sensitivity summaries and do not detect U."
            },
        },
        "summaries": summaries,
        "replicates": rows,
        "provenance": {
            "preregistration_sha256": sha256(PREREG),
            "implementation_sha256": sha256(IMPLEMENTATION),
            "runner_sha256": sha256(RUNNER),
            "verifier_sha256": sha256(VERIFIER),
            "project_config_sha256": sha256(PROJECT_CONFIG),
            "dependency_lock_sha256": sha256(DEPENDENCY_LOCK),
            "access_log_sha256": sha256(ACCESS_LOG),
            "run_authorization_commit": _git("rev-parse", "HEAD"),
        },
    }
    results = _safe_json(results)
    result_bytes = (json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    report_bytes = _render_report(results).encode()
    _atomic_write(RESULTS, result_bytes)
    _atomic_write(REPORT, report_bytes)
    completion = {
        "experiment_id": "EXP-S8-K7-002",
        "status": "completed_once",
        "completed_at_utc": results["timestamp_utc"],
        "implementation_commit": implementation_commit,
        "run_authorization_commit": results["provenance"]["run_authorization_commit"],
        "runtime_versions": results["runtime_versions"],
        "preregistration_sha256": results["provenance"]["preregistration_sha256"],
        "implementation_sha256": results["provenance"]["implementation_sha256"],
        "runner_sha256": results["provenance"]["runner_sha256"],
        "verifier_sha256": results["provenance"]["verifier_sha256"],
        "project_config_sha256": results["provenance"]["project_config_sha256"],
        "dependency_lock_sha256": results["provenance"]["dependency_lock_sha256"],
        "access_log_sha256": results["provenance"]["access_log_sha256"],
        "results_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "replicate_count": len(rows),
        "evaluation_seeds": list(SEEDS),
    }
    _atomic_write(
        COMPLETION,
        (json.dumps(completion, indent=2, sort_keys=True) + "\n").encode(),
    )
    return results


if __name__ == "__main__":
    run()
