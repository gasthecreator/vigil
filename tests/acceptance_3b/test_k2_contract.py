"""Overseer-authored K2 acceptance tests. DO NOT EDIT (see docs/ml/K2-K8-CONTRACT.md)."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("VIGIL_ACCEPT_3B") != "1":
    pytest.skip("set VIGIL_ACCEPT_3B=1 to run 3B acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
K2 = importlib.import_module(os.environ.get("VIGIL_K2_MODULE", "vigil_ml.k2"))
STUBS = (ROOT / "docs" / "STUBS.md").read_text() if (ROOT / "docs" / "STUBS.md").exists() else ""
ALPHA = 0.05


def _gate(token):
    if token in STUBS:
        pytest.xfail(f"{token} registered as stub")


def _days(rng, n_visits):
    return np.cumsum(rng.uniform(40.0, 80.0, size=n_visits))


def _null_series(rng, n_visits, scenario):
    base = np.log(18.0) + rng.normal(0.0, 0.3)
    if scenario == "gauss10":
        eps = rng.normal(0.0, 0.10, n_visits)
    elif scenario == "gauss12":
        eps = rng.normal(0.0, 0.12, n_visits)
    elif scenario == "heavy":
        eps = rng.standard_t(5, n_visits) * 0.10 / np.sqrt(5.0 / 3.0)
    elif scenario == "ar1":
        eps = np.zeros(n_visits)
        e = rng.normal(0.0, 0.10)
        for t in range(n_visits):
            e = 0.3 * e + rng.normal(0.0, 0.10 * np.sqrt(1 - 0.09))
            eps[t] = e
    else:  # pragma: no cover
        raise ValueError(scenario)
    return np.exp(base + eps)


def _false_alarm_rate(n_patients, n_visits, scenario, seed, missing=0.0):
    rng = np.random.default_rng(seed)
    alarms = 0
    for _ in range(n_patients):
        days = _days(rng, n_visits)
        vals = _null_series(rng, n_visits, scenario)
        det = K2.SequentialDetector(alpha_pt=ALPHA)
        for d, v in zip(days, vals):
            miss = rng.random() < missing
            det.update(float(d), None if miss else float(v))
        alarms += int(det.alert)
    return alarms / n_patients


@pytest.mark.parametrize("scenario", ["gauss10", "gauss12", "heavy", "ar1"])
def test_patient_level_validity(scenario):
    _gate("K2-VALIDITY")
    rate = _false_alarm_rate(1500, 20, scenario, seed=1)
    assert rate <= ALPHA + 0.02, (
        f"{scenario}: patient-level false-alarm rate {rate:.3f} > {ALPHA + 0.02:.3f}"
    )


def test_anytime_validity_long_monitoring():
    _gate("K2-VALIDITY")
    rate = _false_alarm_rate(1000, 60, "gauss10", seed=2)
    assert rate <= ALPHA + 0.02, f"60-visit false-alarm rate {rate:.3f} grows with looks"


def test_missing_values_ok():
    _gate("K2-VALIDITY")
    rate = _false_alarm_rate(800, 20, "gauss10", seed=3, missing=0.3)
    assert rate <= ALPHA + 0.02


def test_alert_is_latched():
    rng = np.random.default_rng(4)
    det = K2.SequentialDetector(alpha_pt=ALPHA)
    days = _days(rng, 30)
    g = np.log(2) / 60.0
    vals = 18.0 * np.exp(g * np.maximum(0.0, days - days[5])) * np.exp(rng.normal(0, 0.1, 30))
    seen = False
    for d, v in zip(days, vals):
        det.update(float(d), float(v))
        if seen:
            assert det.alert, "alert reverted"
        seen = seen or det.alert
    assert seen, "strong growth never alerted"


def _power(doubling, seed, n=400, n_visits=20, onset_visit=5):
    rng = np.random.default_rng(seed)
    detected, delays = 0, []
    for _ in range(n):
        days = _days(rng, n_visits)
        onset = days[onset_visit]
        g = np.log(2) / doubling
        base = 18.0 * np.exp(rng.normal(0.0, 0.3))
        vals = base * np.exp(g * np.maximum(0.0, days - onset) + rng.normal(0.0, 0.10, n_visits))
        det = K2.SequentialDetector(alpha_pt=ALPHA)
        first = None
        for d, v in zip(days, vals):
            det.update(float(d), float(v))
            if det.alert and first is None:
                first = d
        if first is not None:
            detected += 1
            delays.append(first - onset)
    return detected / n, (float(np.median(delays)) if delays else np.inf)


def test_power_doubling_90():
    _gate("K2-POWER")
    frac, med = _power(90.0, seed=5)
    assert frac >= 0.75, f"detected only {frac:.2f}"
    assert med <= 240.0, f"median delay {med:.0f} days"


def test_power_doubling_60():
    _gate("K2-POWER")
    frac, _ = _power(60.0, seed=6)
    assert frac >= 0.85, f"detected only {frac:.2f}"
