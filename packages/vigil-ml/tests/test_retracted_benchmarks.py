"""The invalid historical aggregate benchmark must not overwrite its recorded outputs."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[3]


def test_legacy_aggregate_runner_fails_closed_before_access_or_output():
    before = {
        relative: (ROOT / relative).read_bytes()
        for relative in (
            "reports/ml/BENCHMARK_REPORT.md",
            "reports/ml/results.json",
            "reports/ml/frozen_test_access_log.jsonl",
        )
    }
    result = subprocess.run(
        [sys.executable, "scripts/run_benchmarks.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "aggregate benchmark runner is retired" in result.stderr
    for relative, content in before.items():
        assert (ROOT / relative).read_bytes() == content
