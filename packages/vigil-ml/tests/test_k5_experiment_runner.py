"""EXP-K5-001 runner: what the estimators may see, and a tiny end-to-end smoke run."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "experiments" / "EXP-K5-001" / "run.py"


def load():
    spec = importlib.util.spec_from_file_location("exp_k5_run", RUN)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k5_run"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_estimator_inputs_are_exactly_patient_day_lab_value():
    run = load()
    obs, pts = run.clinical_cohort(3, 60)
    from vigil_sim.multilab import MultiLabConfig, apply_multilab, draw_true_beta

    c = apply_multilab(obs, pts, MultiLabConfig(0.15, 0.3, 1), draw_true_beta(2, 0.15, 6))
    args = run.fit_inputs(c)
    assert len(args) == 4
    o = c.observations
    assert (args[0] == o["patient_id"].to_numpy()).all()
    assert (args[1] == o["day"].to_numpy()).all()  # visit day, not calendar day
    assert (args[2] == o["lab"].to_numpy()).all()
    assert (args[3] == o["y"].to_numpy()).all()


def test_runner_never_touches_latent_columns():
    src = RUN.read_text(encoding="utf-8")
    assert "latent_" not in src


def test_smoke_run_executes_end_to_end():
    out = subprocess.run([sys.executable, str(RUN), "--smoke"], capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr[-2000:]
    assert json.loads(out.stdout.strip().splitlines()[-1])["ok"] is True
