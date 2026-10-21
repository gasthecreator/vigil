#!/usr/bin/env python3
"""Verify EXP-S8-K7-004 artifacts without generating or reading cohorts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments" / "EXP-S8-K7-004"
sys.path.insert(0, str(EXPERIMENT))
from run import (  # noqa: E402
    ACCESS_LOG,
    COMPLETION,
    DEPENDENCY_LOCK,
    IMPLEMENTATION,
    PREREG,
    PROJECT_CONFIG,
    REPORT,
    RESULTS,
    RUNNER,
    SEEDS,
    VERIFIER,
    _render_report,
    sha256,
    validate_seed_namespaces,
)


def verify() -> dict[str, Any]:
    validate_seed_namespaces()
    for path in (
        ACCESS_LOG,
        COMPLETION,
        PREREG,
        IMPLEMENTATION,
        RUNNER,
        VERIFIER,
        PROJECT_CONFIG,
        DEPENDENCY_LOCK,
        RESULTS,
        REPORT,
    ):
        if not path.is_file():
            raise RuntimeError(f"required experiment artifact is missing: {path.name}")
    completion = json.loads(COMPLETION.read_text(encoding="utf-8"))
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    checks = {
        "preregistration_sha256": sha256(PREREG),
        "implementation_sha256": sha256(IMPLEMENTATION),
        "runner_sha256": sha256(RUNNER),
        "verifier_sha256": sha256(VERIFIER),
        "project_config_sha256": sha256(PROJECT_CONFIG),
        "dependency_lock_sha256": sha256(DEPENDENCY_LOCK),
        "access_log_sha256": sha256(ACCESS_LOG),
        "results_sha256": sha256(RESULTS),
        "report_sha256": sha256(REPORT),
    }
    for key, actual in checks.items():
        if completion.get(key) != actual:
            raise RuntimeError(f"completion manifest mismatch for {key}")
    if results.get("experiment_id") != "EXP-S8-K7-004":
        raise RuntimeError("results identify a different experiment")
    if tuple(results.get("evaluation_seeds", ())) != SEEDS:
        raise RuntimeError("result seed set differs from registration")
    provenance = results.get("provenance", {})
    for key in (
        "preregistration_sha256",
        "implementation_sha256",
        "runner_sha256",
        "verifier_sha256",
        "project_config_sha256",
        "dependency_lock_sha256",
        "access_log_sha256",
    ):
        if provenance.get(key) != checks[key]:
            raise RuntimeError(f"result provenance mismatch for {key}")
    if results.get("implementation_commit") != completion.get("implementation_commit"):
        raise RuntimeError("completion manifest identifies a different implementation commit")
    if results.get("runtime_versions") != completion.get("runtime_versions"):
        raise RuntimeError("completion manifest runtime versions differ from results")
    expected_pairs = {
        (condition, seed)
        for condition in ("measured_confounding", "unmeasured_confounding")
        for seed in SEEDS
    }
    actual_pairs = {
        (row.get("condition"), row.get("seed")) for row in results.get("replicates", [])
    }
    if len(results.get("replicates", [])) != len(expected_pairs) or actual_pairs != expected_pairs:
        raise RuntimeError(
            "result rows do not cover each registered condition and seed exactly once"
        )
    if completion.get("replicate_count") != len(expected_pairs):
        raise RuntimeError("completion manifest replicate denominator is incorrect")
    for row in results.get("replicates", []):
        if row.get("status") != "estimable":
            continue
        point_digest = row.get("estimates", {}).get("fold_assignment_sha256")
        bootstrap = row.get("bootstrap", {})
        bootstrap_digest = bootstrap.get("grouped_fold_audit_sha256")
        if not isinstance(point_digest, str) or len(point_digest) != 64:
            raise RuntimeError("estimable cohort lacks point grouped-fold audit digest")
        if not isinstance(bootstrap_digest, str) or len(bootstrap_digest) != 64:
            raise RuntimeError("estimable cohort lacks bootstrap grouped-fold audit digest")
        if bootstrap.get("bootstrap_replications") != 1000:
            raise RuntimeError("estimable cohort has wrong bootstrap denominator")
        audited = bootstrap.get("audited_estimable_resamples")
        aipw_failures = bootstrap.get("confidence_intervals", {}).get("aipw", {}).get(
            "non_estimable_resamples"
        )
        if (
            not isinstance(audited, int)
            or not isinstance(aipw_failures, int)
            or audited < 0
            or aipw_failures < 0
            or audited + aipw_failures < 1000
            or audited > 1000
        ):
            raise RuntimeError("bootstrap grouped-fold audit denominator is inconsistent")
    if _render_report(results) != REPORT.read_text(encoding="utf-8"):
        raise RuntimeError("report content does not render exactly from results.json")
    entries = [
        json.loads(line)
        for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    k7_entries = [entry for entry in entries if entry.get("experiment_id") == "EXP-S8-K7-004"]
    if len(k7_entries) != 1 or k7_entries[0].get("implementation_commit") != completion.get(
        "implementation_commit"
    ):
        raise RuntimeError("access record does not identify the result implementation")
    subprocess.check_call(
        ["git", "merge-base", "--is-ancestor", completion["implementation_commit"], "HEAD"],
        cwd=ROOT,
    )
    subprocess.check_call(
        ["git", "merge-base", "--is-ancestor", completion["run_authorization_commit"], "HEAD"],
        cwd=ROOT,
    )
    subprocess.check_call(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            k7_entries[0]["registration_commit"],
            completion["implementation_commit"],
        ],
        cwd=ROOT,
    )
    return {"status": "verified", "checks": checks}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
