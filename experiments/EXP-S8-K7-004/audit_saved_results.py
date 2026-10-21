#!/usr/bin/env python3
"""Independently audit K7-004 saved aggregates without generating cohorts."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENT))
from verify import verify as verify_run  # noqa: E402

RESULTS = EXPERIMENT / "results.json"
COMPLETION = EXPERIMENT / "RUN_COMPLETION.json"
AUDIT = EXPERIMENT / "POSTRUN-AUDIT.json"
CONDITIONS = ("measured_confounding", "unmeasured_confounding")
SEEDS = tuple(range(620261141, 620261161))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _close(actual: Any, expected: float, *, field: str) -> None:
    if not isinstance(actual, (float, int)) or not math.isclose(
        float(actual), expected, rel_tol=1e-12, abs_tol=1e-12
    ):
        raise RuntimeError(f"saved summary mismatch for {field}: {actual!r} != {expected!r}")


def _e_value(rr: float) -> float:
    effective = rr if rr >= 1.0 else 1.0 / rr
    return effective + math.sqrt(effective * (effective - 1.0))


def _audit_condition(results: dict[str, Any], condition: str) -> dict[str, Any]:
    rows = [row for row in results["replicates"] if row["condition"] == condition]
    expected_seeds = set(SEEDS)
    if len(rows) != len(SEEDS) or {row["seed"] for row in rows} != expected_seeds:
        raise RuntimeError(f"{condition} does not contain each registered seed exactly once")
    if any(row["status"] != "estimable" for row in rows):
        raise RuntimeError(f"{condition} contains a non-estimable cohort")

    estimates = [float(row["estimates"]["estimates"]["aipw"]["risk_ratio"]) for row in rows]
    truth = [float(row["truth"]["risk_ratio"]) for row in rows]
    bias = statistics.mean(estimates) - statistics.mean(truth)
    coverage = [bool(row["aipw_interval_covers_truth"]) for row in rows]
    smd = [float(row["estimates"]["covariate_balance"]["maximum_weighted_smd"]) for row in rows]
    max_weight = max(
        float(row["estimates"]["weight_diagnostics"]["maximum_stabilized_weight"]) for row in rows
    )
    undefined_bootstrap = 0
    for row in rows:
        if len(row["estimates"].get("fold_assignment_sha256", "")) != 64:
            raise RuntimeError("saved point estimate lacks grouped-fold audit evidence")
        intervals = row["bootstrap"]["confidence_intervals"]
        if row["bootstrap"]["bootstrap_replications"] != 1000:
            raise RuntimeError("saved bootstrap count differs from preregistration")
        if len(row["bootstrap"].get("grouped_fold_audit_sha256", "")) != 64:
            raise RuntimeError("saved bootstrap lacks grouped-fold audit evidence")
        if not 0 <= row["bootstrap"].get("audited_estimable_resamples", -1) <= 1000:
            raise RuntimeError("saved grouped-fold audit denominator is invalid")
        aipw_ci = intervals["aipw"]["ci_95"]
        if aipw_ci is None:
            raise RuntimeError("AIPW interval is undefined despite an estimable cohort")
        undefined_bootstrap += int(intervals["aipw"]["non_estimable_resamples"])
        point_rr = float(row["estimates"]["estimates"]["aipw"]["risk_ratio"])
        e_values = row["aipw_e_values"]
        if e_values is None:
            raise RuntimeError("AIPW E-value missing for a defined point estimate and interval")
        nearest_limit = aipw_ci[0] if point_rr >= 1.0 else aipw_ci[1]
        expected_ci_e = 1.0
        if (point_rr >= 1.0 and nearest_limit > 1.0) or (point_rr < 1.0 and nearest_limit < 1.0):
            expected_ci_e = _e_value(nearest_limit)
        _close(e_values["point_estimate"], _e_value(point_rr), field=f"{condition} E-value point")
        _close(
            e_values["confidence_limit_nearest_null"],
            expected_ci_e,
            field=f"{condition} E-value CI",
        )

    summary = results["summaries"][condition]
    _close(
        summary["truth_risk_ratio_mean"], statistics.mean(truth), field=f"{condition} truth mean"
    )
    _close(
        summary["aipw_risk_ratio_mean"], statistics.mean(estimates), field=f"{condition} AIPW mean"
    )
    _close(summary["aipw_risk_ratio_sd"], statistics.stdev(estimates), field=f"{condition} AIPW SD")
    _close(
        summary["aipw_risk_ratio_median"],
        statistics.median(estimates),
        field=f"{condition} AIPW median",
    )
    _close(summary["aipw_risk_ratio_min"], min(estimates), field=f"{condition} AIPW minimum")
    _close(summary["aipw_risk_ratio_max"], max(estimates), field=f"{condition} AIPW maximum")
    _close(summary["mean_bias"], bias, field=f"{condition} mean bias")
    _close(
        summary["absolute_mean_point_estimate_error"],
        abs(bias),
        field=f"{condition} absolute mean error",
    )
    if summary["cohort_interval_coverage_count"] != sum(coverage):
        raise RuntimeError(f"{condition} coverage count does not match replicate rows")
    if summary["cohort_interval_coverage_denominator"] != len(coverage):
        raise RuntimeError(f"{condition} coverage denominator does not match replicate rows")
    if summary["weighted_smd_below_0_10_count"] != sum(value < 0.10 for value in smd):
        raise RuntimeError(f"{condition} SMD count does not match replicate rows")
    if summary["weighted_smd_denominator"] != len(smd):
        raise RuntimeError(f"{condition} SMD denominator does not match replicate rows")
    if max_weight > 10.0:
        raise RuntimeError(f"{condition} violated the registered stabilized-weight bound")
    return {
        "replicate_count": len(rows),
        "interval_coverage_count": sum(coverage),
        "interval_coverage_denominator": len(coverage),
        "maximum_stabilized_weight": max_weight,
        "undefined_aipw_bootstrap_resamples": undefined_bootstrap,
        "mean_aipw_bias": bias,
        "aggregate_parity": True,
        "e_value_parity": True,
    }


def audit() -> dict[str, Any]:
    verify_run()
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    condition_audits = {condition: _audit_condition(results, condition) for condition in CONDITIONS}
    measured = results["summaries"]["measured_confounding"]
    h1_met = (
        measured["cohort_interval_coverage_count"] >= 18
        and measured["absolute_mean_point_estimate_error"] <= 0.02
        and measured["cohort_interval_coverage_denominator"] == 20
    )
    if results["hypotheses"]["H1_recovery"]["criteria_met"] is not h1_met:
        raise RuntimeError("saved H1 verdict does not match the registered criteria")
    report = {
        "experiment_id": "EXP-S8-K7-004",
        "audit_status": "passed",
        "audit_after_saved_run": True,
        "cohort_generation_performed": False,
        "replayed_seeds": False,
        "result_sha256": _sha256(RESULTS),
        "completion_manifest_sha256": _sha256(COMPLETION),
        "audit_script_sha256": _sha256(Path(__file__).resolve()),
        "aggregate_and_e_value_parity": True,
        "h1_verdict_parity": True,
        "conditions": condition_audits,
        "h1_verdict": results["hypotheses"]["H1_recovery"]["verdict"],
    }
    AUDIT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
