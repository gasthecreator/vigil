#!/usr/bin/env python3
"""Nightly-ish mutation score for the M5 explanation verifier (G-06).

Uses `mutmut` when installed; otherwise records a documented skip with reason.
Writes reports/quality/MUTATION_SCORE.json (script-written only).

Target kill rate ≥ 80% (MASTER_PLAN §12). Misses are reported honestly.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "quality" / "MUTATION_SCORE.json"
TARGET = 80.0


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("mutmut") is None and not _has_mutmut_module():
        # Prefer documenting absence over fabricating a score.
        payload = {
            "module": "vigil_ml.m5",
            "tool": "mutmut",
            "status": "tool_not_installed",
            "target_kill_percent": TARGET,
            "kill_percent": None,
            "honest_note": "mutmut was not installed in this environment; install with "
            "`uv add --dev mutmut` and re-run scripts/run_mutation_m5.py on the nightly job.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "machine": {"platform": platform.platform(), "python": sys.version.split()[0]},
            "command": "uv run python scripts/run_mutation_m5.py",
        }
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    # Bounded run: only m5.py; paths relative to packages/vigil-ml
    env = {**os.environ, "PYTHONPATH": str(ROOT / "packages" / "vigil-ml")}
    cmd = [
        sys.executable,
        "-m",
        "mutmut",
        "run",
        "--paths-to-mutate=vigil_ml/m5.py",
        "--tests-dir=tests",
        "--runner",
        "python -m pytest tests/test_m3_m5.py -q --tb=no",
        "--no-progress",
    ]
    res = subprocess.run(cmd, cwd=ROOT / "packages" / "vigil-ml", env=env, capture_output=True, text=True)
    results = subprocess.run(
        [sys.executable, "-m", "mutmut", "results"],
        cwd=ROOT / "packages" / "vigil-ml",
        env=env,
        capture_output=True,
        text=True,
    )
    # Parse crude stats from results output when available
    kill_percent = None
    text = results.stdout + "\n" + res.stdout
    # mutmut 2.x prints "Killed X out of Y"
    import re

    counts = _cache_counts(ROOT / "packages" / "vigil-ml" / ".mutmut-cache")
    killed = counts.get("ok_killed", 0) + counts.get("ok_timeout", 0)
    total = sum(counts.values())
    if total:
        kill_percent = 100.0 * killed / total

    payload = {
        "module": "vigil_ml.m5",
        "tool": "mutmut",
        "status": "ran" if res.returncode == 0 or kill_percent is not None else "failed",
        "target_kill_percent": TARGET,
        "kill_percent": kill_percent,
        "mutant_counts": counts,
        "meets_target": (kill_percent is not None and kill_percent >= TARGET),
        "stdout_tail": text[-2000:],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "machine": {"platform": platform.platform(), "python": sys.version.split()[0]},
        "command": " ".join(cmd),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in payload if k != "stdout_tail"}, indent=2))
    if kill_percent is not None and kill_percent + 1e-9 < TARGET:
        print(
            f"⚠️  mutation kill {kill_percent:.1f}% < target {TARGET}% — reported, not reworded.",
            file=sys.stderr,
        )
    return 0


def _cache_counts(path: Path) -> dict[str, int]:
    """Mutant status counts from mutmut's sqlite cache (the only reliable source in mutmut 2.x)."""
    import sqlite3

    if not path.exists():
        return {}
    with sqlite3.connect(path) as con:
        rows = con.execute("select status, count(*) from mutant group by status").fetchall()
    return {status: n for status, n in rows}


def _has_mutmut_module() -> bool:
    try:
        import mutmut  # noqa: F401

        return True
    except ImportError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
