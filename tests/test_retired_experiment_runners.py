"""Retired frozen-test runners must not reopen or overwrite historical experiments."""

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_ACCESS_LOG = ROOT / "data/audit/frozen_test_access.jsonl"
RETIRED_RUNNERS = {
    "001": (ROOT / "experiments/EXP-CORE-ML-001/run.py", "ABORTED.md"),
    "002": (ROOT / "experiments/EXP-CORE-ML-002/run.py", "WITHDRAWN.md"),
    "003": (ROOT / "experiments/EXP-CORE-ML-003/run.py", "ADR-0039"),
    "004": (ROOT / "experiments/EXP-CORE-ML-004/run.py", "ADR-0039"),
    "007": (ROOT / "experiments/EXP-CORE-ML-007/run.py", "already exists"),
}
PRESERVED_ARTIFACTS = (
    ROOT / "experiments/EXP-CORE-ML-002/results.json",
    ROOT / "experiments/EXP-CORE-ML-002/REPORT.md",
    ROOT / "experiments/EXP-CORE-ML-003/results.json",
    ROOT / "experiments/EXP-CORE-ML-003/REPORT.md",
    ROOT / "experiments/EXP-CORE-ML-004/results.json",
    ROOT / "experiments/EXP-CORE-ML-004/REPORT.md",
    ROOT / "experiments/EXP-CORE-ML-007/results.json",
    ROOT / "experiments/EXP-CORE-ML-007/REPORT.md",
    ROOT / "experiments/EXP-K4-001/hyperparameters.json",
    ROOT / "experiments/EXP-K4-001/dev_grid.json",
    ROOT / "experiments/EXP-K4-001/dev_results.json",
    ROOT / "experiments/EXP-K4-001/results.json",
    ROOT / "experiments/EXP-K4-001/REPORT.md",
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
        assert any(
            marker in output.lower()
            for marker in ("retired", "withdrawn", "stale", "exploratory", "already exists")
        )
        assert retirement_record in output
        assert f"EXP-CORE-ML-{experiment_id}" in output

    assert before == {path: _sha256(path) for path in PRESERVED_ARTIFACTS}


def test_k4_persisted_runner_modes_fail_before_overwriting_evidence():
    runner = ROOT / "experiments/EXP-K4-001/run.py"
    before = {path: _sha256(path) for path in PRESERVED_ARTIFACTS}
    for mode in ("--dev", "--dev-pipeline", "--frozen", "--rerender"):
        result = subprocess.run(
            [sys.executable, str(runner), mode],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0
        assert "refuses to overwrite existing evidence" in output
        assert "EXP-K4-001" in output
    assert before == {path: _sha256(path) for path in PRESERVED_ARTIFACTS}


def test_k4_smoke_uses_seed_range_after_development_not_frozen():
    runner = ROOT / "experiments/EXP-K4-001/run.py"
    spec = importlib.util.spec_from_file_location("exp_k4_seed_namespace_test", runner)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    dev = module.CONFIG["seeds"]["dev"]
    smoke = [module.base_seed("smoke", r) for r in range(module.SMOKE_CONFIG["n_replications"])]
    frozen = module.CONFIG["seeds"]["frozen"]
    frozen_seeds = {frozen["base"] + frozen["step"] * r for r in range(frozen["n"])}
    dev_seeds = {dev["base"] + dev["step"] * r for r in range(dev["n"])}
    assert set(smoke).isdisjoint(frozen_seeds | dev_seeds)
    assert module.design("smoke")["bootstrap_seed"] == module.base_seed("smoke", len(smoke))
