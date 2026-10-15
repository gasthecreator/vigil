"""Overseer-authored K1 acceptance tests, contract v2. DO NOT EDIT (see docs/ml/K1-CONTRACT.md)."""

from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("VIGIL_ACCEPTANCE") != "1":
    pytest.skip("set VIGIL_ACCEPTANCE=1 to run K1 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
K1 = importlib.import_module(os.environ.get("VIGIL_K1_MODULE", "vigil_ml.k1"))
STUBS = (ROOT / "docs" / "STUBS.md").read_text() if (ROOT / "docs" / "STUBS.md").exists() else ""
SCHEDULE = [0, 60, 120, 180, 240, 300, 360]


def _stub_or_fail(token: str, message: str):
    if token in STUBS:
        pytest.xfail(f"{token} registered as stub")
    pytest.fail(message)


def test_amortized_route_is_distinct_from_npe():
    routes = K1.ROUTES
    if "amortized" not in routes or "npe" not in routes:
        pytest.fail("amortized and npe routes are required")
    assert routes["amortized"] is not routes["npe"], "amortized is the same callable as npe"
    src = inspect.getsource(routes["amortized"]).lower()
    assert "npe" not in src, "amortized route references the npe route"
    rng_a, rng_b = np.random.default_rng(5), np.random.default_rng(5)
    p = K1.sample_prior(np.random.default_rng(1))
    obs = K1.simulate_patient(p, SCHEDULE, np.random.default_rng(2))
    a = routes["amortized"](obs, rng_a, 200)["doubling_time_days"]
    b = routes["npe"](obs, rng_b, 200)["doubling_time_days"]
    assert not np.allclose(a, b), "amortized and npe return identical draws"


def test_training_is_real():
    if not hasattr(K1, "train_amortized"):
        _stub_or_fail("K1-TRAIN", "train_amortized missing and K1-TRAIN not registered")
    real = K1.train_amortized(n_sims=1500, seed=0, shuffle_pairs=False)
    shuf = K1.train_amortized(n_sims=1500, seed=0, shuffle_pairs=True)
    again = K1.train_amortized(n_sims=1500, seed=0, shuffle_pairs=False)
    other = K1.train_amortized(n_sims=1500, seed=1, shuffle_pairs=False)
    v = np.array(real["val_loss"], dtype=float)
    assert len(v) >= 5 and len(real["train_loss"]) == len(v)
    assert v[0] - v[-1] >= 0.2, f"validation loss did not fall (first {v[0]:.3f}, last {v[-1]:.3f})"
    sv = np.array(shuf["val_loss"], dtype=float)
    assert sv[0] - sv[-1] < 0.05, (
        "shuffled-pair control still 'learns': loss is not from real optimisation"
    )
    assert np.allclose(real["val_loss"], again["val_loss"]), "same seed does not reproduce training"
    assert not np.allclose(real["val_loss"], other["val_loss"]), (
        "different seed gives identical history"
    )


def test_no_pickled_artifacts():
    bad = [
        p
        for ext in ("*.pt", "*.pth", "*.pkl", "*.pickle")
        for p in (ROOT / "packages").rglob(ext)
        if ".venv" not in p.parts
    ]
    assert not bad, (
        f"pickled/binary model artifacts under packages/: {[str(b.relative_to(ROOT)) for b in bad]}"
    )
    src = Path(K1.__file__).read_text()
    assert "weights_only=False" not in src and "pickle" not in src, (
        "K1 source loads pickled objects"
    )


def test_k1_discriminates_on_project_simulator():
    try:
        from sklearn.metrics import roc_auc_score
        from vigil_sim.generators import GeneratorType, get_generator
    except ImportError:  # pragma: no cover
        pytest.fail("vigil_sim / sklearn required")
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=5).generate_cohort(
        300, duration_days=730.0
    )
    obs_df, pts = cohort.to_observations_dataframe(), cohort.to_patients_dataframe()
    rng = np.random.default_rng(0)
    route = K1.ROUTES["amortized"]
    y, s, ref = [], [], []
    for _, p in pts.iterrows():
        rec = bool(p["true_recurrence_event"])
        day = p["true_recurrence_day"]
        if rec and day is not None and day <= 365:
            continue
        ce = p["competing_event_day"]
        if ce is not None and ce == ce and ce <= 730 and not rec:
            continue
        o = obs_df[(obs_df.patient_id == p["patient_id"]) & (obs_df.day <= 365)].dropna(
            subset=["observed_ca_15_3"]
        )
        if len(o) < 2:
            continue
        ob = K1.K1Observations(
            days=o["day"].to_numpy(float), values={"ca153": o["observed_ca_15_3"].to_numpy(float)}
        )
        samples = route(ob, rng, 100)
        s.append(K1.risk_from_posterior(samples, 730.0))
        ref.append(float(o["observed_ca_15_3"].iloc[-1]))
        y.append(int(rec and day is not None and 365 < day <= 730))
    assert sum(y) >= 10 and len(set(y)) == 2, "too few events to evaluate"
    auc = roc_auc_score(y, s)
    ref_auc = roc_auc_score(y, ref)
    bar = max(0.55, ref_auc - 0.02)
    if auc < bar:
        _stub_or_fail(
            "K1-WORLD",
            f"K1 AUC on the project simulator is {auc:.3f} < {bar:.3f} (last-CA15-3 rule {ref_auc:.3f}) and K1-WORLD is not registered",
        )
