#!/usr/bin/env python3
"""Verify EXP-S8-K7-002 artifacts without generating or reading cohorts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments" / "EXP-S8-K7-002"
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
)


def verify() -> dict[str, Any]:
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
    if results.get("experiment_id") != "EXP-S8-K7-002":
        raise RuntimeError("results identify a different experiment")
    if tuple(results.get("evaluation_seeds", ())) != SEEDS:
        raise RuntimeError("result seed set differs from registration")
    if results.get("provenance", {}).get("access_log_sha256") != checks["access_log_sha256"]:
        raise RuntimeError("result provenance does not match the committed access log")
    if _render_report(results) != REPORT.read_text(encoding="utf-8"):
        raise RuntimeError("report content does not render exactly from results.json")
    entries = [
        json.loads(line)
        for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    k7_entries = [entry for entry in entries if entry.get("experiment_id") == "EXP-S8-K7-002"]
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
