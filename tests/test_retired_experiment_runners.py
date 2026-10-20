"""Retired frozen-test runners must not reopen or overwrite historical experiments."""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_ACCESS_LOG = ROOT / "data/audit/frozen_test_access.jsonl"
RETIRED_RUNNERS = {
    "001": (ROOT / "experiments/EXP-CORE-ML-001/run.py", "ABORTED.md"),
    "002": (ROOT / "experiments/EXP-CORE-ML-002/run.py", "WITHDRAWN.md"),
}
PRESERVED_ARTIFACTS = (
    ROOT / "experiments/EXP-CORE-ML-002/results.json",
    ROOT / "experiments/EXP-CORE-ML-002/REPORT.md",
    FROZEN_ACCESS_LOG,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_retired_frozen_test_runners_fail_before_touching_evidence():
    before = {path: _sha256(path) for path in PRESERVED_ARTIFACTS}

    for experiment_id, (runner, retirement_record) in RETIRED_RUNNERS.items():
        result = subprocess.run(
            [sys.executable, str(runner)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0
        assert "retired" in output.lower() or "withdrawn" in output.lower()
        assert retirement_record in output
        assert f"EXP-CORE-ML-{experiment_id}" in output

    assert before == {path: _sha256(path) for path in PRESERVED_ARTIFACTS}
