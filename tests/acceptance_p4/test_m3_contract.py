"""Overseer-authored M3 acceptance tests. DO NOT EDIT (see docs/ml/M3-M5-CONTRACT.md)."""

from __future__ import annotations

import importlib
import math
import os
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

if os.environ.get("VIGIL_ACCEPT_P4") != "1":
    pytest.skip("set VIGIL_ACCEPT_P4=1 to run Phase 4 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
M3 = importlib.import_module(os.environ.get("VIGIL_M3_MODULE", "vigil_ml.m3"))
STUBS = (ROOT / "docs" / "STUBS.md").read_text() if (ROOT / "docs" / "STUBS.md").exists() else ""
CVA, CVI = 0.05, 0.10
SIG = math.sqrt(CVA**2 + CVI**2)
P_ERR, P_REAL = 0.03, 0.20


def _gate(token):
    if token in STUBS:
        pytest.xfail(f"{token} registered as stub")


def _case(rng, lab_changed=False, force=None):
    level = math.exp(rng.normal(math.log(18.0), 0.3))
    n = int(rng.integers(3, 8))
    days = np.cumsum(rng.uniform(50, 90, n))
    hist = [(float(d), level * math.exp(rng.normal(0, SIG))) for d in days]
    new_day = float(days[-1] + rng.uniform(50, 90))
    u = (
        rng.random()
        if force is None
        else {"error": 0.0, "real": P_ERR + 0.001, "stable": 0.99}[force]
    )
    base = level * math.exp(rng.normal(0, SIG))
    if u < P_ERR:
        kind = "error"
        mode = int(rng.integers(3))
        value = (
            math.exp(rng.normal(math.log(18.0), 0.6))
            if mode == 0
            else (base * 10 if mode == 1 else base / 10)
        )
    elif u < P_ERR + P_REAL:
        kind = "real"
        f = math.exp(rng.uniform(math.log(1.4), math.log(3.0)))
        value = level * f * math.exp(rng.normal(0, SIG))
    else:
        kind, value = "stable", base
    if lab_changed:
        value *= math.exp(rng.normal(0, 0.10))
    return hist, new_day, float(value), kind


def _run(hist, new_day, value, **kw):
    return M3.adjudicate(hist, new_day, value, cv_analytical=CVA, cv_within=CVI, **kw)


def test_rcv_closed_forms():
    _gate("M3-RCV")
    assert M3.rcv(0.05, 0.10) == pytest.approx(
        math.sqrt(2) * 1.96 * math.sqrt(0.05**2 + 0.10**2), rel=1e-9
    )
    s = math.sqrt(math.log(1 + 0.05**2) + math.log(1 + 0.10**2))
    up, down = M3.rcv(0.05, 0.10, log_normal=True)
    assert up == pytest.approx(math.exp(1.96 * math.sqrt(2) * s) - 1, rel=1e-9)
    assert down == pytest.approx(math.exp(-1.96 * math.sqrt(2) * s) - 1, rel=1e-9)


def test_outputs_valid():
    rng = np.random.default_rng(1)
    for _ in range(300):
        h, d, v, _k = _case(rng)
        out = _run(h, d, v)
        ps = [out["p_real"], out["p_error"], out["p_stable"]]
        assert all(0.0 <= p <= 1.0 for p in ps) and abs(sum(ps) - 1.0) < 1e-6
        assert out["action"] in {"explained", "needs_repeat", "escalate"}


def _ece(p, y, bins=8):
    p, y = np.asarray(p), np.asarray(y)
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p <= hi) if hi == edges[-1] else (p >= lo) & (p < hi)
        if m.sum():
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(ece)


@pytest.fixture(scope="module")
def sim():
    rng = np.random.default_rng(2)
    rows = []
    for _ in range(3000):
        h, d, v, k = _case(rng)
        out = _run(h, d, v)
        rows.append((out["p_real"], out["p_error"], out["p_stable"], k, out["action"]))
    return rows


def test_calibration(sim):
    _gate("M3-CALIB")
    for idx, name, prior in ((0, "real", P_REAL), (1, "error", P_ERR)):
        p = np.array([r[idx] for r in sim])
        y = np.array([r[3] == name for r in sim], dtype=float)
        assert _ece(p, y) <= 0.06, f"{name}: ECE {_ece(p, y):.3f}"
        brier = float(np.mean((p - y) ** 2))
        base = float(np.mean((prior - y) ** 2))
        assert brier <= 0.85 * base, f"{name}: Brier {brier:.4f} vs prior {base:.4f}"


def test_discrimination(sim):
    _gate("M3-CALIB")
    rs = [(r[0], r[3]) for r in sim if r[3] in ("real", "stable")]
    auc_real = roc_auc_score([k == "real" for _, k in rs], [p for p, _ in rs])
    auc_err = roc_auc_score([r[3] == "error" for r in sim], [r[1] for r in sim])
    assert auc_real >= 0.85, f"AUROC real vs stable {auc_real:.3f}"
    assert auc_err >= 0.80, f"AUROC error vs rest {auc_err:.3f}"


def test_no_dismissal_policy(sim):
    _gate("M3-POLICY")
    for p_real, p_err, p_stable, _k, action in sim:
        if action == "explained":
            assert p_stable >= 0.90
        if action == "escalate":
            assert p_real >= 0.60
        if p_err >= 0.30:
            assert action == "needs_repeat"


def test_lab_change_lowers_real_probability():
    rng = np.random.default_rng(3)
    lower = 0
    n = 60
    for _ in range(n):
        h, d, _v, _k = _case(rng, force="stable")
        base = math.exp(np.mean([math.log(x) for _, x in h]))
        v = base * 1.35
        a = _run(h, d, v, lab_changed=False)["p_real"]
        b = _run(h, d, v, lab_changed=True)["p_real"]
        lower += int(b < a)
    assert lower >= int(0.95 * n), f"lab change lowered p_real in only {lower}/{n} cases"


def test_rationale_facts():
    _gate("M3-FACTS")
    rng = np.random.default_rng(4)
    for _ in range(30):
        h, d, v, _k = _case(rng)
        out = _run(h, d, v)
        facts = {f["type"]: f for f in out["rationale_facts"]}
        assert "rcv" in facts and "observed_change" in facts
        assert facts["rcv"]["value"] == pytest.approx(M3.rcv(CVA, CVI), rel=1e-6)
        base = math.exp(np.mean([math.log(x) for _, x in h]))
        assert facts["observed_change"]["value"] == pytest.approx(v / base, rel=0.01)
        assert all("fact_id" in f for f in out["rationale_facts"])
