"""Overseer-authored K8 acceptance tests. DO NOT EDIT (see docs/ml/K2-K8-CONTRACT.md)."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import norm

if os.environ.get("VIGIL_ACCEPT_3B") != "1":
    pytest.skip("set VIGIL_ACCEPT_3B=1 to run 3B acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
K8 = importlib.import_module(os.environ.get("VIGIL_K8_MODULE", "vigil_ml.k8"))
STUBS = (ROOT / "docs" / "STUBS.md").read_text() if (ROOT / "docs" / "STUBS.md").exists() else ""


def _gate(token):
    if token in STUBS:
        pytest.xfail(f"{token} registered as stub")


def _draw(rng, n, prev=0.2):
    y = (rng.random(n) < prev).astype(int)
    s = np.where(y == 1, rng.normal(1.2, 1.0, n), rng.normal(0.0, 1.0, n))
    return s, y


@pytest.mark.parametrize("alpha", [0.1, 0.2])
def test_conformal_risk_control(alpha):
    _gate("K8-CRC")
    rng = np.random.default_rng(10)
    fnr, fpr = [], []
    for _ in range(300):
        sc, yc = _draw(rng, 800)
        st, yt = _draw(rng, 4000)
        ctrl = K8.ConformalRiskController(alpha).fit(sc, yc)
        alert = np.asarray(ctrl.decide(st), dtype=bool)
        fnr.append(np.mean(~alert[yt == 1]))
        fpr.append(np.mean(alert[yt == 0]))
    tau = 1.2 + norm.ppf(alpha)
    oracle_fpr = 1.0 - norm.cdf(tau)
    assert np.mean(fnr) <= alpha + 0.015, f"mean FNR {np.mean(fnr):.3f} > alpha {alpha}"
    assert np.mean(fpr) <= oracle_fpr + 0.10, (
        f"mean FPR {np.mean(fpr):.3f} vs oracle {oracle_fpr:.3f} (trivial alerting?)"
    )


def test_ood_gate():
    _gate("K8-OOD")
    rng = np.random.default_rng(11)
    gate = K8.OODGate().fit(rng.normal(size=(2000, 6)))
    inliers = rng.normal(size=(2000, 6))
    shifted = rng.normal(size=(2000, 6))
    shifted[:, :3] += 4.0
    assert np.mean(gate.is_ood(inliers)) <= 0.08
    assert np.mean(gate.is_ood(shifted)) >= 0.90


def test_adaptive_conformal_tracks_drift():
    _gate("K8-ACI")
    alpha = 0.1
    rng = np.random.default_rng(12)
    steps = 5000
    scale = np.linspace(1.0, 2.0, steps)

    def run(adaptive):
        aci = K8.AdaptiveConformal(alpha, gamma=0.005)
        misses = []
        for t in range(steps):
            a_t = aci.alpha_t if adaptive else alpha
            a_t = min(max(a_t, 1e-3), 0.999)
            q = norm.ppf(1.0 - a_t / 2.0)  # half-width calibrated at scale 1
            resid = abs(rng.normal(0.0, scale[t]))
            covered = resid <= q
            misses.append(0 if covered else 1)
            if adaptive:
                aci.update(bool(covered))
        return float(np.mean(misses[1000:]))

    miss_adaptive = run(True)
    miss_static = run(False)
    assert abs(miss_adaptive - alpha) <= 0.03, f"adaptive miscoverage {miss_adaptive:.3f}"
    assert miss_static > alpha + 0.05, "test is not sensitive to drift"
