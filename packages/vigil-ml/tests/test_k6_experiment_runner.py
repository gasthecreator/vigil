"""EXP-K6-001 runner: a tiny end-to-end smoke run and the re-derivation of a committed result file."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import xgboost  # noqa: F401  (before anything that may load another OpenMP runtime)

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "experiments" / "EXP-K6-001" / "run.py"
DEV = ROOT / "experiments" / "EXP-K6-001" / "dev_results.json"


def load():
    spec = importlib.util.spec_from_file_location("exp_k6_run", RUN)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k6_run"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_smoke_run_executes_end_to_end():
    out = subprocess.run(
        [sys.executable, str(RUN), "--smoke", "--workers", "2"],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    printed = out.stdout[out.stdout.index("{") :]
    assert set(json.loads(printed)) == {"H1", "H2", "H3"}


def test_aggregate_and_report_are_functions_of_the_stored_records():
    run = load()
    res = json.loads(DEV.read_text(encoding="utf-8"))
    again = json.loads(json.dumps(run.aggregate(res)))
    assert again == res["aggregate"]
    assert run.render_report(res) == run.render_report(json.loads(json.dumps(res)))


def test_w_grid_matches_amendment_3():
    run = load()
    assert len(run.CONFIG["w_grid"]) == 17
    assert min(run.CONFIG["w_grid"]) == 0.1 / 256
    assert max(run.CONFIG["w_grid"]) == 25.6
