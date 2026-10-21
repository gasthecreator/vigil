#!/usr/bin/env python3
"""Verify the preserved K7-002 failure record without replaying its seeds."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments" / "EXP-S8-K7-002"
ACCESS_LOG = EXPERIMENT / "ACCESS_LOG.jsonl"
FAILURE = EXPERIMENT / "FAILED_RUN.json"
SPENT_SEEDS = tuple(range(620261101, 620261121))
CONDITIONS = ("measured_confounding", "unmeasured_confounding")


def _git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def _git_hash(commit: str, path: str) -> str:
    return hashlib.sha256(_git_bytes(commit, path)).hexdigest()


def verify() -> dict[str, Any]:
    failure = json.loads(FAILURE.read_text(encoding="utf-8"))
    entries = [
        json.loads(line)
        for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(entries) != 2:
        raise RuntimeError("K7-002 access log must preserve one pre-run and one failure entry")
    preregistration, failed = entries
    if preregistration.get("status") != "pre_run_record_committed":
        raise RuntimeError("K7-002 pre-run record is missing")
    if failed.get("event") != "one_time_run_failed_after_cohort_generation":
        raise RuntimeError("K7-002 failure event is missing")
    if failure != failed:
        raise RuntimeError("FAILED_RUN.json does not match the append-only access log")
    if tuple(failure.get("evaluation_seeds_consumed", ())) != SPENT_SEEDS:
        raise RuntimeError("K7-002 spent seed range differs from its registration")
    if tuple(failure.get("cohort_conditions_completed", ())) != CONDITIONS:
        raise RuntimeError("K7-002 condition coverage differs from its registration")
    if failure.get("cohort_condition_runs_completed") != len(SPENT_SEEDS) * len(CONDITIONS):
        raise RuntimeError("K7-002 completed cohort-condition denominator is invalid")
    if failure.get("bootstrap_resamples_completed") != 40_000:
        raise RuntimeError("K7-002 bootstrap access denominator is invalid")
    if failure.get("result_rows_persisted") is not False or failure.get("artifacts_written") != []:
        raise RuntimeError("failure record incorrectly claims persisted result artifacts")
    for output in ("results.json", "REPORT.md", "RUN_COMPLETION.json"):
        if (EXPERIMENT / output).exists():
            raise RuntimeError(f"K7-002 unexpectedly contains {output}")

    source_commit = preregistration["runner_commit"]
    expected_hashes = {
        "preregistration_sha256": "experiments/EXP-S8-K7-002/PREREG.md",
        "implementation_sha256": "packages/vigil-ml/vigil_ml/causal_k7_replacement.py",
        "runner_sha256": "experiments/EXP-S8-K7-002/run.py",
        "verifier_sha256": "experiments/EXP-S8-K7-002/verify.py",
        "project_config_sha256": "pyproject.toml",
        "dependency_lock_sha256": "uv.lock",
    }
    for field, path in expected_hashes.items():
        if _git_hash(source_commit, path) != preregistration.get(field):
            raise RuntimeError(f"K7-002 source provenance mismatch for {field}")
    for predecessor in (
        preregistration["registration_commit"],
        preregistration["implementation_commit"],
    ):
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", predecessor, source_commit], cwd=ROOT
        )
    subprocess.check_call(
        ["git", "merge-base", "--is-ancestor", failure["run_commit"], "HEAD"], cwd=ROOT
    )
    return {
        "status": "failed_run_evidence_verified",
        "spent_seed_count": len(SPENT_SEEDS),
        "cohort_condition_runs": failure["cohort_condition_runs_completed"],
        "result_artifacts_persisted": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
