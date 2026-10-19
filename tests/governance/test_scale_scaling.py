"""The scaling analyzer must call a budget missed when the extrapolation misses it (no verdict from a small run)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("analyze_scale_scaling", ROOT / "scripts" / "analyze_scale_scaling.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(n, triage, timeline):
    return {
        "run": {"n_patients": n, "obs_per_patient": 10},
        "metrics": {"triage_p95_ms": triage, "timeline_p95_ms": timeline},
    }


def test_small_passing_runs_do_not_hide_a_linear_budget_miss(tmp_path, monkeypatch):
    mod = _load()
    runs = tmp_path / "scale_runs"
    runs.mkdir()
    for n, t in ((1000, 50.0), (5000, 250.0)):  # both under 400 ms, slope 0.05 ms/patient
        (runs / f"size_{n}.json").write_text(json.dumps(_run(n, t, 10.0)))
    monkeypatch.setattr(mod, "RUNS", runs)
    monkeypatch.setattr(mod, "OUT", tmp_path / "out.json")
    assert mod.main() == 0
    out = json.loads((tmp_path / "out.json").read_text())
    tri = out["metrics"]["triage_p95_ms"]
    assert tri["meets_budget_at_plan_size"] is False
    assert tri["extrapolated_at_plan_size_ms"] > 4000
    assert 7000 < tri["patients_within_budget_linear_estimate"] < 9000
    assert out["metrics"]["timeline_p95_ms"]["meets_budget_at_plan_size"] is True
    assert out["verdict"].startswith("NOT MET")
