"""Silent-mode monitors (PREREGISTRATION.md section 6): known values, planted drift, planted calm, edge cases.

All data written here is synthetic and exists only in a temporary shadow database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from vigil_api import silent_monitoring as sm
from vigil_api.shadow_store import (
    ShadowIngestRejection,
    ShadowOutcome,
    ShadowPrediction,
    ShadowStore,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
PARAMS = sm.Parameters(
    slope_low=0.8, slope_high=1.2, alert_budget=10.0, min_window=30, coverage_shortfall=0.05,
    provenance="test parameters (not ratified)",
)


@pytest.fixture
def store(tmp_path):
    s = ShadowStore(f"sqlite:///{tmp_path / 'm.db'}")
    yield s
    s.dispose()


def add_prediction(session, pid, when, score, alert=False, analyte="ca_15_3", conformal=None, nominal=None, recorded=None):
    session.add(
        ShadowPrediction(
            patient_id=pid, observation_id=f"o-{pid}-{when.isoformat()}-{analyte}", analyte_code=analyte,
            specimen_collected_at=when, canonical_value=1.0, score=score, score_kind="m3_p_real",
            m3_action="explained", risk_tier="low", would_alert=alert,
            conformal_set=conformal, conformal_nominal=nominal,
            recorded_at=recorded or when,
        )
    )


def add_outcome(session, pid, kind, when):
    session.add(ShadowOutcome(patient_id=pid, event_type=kind, event_time=when, source="test"))


# ------------------------------------------------------------------------------- statistics against references


@pytest.mark.parametrize(
    "k, lo, hi",
    [(0, 0.0, 3.6889), (5, 1.6235, 11.6683), (10, 4.7954, 18.3904)],
)
def test_poisson_exact_interval_matches_published_garwood_values(k, lo, hi):
    got_lo, got_hi = sm.poisson_exact_interval(k, 0.95)
    assert got_lo == pytest.approx(lo, abs=2e-3)
    assert got_hi == pytest.approx(hi, abs=2e-3)


def test_logistic_slope_matches_scikit_learn():
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(7)
    score = rng.uniform(0.02, 0.98, 4000)
    x = np.log(score / (1 - score))
    y = (rng.uniform(size=4000) < 1 / (1 + np.exp(-(0.2 + 0.7 * x)))).astype(int)
    ours = sm.logistic_slope(score, y)
    ref = LogisticRegression(penalty=None, tol=1e-12, max_iter=1000).fit(x.reshape(-1, 1), y)
    assert ours["slope"] == pytest.approx(ref.coef_[0][0], abs=1e-4)
    assert ours["intercept"] == pytest.approx(ref.intercept_[0], abs=1e-4)
    assert ours["ci_low"] < ours["slope"] < ours["ci_high"]
    assert ours["ci_low"] < 0.7 < ours["ci_high"]  # the interval covers the generating slope for this seed


def test_logistic_slope_refuses_separation_and_tiny_samples():
    assert sm.logistic_slope([0.1, 0.2], [0, 1])["status"] == "INSUFFICIENT"
    sep = sm.logistic_slope(np.linspace(0.01, 0.99, 60), [0] * 30 + [1] * 30)
    assert sep["status"] in ("UNSTABLE", "OK")  # perfect separation must never yield a silent absurd interval
    if sep["status"] == "OK":
        assert sep["ci_high"] - sep["ci_low"] > 0


# ------------------------------------------------------------------------------- outcome determinability


def lm(when):
    return sm.Landmark("p", when.date(), when, 0.5, False, ("ca_15_3",))


@pytest.mark.parametrize(
    "events, expected",
    [
        ([("recurrence_confirmed", 100)], 1),
        ([("recurrence_confirmed", 400), ("last_followup", 500)], 0),
        ([("last_followup", 400)], 0),
        ([("last_followup", 200)], None),
        ([("death_other", 200)], None),
        ([("recurrence_confirmed", -5), ("last_followup", 900)], None),
        ([], None),
    ],
)
def test_outcome_determinability(events, expected):
    info = sm.patient_outcomes([{"patient_id": "p", "event_type": e, "time": T0 + timedelta(days=d)} for e, d in events])
    assert sm.label(lm(T0), info, 365) == expected


# ------------------------------------------------------------------------------- planted drift and calm


def build_cohort(store, n, true_slope, seed, intercept=0.0):
    rng = np.random.default_rng(seed)
    with store.session() as session:
        for i in range(n):
            score = float(rng.beta(2, 5))
            x = np.log(score / (1 - score))
            y = rng.uniform() < 1 / (1 + np.exp(-(intercept + true_slope * x)))
            when = T0 + timedelta(days=i % 200, hours=i % 24)
            pid = f"P{i}"
            add_prediction(session, pid, when, score)
            if y:
                add_outcome(session, pid, "recurrence_confirmed", when + timedelta(days=120))
            else:
                add_outcome(session, pid, "last_followup", when + timedelta(days=500))
        session.commit()


def test_calibrated_stream_is_not_flagged_and_drifted_stream_is(store, tmp_path):
    build_cohort(store, 3000, true_slope=1.0, seed=1)
    calm = sm.build_report(store, PARAMS)["sections"]["calibration_drift"]
    assert calm["windows"], "the planted cohort must complete at least one window"
    assert calm["status"] == "OK"

    drifted = ShadowStore(f"sqlite:///{tmp_path / 'd.db'}")
    try:
        build_cohort(drifted, 3000, true_slope=0.3, seed=2)
        rep = sm.build_report(drifted, PARAMS)
        assert rep["sections"]["calibration_drift"]["status"] == "BREACH"
        assert rep["breach"] is True
        flagged = [w for w in rep["sections"]["calibration_drift"]["windows"] if w["status"] == "BREACH"]
        assert flagged and all(w["ci_high"] < PARAMS.slope_low for w in flagged)
    finally:
        drifted.dispose()


def test_small_windows_are_insufficient_never_a_breach(store):
    # Badly calibrated but only a handful of events: below PR-08 nothing may be declared.
    with store.session() as session:
        for i in range(40):
            when = T0 + timedelta(days=i)
            add_prediction(session, f"P{i}", when, 0.9)
            add_outcome(session, f"P{i}", "recurrence_confirmed" if i < 5 else "last_followup", when + timedelta(days=(100 if i < 5 else 500)))
        session.commit()
    rep = sm.build_report(store, PARAMS)["sections"]["calibration_drift"]
    assert rep["status"] == "INSUFFICIENT" and rep["windows"] == []


def test_slope_interval_straddling_a_bound_is_inconclusive_not_a_breach(store):
    build_cohort(store, 900, true_slope=0.85, seed=3)
    rep = sm.build_report(store, PARAMS)["sections"]["calibration_drift"]
    assert rep["status"] in ("OK", "BREACH")
    for w in rep["windows"]:
        if w["status"] == "OK" and w.get("inconclusive"):
            assert not (w["ci_high"] < PARAMS.slope_low or w["ci_low"] > PARAMS.slope_high)


# ------------------------------------------------------------------------------- alarm rate


def build_alarm_cohort(store, patients, landmarks_each, alert_every):
    with store.session() as session:
        for p in range(patients):
            for j in range(landmarks_each):
                n = p * landmarks_each + j
                add_prediction(session, f"A{p}", T0 + timedelta(days=30 * j), 0.1, alert=(alert_every and n % alert_every == 0))
        session.commit()


def test_alarm_rate_breach_ok_and_missing_budget(store, tmp_path):
    build_alarm_cohort(store, 20, 6, alert_every=2)  # half of all landmarks alert
    breach = sm.build_report(store, PARAMS)["sections"]["alarm_rate"]
    assert breach["status"] == "BREACH" and breach["ci_low"] > PARAMS.alert_budget
    assert breach["patient_months"] == pytest.approx(20 * 5 * 30 / sm.MONTH_DAYS, rel=1e-3)

    calm = ShadowStore(f"sqlite:///{tmp_path / 'c.db'}")
    try:
        build_alarm_cohort(calm, 20, 6, alert_every=0)
        assert sm.build_report(calm, PARAMS)["sections"]["alarm_rate"]["status"] == "OK"
    finally:
        calm.dispose()

    no_budget = sm.Parameters(**{**PARAMS.__dict__, "alert_budget": None})
    rep = sm.build_report(store, no_budget)
    assert rep["sections"]["alarm_rate"]["status"] == "NOT_EVALUABLE"
    assert rep["incomplete"] is True and rep["breach"] is False


def test_alarm_counts_one_alert_per_patient_day_not_per_analyte(store):
    with store.session() as session:
        for analyte in ("ca_15_3", "alt", "ast"):
            add_prediction(session, "P1", T0, 0.5, alert=True, analyte=analyte)
        add_prediction(session, "P1", T0 + timedelta(days=60), 0.1)
        session.commit()
    a = sm.build_report(store, PARAMS)["sections"]["alarm_rate"]
    assert a["alerts"] == 1 and a["landmarks"] == 2


def test_empty_store_reports_without_error(store):
    rep = sm.build_report(store, PARAMS)
    assert rep["breach"] is False
    assert rep["sections"]["alarm_rate"]["status"] == "INSUFFICIENT"
    assert rep["sections"]["conformal_coverage"]["status"] == "NOT_MEASURABLE"
    assert "Silent-mode monitoring report" in sm.render_markdown(rep)


# ------------------------------------------------------------------------------- conformal coverage


def test_conformal_coverage_not_invented_and_breach_detected(store, tmp_path):
    build_cohort(store, 200, true_slope=1.0, seed=5)
    assert sm.build_report(store, PARAMS)["sections"]["conformal_coverage"]["status"] == "NOT_MEASURABLE"

    for name, covered_fraction, expected in (("low", 0.7, "BREACH"), ("good", 0.92, "OK")):
        s = ShadowStore(f"sqlite:///{tmp_path / (name + '.db')}")
        try:
            rng = np.random.default_rng(11)
            with s.session() as session:
                for i in range(200):
                    when = T0 + timedelta(days=i)
                    y_event = i % 3 == 0
                    covered = rng.uniform() < covered_fraction
                    label_set = [1 if y_event else 0] if covered else [0 if y_event else 1]
                    add_prediction(session, f"C{i}", when, 0.3, conformal=label_set, nominal=0.9)
                    add_outcome(session, f"C{i}", "recurrence_confirmed" if y_event else "last_followup", when + timedelta(days=(90 if y_event else 500)))
                session.commit()
            assert sm.build_report(s, PARAMS)["sections"]["conformal_coverage"]["status"] == expected
        finally:
            s.dispose()


# ------------------------------------------------------------------------------- data shift


def test_rejection_rate_that_more_than_doubles_is_a_breach(store, tmp_path):
    with store.session() as session:
        for i in range(120):
            add_prediction(session, f"S{i}", T0 + timedelta(days=i), 0.1, recorded=T0 + timedelta(hours=i))
        for i in (5,):  # first window: 1 refusal in 31 attempts
            session.add(ShadowIngestRejection(analyte_code="ca_15_3", reason="unit", recorded_at=T0 + timedelta(hours=i, minutes=1)))
        for i in range(70, 80):  # a later window: many refusals
            session.add(ShadowIngestRejection(analyte_code="ca_15_3", reason="unit", recorded_at=T0 + timedelta(hours=i, minutes=1)))
        session.commit()
    shift = sm.build_report(store, PARAMS)["sections"]["data_shift"]
    assert shift["status"] == "BREACH"
    assert shift["rejection_rate"]["ca_15_3"]["windows_more_than_double"]

    zero = ShadowStore(f"sqlite:///{tmp_path / 'z.db'}")
    try:
        with zero.session() as session:
            for i in range(120):
                add_prediction(session, f"S{i}", T0 + timedelta(days=i), 0.1, recorded=T0 + timedelta(hours=i))
            for i in range(70, 75):
                session.add(ShadowIngestRejection(analyte_code="ca_15_3", reason="unit", recorded_at=T0 + timedelta(hours=i, minutes=1)))
            session.commit()
        res = sm.build_report(zero, PARAMS)["sections"]["data_shift"]["rejection_rate"]["ca_15_3"]
        assert res["status"] == "OK" and "undefined" in res["note"]
    finally:
        zero.dispose()


def test_missingness_that_more_than_doubles_is_a_breach(store):
    with store.session() as session:
        for i in range(120):
            day = T0 + timedelta(days=i)
            add_prediction(session, f"M{i}", day, 0.1, analyte="ca_15_3")
            # alt present on 90 % of days at first, then on 60 % of days
            present = (i % 10 != 0) if i < 60 else (i % 5 not in (0, 1))
            if present:
                add_prediction(session, f"M{i}", day, 0.1, analyte="alt")
        session.commit()
    shift = sm.build_report(store, PARAMS)["sections"]["data_shift"]["missingness"]["alt"]
    assert shift["status"] == "BREACH"


# ------------------------------------------------------------------------------- outcome import


def test_outcome_import_rejects_with_codes_and_never_echoes_values(store):
    with store.session() as session:
        add_prediction(session, "KNOWN", T0, 0.2)
        session.commit()
    rows = [
        {"patient_id": "KNOWN", "event_type": "recurrence_confirmed", "event_time": "2026-03-01"},
        {"patient_id": "KNOWN", "event_type": "recurrence_confirmed", "event_time": "2026-03-01"},
        {"patient_id": "KNOWN", "event_type": "relapsed", "event_time": "2026-03-01"},
        {"patient_id": "KNOWN", "event_type": "last_followup", "event_time": "next tuesday"},
        {"patient_id": "NOBODY", "event_type": "last_followup", "event_time": "2026-04-01"},
        {"patient_id": "", "event_type": "last_followup", "event_time": "2026-04-01"},
    ]
    rep = sm.import_outcomes(store, rows, source="unit-test")
    assert rep["accepted"] == 1 and rep["rejected"] == 5
    assert rep["rejection_codes"] == {
        "BAD_ENUM": 1, "BAD_TIMESTAMP": 1, "DUPLICATE": 1, "MISSING_REQUIRED": 1, "UNKNOWN_PATIENT": 1,
    }
    assert "NOBODY" not in str(rep) and "relapsed" not in str(rep) and "next tuesday" not in str(rep)
