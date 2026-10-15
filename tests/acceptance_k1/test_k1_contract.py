"""Overseer-authored K1 acceptance tests. DO NOT EDIT (see docs/ml/K1-CONTRACT.md)."""

from __future__ import annotations

import importlib
import os
import re
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("VIGIL_ACCEPTANCE") != "1":
    pytest.skip("set VIGIL_ACCEPTANCE=1 to run K1 acceptance tests", allow_module_level=True)
K1 = importlib.import_module(os.environ.get("VIGIL_K1_MODULE", "vigil_ml.k1"))
REQUIRED_ROUTES = ("amortized", "ukf", "nuts", "npe")
SCHEDULE = [0, 60, 120, 180, 240, 300, 360]
SBC_SIMS = {"nuts": 30}
STUBS = (ROOT / "docs" / "STUBS.md").read_text() if (ROOT / "docs" / "STUBS.md").exists() else ""


def _registered_stub(route: str) -> bool:
    return f"K1-ROUTE:{route}" in STUBS


def _route(name):
    if name not in getattr(K1, "ROUTES", {}):
        if _registered_stub(name):
            pytest.xfail(f"route {name} registered as stub")
        pytest.fail(f"required K1 route '{name}' missing and not registered in docs/STUBS.md")
    return K1.ROUTES[name]


def _draws(route, obs, rng, n=400):
    out = route(obs, rng, n)
    for p in K1.PARAM_NAMES:
        assert p in out and len(out[p]) == n and np.all(np.isfinite(out[p])), f"bad samples for {p}"
    return out


def test_param_names_contract():
    assert {"doubling_time_days", "shedding_ca153", "clearance_ca153", "onset_day"} <= set(
        K1.PARAM_NAMES
    )


@pytest.mark.parametrize("name", REQUIRED_ROUTES)
def test_route_recovers_truth_with_posterior_intervals(name):
    route = _route(name)
    rng = np.random.default_rng(2024)
    truth, means, covered = [], [], []
    for _ in range(40):
        p = K1.sample_prior(rng)
        obs = K1.simulate_patient(p, SCHEDULE, rng)
        s = _draws(route, obs, rng)["doubling_time_days"]
        lo, hi = np.percentile(s, [5, 95])
        truth.append(p.doubling_time_days)
        means.append(float(np.mean(s)))
        covered.append(lo <= p.doubling_time_days <= hi)
    cov = float(np.mean(covered))
    corr = float(np.corrcoef(truth, means)[0, 1])
    assert 0.75 <= cov <= 0.97, f"{name}: 90% interval coverage {cov:.2f} outside [0.75, 0.97]"
    assert corr >= 0.6, f"{name}: posterior-mean correlation {corr:.2f} < 0.6"


@pytest.mark.parametrize("name", REQUIRED_ROUTES)
def test_sbc_through_route(name):
    route = _route(name)
    n_sims = SBC_SIMS.get(name, 60)
    rng = np.random.default_rng(7)
    ranks = {p: [] for p in K1.PARAM_NAMES}
    L = 100
    for _ in range(n_sims):
        p = K1.sample_prior(rng)
        obs = K1.simulate_patient(p, SCHEDULE, rng)
        post = _draws(route, obs, rng, n=L)
        for k in K1.PARAM_NAMES:
            ranks[k].append(np.sum(post[k] < getattr(p, k)))
    for k, r in ranks.items():
        u = (np.array(r) + 0.5) / (L + 1.0)
        pval = stats.kstest(u, "uniform").pvalue
        assert pval > 0.01, f"{name}/{k}: SBC rank non-uniform (KS p={pval:.4f})"


def test_routes_agree_with_reference():
    for n in ("nuts", "amortized", "npe"):
        _route(n)
    rng = np.random.default_rng(11)
    for _ in range(5):
        p = K1.sample_prior(rng)
        obs = K1.simulate_patient(p, SCHEDULE, rng)
        ref = _draws(K1.ROUTES["nuts"], obs, rng)["doubling_time_days"]
        for other in ("amortized", "npe"):
            o = _draws(K1.ROUTES[other], obs, rng)["doubling_time_days"]
            assert abs(np.mean(o) - np.mean(ref)) <= 0.30 * np.mean(ref), (
                f"{other} disagrees with NUTS"
            )
            lo, hi = np.percentile(o, [2.5, 97.5])
            assert lo <= np.mean(ref) <= hi, f"NUTS mean outside {other} 95% interval"


def test_risk_is_posterior_derived_and_monotone():
    rng = np.random.default_rng(3)
    p = K1.sample_prior(rng)
    obs = K1.simulate_patient(p, SCHEDULE, rng)
    route = K1.ROUTES.get("amortized") or next(iter(K1.ROUTES.values()))
    s = _draws(route, obs, rng)
    base = K1.risk_from_posterior(s, 365.0)
    faster = dict(s)
    faster["doubling_time_days"] = s["doubling_time_days"] * 0.5
    assert K1.risk_from_posterior(faster, 365.0) >= base - 1e-9
    assert K1.risk_from_posterior(s, 730.0) >= K1.risk_from_posterior(s, 180.0) - 1e-9
    assert 0.0 <= base <= 1.0


def test_no_direct_label_head():
    model = K1.HybridKineticModelK1()
    names = (
        [n for n, _ in getattr(model, "recognition_net", model).named_parameters()]
        if hasattr(getattr(model, "recognition_net", model), "named_parameters")
        else []
    )
    names += list(vars(model).keys())
    bad = [n for n in names if re.search(r"risk_logit|label_head", n)]
    assert not bad, f"model contains a direct label head: {bad}"
    src = Path(K1.__file__).read_text()
    assert "risk_logit" not in src and "label_head" not in src, "source defines a direct label head"


def test_identifiability_is_computed():
    out = K1.HybridKineticModelK1().identifiability_analysis()
    ev = np.array(out["eigenvalues"], dtype=float)
    assert len(ev) == len(K1.PARAM_NAMES), "eigenvalues must cover every parameter"
    ratio = np.abs(ev) / max(np.max(np.abs(ev)), 1e-300)
    expected_nonid = int(np.sum(ratio < 1e-6))
    assert len(out["non_identifiable"]) == expected_nonid, (
        "non_identifiable list not consistent with eigenvalues"
    )
