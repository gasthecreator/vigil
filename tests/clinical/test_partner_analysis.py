"""Partner analysis: partition, landmarks, leakage attack, metrics with known answers, null behaviour, CLI guards.

Cohorts are SYNTHETIC (scripts/make_dryrun_cohort.py). Tests that run the whole pipeline assert plumbing and null
behaviour, never performance.
"""

from __future__ import annotations

import copy
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

warnings.filterwarnings("ignore", category=FutureWarning)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_prereg_freeze as gate  # noqa: E402
import make_dryrun_cohort as gen  # noqa: E402
import partner_analysis as pa  # noqa: E402
import run_partner_evaluation as cli  # noqa: E402
from contracts.partner import ingest_path  # noqa: E402

KEY = b"unit-test-partition-key-0123456789"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("I", "STAGE I"),
        ("IIA", "STAGE II"),
        ("IIB", "STAGE II"),
        ("IIIA", "STAGE III"),
        ("IIIB", "STAGE III"),
        ("IIIC", "STAGE III"),
    ],
)
def test_stage_mapping_preserves_contract_stage_group(raw, expected):
    assert pa._stage(raw) == expected


@pytest.mark.parametrize("raw", ["IV", "Stage IV", "IIX", "", "unknown"])
def test_stage_mapping_rejects_out_of_contract_values(raw):
    with pytest.raises(ValueError, match="unsupported AJCC stage_ajcc"):
        pa._stage(raw)


# ------------------------------------------------------------------------------------------------ partition
def test_partition_is_deterministic_keyed_and_balanced():
    ids = [f"P{i:05d}" for i in range(4000)]
    a = [pa.assign_split(i, KEY) for i in ids]
    assert a == [pa.assign_split(i, KEY) for i in reversed(ids)][::-1]  # order-independent
    assert 0.46 < a.count("dev") / len(a) < 0.54
    b = [pa.assign_split(i, KEY + b"x") for i in ids]
    assert (
        0.35 < np.mean([x != y for x, y in zip(a, b)]) < 0.65
    )  # a different key gives an unrelated split


def test_partition_refuses_a_short_key():
    with pytest.raises(ValueError):
        pa.assign_split("P1", b"short")


# ------------------------------------------------------------------------------------------------ landmarks
def _tables(patients):
    """patients: list of dict(pid, follow, index, rec_day or None, vital, labs=[(day, ca)])."""
    t = {"patients": [], "baseline_profile": [], "lab_observations": [], "clinical_outcomes": []}
    for p in patients:
        t["patients"].append(
            {
                "patient_id": p["pid"],
                "age_at_diagnosis": 50,
                "menopausal_status": "POST",
                "vital_status": p.get("vital", "ALIVE"),
                "days_to_last_followup": p["follow"],
                "days_to_death": p.get("death_day"),
                "index_day": p["index"],
            }
        )
        t["baseline_profile"].append(
            {
                "patient_id": p["pid"],
                "histological_type": "IDC",
                "tumor_grade": 2,
                "stage_ajcc": "IIA",
                "er_status": "POSITIVE",
                "pr_status": "POSITIVE",
                "her2_status": "NEGATIVE",
                "has_hypertension": False,
                "renal_history": False,
                "surgery_type": "MRM",
                "chemotherapy_given": True,
                "endocrine_therapy": True,
                "radiotherapy_given": True,
            }
        )
        t["clinical_outcomes"].append(
            {
                "patient_id": p["pid"],
                "recurrence_confirmed": p["rec_day"] is not None,
                "recurrence_day": p["rec_day"],
                "dismissed_prior_signal": False,
                "restaging_imaging_done": None,
            }
        )
        for day, ca in p["labs"]:
            t["lab_observations"].append(
                {
                    "patient_id": p["pid"],
                    "observation_day": day,
                    "analyte": "ca_15_3",
                    "value_canonical": ca,
                }
            )
    return t


def test_landmark_times_events_and_exclusions_on_a_hand_worked_cohort():
    labs = [(100, 20.0), (190, 22.0), (280, 25.0), (370, 30.0)]
    tables = _tables(
        [
            {
                "pid": "A",
                "follow": 1000,
                "index": 90,
                "rec_day": 600,
                "labs": labs + [(50, 99.0)],
            },  # day 50 is before the index
            {"pid": "B", "follow": 800, "index": 90, "rec_day": None, "labs": labs},
            {
                "pid": "C",
                "follow": 800,
                "index": 90,
                "rec_day": None,
                "labs": [(100, 20.0)],
            },  # one draw: excluded
            {
                "pid": "D",
                "follow": 800,
                "index": 90,
                "rec_day": 150,
                "labs": labs,
            },  # recurred before the 2nd draw
        ]
    )
    lm = pa.build_landmarks(tables, ["A", "B", "C", "D"])
    assert set(lm.X["patient_id"]) == {"A", "B"}
    assert lm.counts["patients_with_a_landmark"] == 2 and lm.counts["cohort_complete_case"] == 4
    a = lm.X["patient_id"].to_numpy() == "A"
    days = lm.X["eval_day"].to_numpy()[a]
    assert list(days) == [190, 280, 370]  # 2nd draw onward; the pre-index draw never counts
    assert list(lm.T[a]) == [600 - 190, 600 - 280, 600 - 370] and list(lm.E[a]) == [1, 1, 1]
    assert list(lm.y[a]) == [
        0,
        1,
        1,
    ]  # 410 days to recurrence is outside the 365-day horizon; 320 and 230 are inside
    b = lm.X["patient_id"].to_numpy() == "B"
    assert list(lm.E[b]) == [0, 0, 0] and list(lm.T[b]) == [
        800 - 190,
        800 - 280,
        800 - 370,
    ]  # censored at follow-up
    assert lm.first.sum() == 2 and lm.end_day == {"A": 600.0, "B": 800.0}
    assert (
        "history_length" in lm.X.columns
        and (lm.X.loc[a, "history_length"].to_numpy() == [2, 3, 4]).all()
    )


def test_death_from_another_cause_is_a_competing_event_and_known_control():
    labs = [(100, 20.0), (190, 22.0), (280, 25.0)]
    lm = pa.build_landmarks(
        _tables(
            [
                {
                    "pid": "A",
                    "follow": 300,
                    "index": 90,
                    "rec_day": None,
                    "vital": "DEAD_OTHER",
                    "death_day": 300,
                    "labs": labs,
                }
            ]
        ),
        ["A"],
    )
    assert list(lm.E) == [2, 2] and list(lm.T) == [300 - 190, 300 - 280]
    assert list(lm.y) == [0.0, 0.0]
    assert lm.end_day == {"A": 300.0}
    assert (pa.compute_ipcw_weights(lm.T, lm.E, pa.HORIZON) > 0).all()


def test_partner_adapter_refuses_to_infer_death_day_from_last_followup():
    tables = _tables(
        [
            {
                "pid": "A",
                "follow": 300,
                "index": 90,
                "rec_day": None,
                "vital": "DEAD_OTHER",
                "labs": [(100, 20.0), (190, 22.0), (280, 25.0)],
            }
        ]
    )
    with pytest.raises(ValueError, match="explicit days_to_death"):
        pa.to_vigil_frames(tables, ["A"])


def test_administrative_censoring_before_horizon_keeps_outcome_unknown():
    lm = pa.build_landmarks(
        _tables(
            [
                {
                    "pid": "A",
                    "follow": 300,
                    "index": 90,
                    "rec_day": None,
                    "labs": [(100, 20.0), (190, 22.0), (280, 25.0)],
                }
            ]
        ),
        ["A"],
    )
    assert list(lm.E) == [0, 0]
    assert np.isnan(lm.y).all()
    assert (pa.compute_ipcw_weights(lm.T, lm.E, pa.HORIZON) == 0).all()


def test_recurrence_before_competing_death_remains_the_event_of_interest():
    labs = [(100, 20.0), (190, 22.0), (280, 25.0)]
    lm = pa.build_landmarks(
        _tables(
            [
                {
                    "pid": "A",
                    "follow": 400,
                    "index": 90,
                    "rec_day": 350,
                    "vital": "DEAD_OTHER",
                    "death_day": 400,
                    "labs": labs,
                }
            ]
        ),
        ["A"],
    )
    assert list(lm.E) == [1, 1]
    assert list(lm.T) == [350 - 190, 350 - 280]
    assert list(lm.y) == [1.0, 1.0]
    assert lm.end_day == {"A": 350.0}


# ------------------------------------------------------------------------------------------------ leakage attack
def test_features_at_a_landmark_do_not_change_when_the_future_changes(tmp_path):
    gen.generate(tmp_path, 60, "signal", 7)
    res = ingest_path(tmp_path)
    base = pa.build_landmarks(res.tables, res.cohort_ids)
    pid = base.X["patient_id"].iloc[0]
    days = sorted(
        r["observation_day"] for r in res.tables["lab_observations"] if r["patient_id"] == pid
    )
    cut = days[len(days) // 2]
    attacked = copy.deepcopy(res.tables)
    for r in attacked["lab_observations"]:
        if r["patient_id"] == pid and r["observation_day"] > cut:
            r["value_canonical"] *= 1000.0  # an enormous fake future
    atk = pa.build_landmarks(attacked, res.cohort_ids)
    cols = [c for c in base.X.columns if c != "patient_id"]
    b = base.X[(base.X.patient_id == pid) & (base.X.eval_day <= cut)][cols].reset_index(drop=True)
    a = atk.X[(atk.X.patient_id == pid) & (atk.X.eval_day <= cut)][cols].reset_index(drop=True)
    assert len(b) >= 2 and b.equals(a)
    later_b = base.X[(base.X.patient_id == pid) & (base.X.eval_day > cut)][
        "ca_15_3_curr"
    ].to_numpy()
    later_a = atk.X[(atk.X.patient_id == pid) & (atk.X.eval_day > cut)]["ca_15_3_curr"].to_numpy()
    assert (
        len(later_b) and (later_a > later_b * 100).all()
    )  # the attack did change what it was meant to change


def test_pre_index_laboratory_values_are_not_features():
    labs = [(100, 20.0), (190, 22.0)]
    plain = pa.build_landmarks(
        _tables([{"pid": "A", "follow": 900, "index": 90, "rec_day": None, "labs": labs}]), ["A"]
    )
    with_pre = pa.build_landmarks(
        _tables(
            [
                {
                    "pid": "A",
                    "follow": 900,
                    "index": 90,
                    "rec_day": None,
                    "labs": labs + [(10, 5000.0)],
                }
            ]
        ),
        ["A"],
    )
    assert plain.X.drop(columns=[]).equals(with_pre.X)


# ------------------------------------------------------------------------------------------------ metrics with known answers
def test_alert_burden_counts_every_alert_and_does_not_reward_always_on():
    p = np.array([0.1, 0.9, 0.9, 0.2, 0.8, 0.9, 0.9, 0.9])
    pid = np.array(["a"] * 5 + ["b"] * 3)
    day = np.array([0, 30, 60, 90, 120, 0, 30, 60], float)
    al, mo = pa.alert_burden(p, 0.5, pid, day, {"a": 120.0, "b": 60.0})
    assert al == {"a": 3, "b": 3}
    assert mo["a"] == pytest.approx(120 / pa.DAYS_PER_MONTH) and mo["b"] == pytest.approx(
        60 / pa.DAYS_PER_MONTH
    )
    always, _ = pa.alert_burden(np.ones(8), 0.0, pid, day, {"a": 120.0, "b": 60.0})
    assert always == {"a": 5, "b": 3}  # one alert per landmark, not one per patient
    assert pa.rate_per_100_months(al, mo) == pytest.approx(
        100 * 6 / ((120 + 60) / pa.DAYS_PER_MONTH)
    )


def _simulated_outcomes(p, rng, censor_rate=0.0):
    ev = rng.random(len(p)) < p
    T = np.where(
        ev, 100.0, 2000.0
    )  # events at day 100 (inside the horizon), others observed past it
    E = ev.astype(int)
    if censor_rate:
        c = rng.random(len(p)) < censor_rate
        T = np.where(c & ~ev, 50.0, T)  # random early censoring of non-events
    return T, E


def test_calibration_slope_is_one_for_calibrated_predictions_and_half_for_overconfident_ones():
    rng = np.random.default_rng(3)
    p = rng.beta(2, 5, 20000)
    T, E = _simulated_outcomes(p, rng)
    assert pa.calibration_slope(p, T, E) == pytest.approx(1.0, abs=0.08)
    over = 1 / (1 + np.exp(-2.0 * pa._logit(p)))
    assert pa.calibration_slope(over, T, E) == pytest.approx(0.5, abs=0.06)
    Tc, Ec = _simulated_outcomes(p, rng, censor_rate=0.3)
    assert pa.calibration_slope(p, Tc, Ec) == pytest.approx(
        1.0, abs=0.12
    )  # IPCW keeps it unbiased under random censoring


def test_ipcw_auc_is_one_for_a_perfect_score_and_half_for_noise():
    rng = np.random.default_rng(5)
    p = rng.random(4000)
    T, E = _simulated_outcomes(p, rng)
    assert pa.ipcw_auc(E.astype(float) + 0.01 * rng.random(len(E)), T, E) == pytest.approx(
        1.0, abs=1e-9
    )
    assert pa.ipcw_auc(rng.random(len(E)), T, E) == pytest.approx(0.5, abs=0.04)


def test_holm_adjustment():
    r = pa.holm({"C1": 0.01, "C2": 0.02, "C3": 0.03})
    assert [round(r[k]["p_holm"], 3) for k in ("C1", "C2", "C3")] == [0.03, 0.04, 0.04] and all(
        v["reject"] for v in r.values()
    )
    r2 = pa.holm({"C1": 0.02, "C2": 0.5, "C3": 0.9})
    assert [round(r2[k]["p_holm"], 3) for k in ("C1", "C2", "C3")] == [0.06, 1.0, 1.0] and not any(
        v["reject"] for v in r2.values()
    )


def test_begg_greenes_bounds_move_with_the_assumption():
    p = np.array([0.9, 0.9, 0.1, 0.1, 0.9, 0.9])
    y = np.array([1, 0, 0, 1, 0, 0])
    v = np.array([1, 1, 1, 1, 0, 0], bool)
    rows = pa.begg_greenes_sensitivity(p, y, v, 0.5, (0.0, 0.5, 1.0))
    # verified: tp=1 fp=1 tn=1 fn=1; both unverified patients are predicted positive
    assert [r["sensitivity"] for r in rows] == pytest.approx([1 / 2, 2 / 3, 3 / 4])
    assert [r["specificity"] for r in rows] == pytest.approx([1 / 4, 1 / 3, 1 / 2])


def test_verification_propensity_is_fit_on_development_with_explicit_missingness_features():
    n = 40
    patients = pd.DataFrame(
        {
            "patient_id": [f"DEV-{i}" for i in range(n)],
            "restaging_imaging_done": [i % 2 == 0 for i in range(n)],
        }
    )
    X = pd.DataFrame(
        {
            "patient_id": patients["patient_id"],
            "eval_day": np.full(n, 180.0),
            "age": np.linspace(30.0, 70.0, n),
            "ca_15_3_curr": np.linspace(10.0, 80.0, n),
            "history_length": np.full(n, 2.0),
        }
    )
    X.loc[[3, 11, 27], "ca_15_3_curr"] = np.nan
    dev = pa.Landmarks(
        X=X,
        y=np.tile([0, 1], n // 2),
        T=np.full(n, 365.0),
        E=np.tile([0, 1], n // 2),
        first=np.ones(n, dtype=bool),
        end_day={pid: 545.0 for pid in patients["patient_id"]},
        patients=patients,
    )

    model, medians, issue = pa._fit_verification_propensity(dev)
    assert issue is None and model is not None and medians is not None
    assert medians[1] == pytest.approx(float(np.nanmedian(X["ca_15_3_curr"])))
    matrix, returned_medians = pa._verification_feature_matrix(X, medians)
    assert matrix.shape == (n, 6)
    assert matrix[3, 4] == 1.0  # CA 15-3 missingness is explicit, not encoded as zero
    assert np.array_equal(returned_medians, medians)

    held_out = X.copy()
    held_out["ca_15_3_curr"] = 1_000_000.0
    _, held_out_medians = pa._verification_feature_matrix(held_out, medians)
    assert np.array_equal(held_out_medians, medians)  # test patients cannot refit imputation


def test_verification_propensity_fails_closed_without_complete_development_labels():
    n = 20
    patients = pd.DataFrame(
        {
            "patient_id": [f"DEV-{i}" for i in range(n)],
            "restaging_imaging_done": [None] * n,
        }
    )
    X = pd.DataFrame(
        {
            "patient_id": patients["patient_id"],
            "age": np.linspace(30.0, 70.0, n),
            "ca_15_3_curr": np.linspace(10.0, 80.0, n),
            "history_length": np.full(n, 2.0),
        }
    )
    dev = pa.Landmarks(
        X=X,
        y=np.tile([0, 1], n // 2),
        T=np.full(n, 365.0),
        E=np.tile([0, 1], n // 2),
        first=np.ones(n, dtype=bool),
        end_day={pid: 545.0 for pid in patients["patient_id"]},
        patients=patients,
    )
    model, medians, issue = pa._fit_verification_propensity(dev)
    assert model is None and medians is None
    assert issue == "development verification status is incomplete or non-binary"


def test_out_of_fold_censoring_weights_are_fit_inside_patient_folds(monkeypatch):
    n = 10
    patients = np.array([f"P{i:02d}" for i in range(n)])
    events = np.tile([1, 2], n // 2)
    times = np.tile([100.0, 200.0], n // 2)
    labels = (events == 1).astype(float)
    dev = pa.Landmarks(
        X=pd.DataFrame(
            {
                "patient_id": patients,
                "eval_day": np.zeros(n),
                "ca_15_3_curr": np.linspace(10.0, 80.0, n),
            }
        ),
        y=labels,
        T=times,
        E=events,
        first=np.ones(n, dtype=bool),
        end_day={patient: 365.0 for patient in patients},
        patients=pd.DataFrame({"patient_id": patients}),
    )
    original = pa.compute_ipcw_weights
    input_sizes = []
    b1_training_ids = []
    b2_training_ids = []
    base_b1, base_b2 = pa.SingleThresholdBaseline, pa.VelocityBaseline

    class SpyB1(base_b1):
        def fit(self, X, y, sample_weight=None, **kwargs):
            b1_training_ids.append(set(X["patient_id"]))
            return super().fit(X, y, sample_weight=sample_weight, **kwargs)

    class SpyB2(base_b2):
        def fit(self, X, y, sample_weight=None, **kwargs):
            b2_training_ids.append(set(X["patient_id"]))
            return super().fit(X, y, sample_weight=sample_weight, **kwargs)

    def record_fold_only_weights(follow_up_times, event_indicators, horizon_time):
        input_sizes.append(len(follow_up_times))
        return original(follow_up_times, event_indicators, horizon_time)

    monkeypatch.setattr(pa, "compute_ipcw_weights", record_fold_only_weights)
    monkeypatch.setattr(pa, "SingleThresholdBaseline", SpyB1)
    monkeypatch.setattr(pa, "VelocityBaseline", SpyB2)
    predictions = pa._out_of_fold(dev, horizon=365.0, folds=5)

    assert input_sizes == [8] * 5
    from sklearn.model_selection import GroupKFold

    expected_training_ids = [
        set(patients[train])
        for train, _test in GroupKFold(n_splits=5).split(dev.X, groups=patients)
    ]
    assert b1_training_ids == b2_training_ids == expected_training_ids
    assert set(predictions) == {
        "B1_SINGLE_THRESHOLD",
        "B2_VELOCITY_RULE",
        "B3_REGULARIZED_LOGISTIC_HORIZON",
        "B4_GRADIENT_BOOSTING_HORIZON",
    }
    assert all(np.isfinite(scores).all() for scores in predictions.values())


# ------------------------------------------------------------------------------------------------ whole pipeline on synthetic cohorts
@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    out = {}
    for mode in ("signal", "null"):
        d = tmp_path_factory.mktemp(mode)
        gen.generate(d, 500, mode, 20261018)
        res = ingest_path(d)
        lm = pa.build_landmarks(res.tables, res.cohort_ids)
        split = {p: pa.assign_split(p, KEY) for p in lm.patients["patient_id"]}
        dev = lm.subset([p for p, s in split.items() if s == "dev"])
        test = lm.subset([p for p, s in split.items() if s == "test"])
        plan = pa.fit_on_development(dev, alert_budget=5.0)
        out[mode] = (dev, test, plan)
    return out


PARAMS = {"PR-01": 0.8, "PR-02": 1.2, "PR-03": 0.0, "PR-04": 5.0, "PR-05": 20.0, "PR-06": 5.0}


def test_dev_and_test_share_no_patient(runs):
    dev, test, _ = runs["signal"]
    assert not (set(dev.X["patient_id"]) & set(test.X["patient_id"]))


def test_the_operating_point_is_chosen_on_development_to_meet_the_budget(runs):
    _, _, plan = runs["signal"]
    assert plan.dev_alert_rate <= PARAMS["PR-04"] + 1e-9 and 0.0 < plan.threshold < 1.0


def test_confirmatory_results_are_reproducible_and_null_data_meet_no_criterion(runs):
    _, test, plan = runs["null"]
    a = pa.confirmatory(test, plan, PARAMS, n_boot=100, seed=11)
    b = pa.confirmatory(test, plan, PARAMS, n_boot=100, seed=11)
    assert a == b
    assert (
        not a["C1"]["met"] and not a["C2"]["met"]
    )  # no signal: calibration and discrimination claims must fail
    lo, hi = a["C2"]["ci95"]
    assert (
        lo < 0.0 < hi or lo <= 0.0 + 0.05
    )  # the AUC difference against the comparator is indistinguishable from zero


def test_candidate_finds_signal_that_is_present_and_not_signal_that_is_absent(runs):
    def cand_auc(mode):
        _, test, plan = runs[mode]
        f = test.first
        return pa.ipcw_auc(plan.candidate_risk(test.X[f]), test.T[f], test.E[f])

    assert cand_auc("signal") > 0.62
    assert 0.40 < cand_auc("null") < 0.60
    assert cand_auc("signal") > cand_auc("null")


def test_secondary_analyses_apply_the_small_cell_and_minimum_event_rules(runs):
    _, test, plan = runs["signal"]
    s = pa.secondary(test, plan, {**PARAMS, "PR-05": 10_000.0}, n_boot=20, seed=1)
    groups = s["subgroups"]["groups"]
    assert groups and all(
        g["result"] == "insufficient data" for g in groups.values()
    )  # nothing reaches 10 000 events
    assert s["subgroups"]["worst_group"] is None
    assert "verification_bias" in s and "decision_curve" in s and "lead_time" in s
    assert "not_run" in s["decision_curve"]
    assert s["m10_aggregate"]["small_cell_threshold"] == 5


def test_secondary_uses_only_the_explicit_dca_threshold_grid(runs):
    _, test, plan = runs["signal"]
    thresholds = np.asarray([0.1, 0.25, 0.4])
    s = pa.secondary(test, plan, PARAMS, n_boot=5, seed=7, dca_thresholds=thresholds)
    assert s["decision_curve"]["thresholds"] == thresholds.tolist()
    assert len(s["decision_curve"]["net_benefit_model"]) == len(thresholds)


def test_too_few_development_events_is_an_explicit_not_run(runs):
    dev, _, _ = runs["signal"]
    with pytest.raises(pa.InsufficientData):
        pa.fit_on_development(dev, 5.0, min_events=10_000)


# ------------------------------------------------------------------------------------------------ command line guards
def _write_freeze(tmp_path, monkeypatch, budget="3.0"):
    text = gate.PREREG.read_text(encoding="utf-8")
    import hashlib

    params = gate.parameters(text)
    rat = [
        {
            "id": k,
            "value": (budget if k == "PR-04" else "[0.05, 0.1, 0.2]" if k == "PR-10" else v),
            "ratifier": "test",
            "date": "2026-01-01",
        }
        for k, v in params.items()
    ]
    f = tmp_path / "freeze.json"
    f.write_text(
        json.dumps(
            {
                "prereg_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "analysis_spec_sha256": hashlib.sha256(
                    gate.SPEC.read_text(encoding="utf-8").encode()
                ).hexdigest(),
                "bootstrap_seed": 4242,
                "partition_key_id": "KEY-TEST",
                "ratifications": rat,
            }
        )
    )
    monkeypatch.setattr(gate, "FREEZE", f)


def test_real_data_path_is_blocked_without_a_freeze_and_dry_run_needs_the_marker(
    tmp_path, monkeypatch, capsys
):
    d = tmp_path / "cohort"
    gen.generate(d, 40, "signal", 1)
    assert cli.main([str(d), "--out", str(tmp_path / "o1")]) == 4  # unfrozen real run
    assert "NOT FROZEN" in capsys.readouterr().err
    assert (
        cli.main(
            [str(d), "--out", str(tmp_path / "o2"), "--synthetic-dry-run", "--alert-budget", "5"]
        )
        == 4
    )  # no SYNTHETIC marker
    assert "SYNTHETIC marker" in capsys.readouterr().err
    assert (
        not (tmp_path / "o1" / "report.json").exists()
        and not (tmp_path / "o2" / "report.json").exists()
    )
    _write_freeze(tmp_path, monkeypatch)
    monkeypatch.setenv("VIGIL_PARTITION_KEY", "short")
    assert (
        cli.main([str(d), "--out", str(tmp_path / "o3")]) == 4
    )  # frozen, but no usable partition key
    monkeypatch.setenv("VIGIL_PARTITION_KEY", KEY.decode())
    assert (
        cli.main([str(d), "--out", str(tmp_path / "o4"), "--n-boot", "5"]) == 4
    )  # dry-run option on a real run
    assert cli.main([str(d), "--out", str(tmp_path / "o5"), "--alert-budget", "9"]) == 4


def test_dry_run_end_to_end_logs_the_test_split_opening_and_refuses_a_second_one(tmp_path, capsys):
    d = tmp_path / "cohort"
    gen.generate(d, 300, "signal", 3)
    (d / "SYNTHETIC").write_text("invented data\n")
    out = tmp_path / "out"
    argv = [
        str(d),
        "--out",
        str(out),
        "--synthetic-dry-run",
        "--alert-budget",
        "5",
        "--n-boot",
        "20",
    ]
    assert cli.main(argv) == 0
    rep = json.loads((out / "report.json").read_text())
    assert (
        rep["tier"].startswith("SYNTHETIC DRY RUN")
        and rep["status"] == "COMPLETED"
        and rep["bootstrap_resamples"] == 20
    )
    assert "NOT A RESULT" in (out / "REPORT.md").read_text()
    log = (out / "frozen_test_access_log.jsonl").read_text().strip().splitlines()
    assert len(log) == 1 and json.loads(log[0])["access_type"] == "partner_confirmatory_evaluation"
    assert cli.main(argv) == 5  # second opening refused
    assert len((out / "frozen_test_access_log.jsonl").read_text().strip().splitlines()) == 1
    assert cli.main(argv + ["--acknowledge-deviation"]) == 0
    dev_rep = json.loads((out / "report.json").read_text())
    assert any("protocol deviation" in x for x in dev_rep["deviations"])
    assert len((out / "frozen_test_access_log.jsonl").read_text().strip().splitlines()) == 2


def test_real_path_runs_with_ratified_values_the_ratified_seed_and_2000_resamples(
    tmp_path, monkeypatch
):
    d = tmp_path / "cohort"
    gen.generate(d, 300, "signal", 3)
    _write_freeze(tmp_path, monkeypatch, budget="3.0")
    monkeypatch.setenv("VIGIL_PARTITION_KEY", KEY.decode())
    out = tmp_path / "out"
    assert cli.main([str(d), "--out", str(out)]) == 0
    rep = json.loads((out / "report.json").read_text())
    assert (
        rep["tier"] == "T-R retrospective partner cohort"
        and "ratified" in rep["parameter_provenance"]
    )
    assert (
        rep["parameters"]["PR-04"] == 3.0
        and rep["bootstrap_seed"] == 4242
        and rep["partition_key_id"] == "KEY-TEST"
    )
    assert rep["dca_thresholds"] == [0.05, 0.1, 0.2]
    if rep["status"] == "COMPLETED":
        assert rep["secondary"]["decision_curve"]["thresholds"] == rep["dca_thresholds"]
    assert rep["bootstrap_resamples"] == 2000
    if rep["status"] == "COMPLETED":
        assert rep["confirmatory"]["seed"] == 4242


def test_a_messy_extract_over_the_stop_rate_stops_the_analysis(tmp_path):
    out = tmp_path / "o"
    fixture = ROOT / "data" / "fixtures" / "partner_messy"
    assert (
        cli.main(
            [
                str(fixture),
                "--out",
                str(out),
                "--synthetic-dry-run",
                "--alert-budget",
                "5",
                "--n-boot",
                "5",
            ]
        )
        == 2
    )
    rep = json.loads((out / "report.json").read_text())
    assert (
        rep["status"] == "STOPPED"
        and "confirmatory" not in rep
        and not (out / "frozen_test_access_log.jsonl").exists()
    )


def test_committed_dry_run_reports_reproduce_byte_for_byte():
    """Result files are written only by their script; this re-runs it and diffs against the committed files.
    (Byte-exact on the platform that wrote them; elsewhere within the documented float tolerance, see
    scripts/run_partner_dry_run.py. The name is kept for the CI history.)"""
    import run_partner_dry_run as dry

    assert dry.main(["--check"]) == 0


def test_dry_run_tolerance_accepts_float_drift_but_not_changed_facts(tmp_path):
    import run_partner_dry_run as dry

    def pair(committed: str, rebuilt: str, suffix: str):
        a, b = tmp_path / f"a{suffix}", tmp_path / f"b{suffix}"
        a.write_text(committed, encoding="utf-8")
        b.write_text(rebuilt, encoding="utf-8")
        return dry.agree(a, b)

    base = '{"slope": 0.374, "n": 49, "met": false, "name": "C1", "ci": [1.0, 2.0]}'
    assert pair(base, base, ".json")
    assert pair(
        base, base.replace("0.374", "0.380"), ".json"
    )  # the drift seen between macOS and Linux
    assert not pair(base, base.replace("0.374", "0.600"), ".json")  # a different number
    assert not pair(base, base.replace("49", "50"), ".json")  # an integer count is exact
    assert not pair(base, base.replace("false", "true"), ".json")  # a verdict is exact
    assert not pair(base, base.replace('"C1"', '"C2"'), ".json")
    assert not pair(base, base.replace('"slope"', '"slop"'), ".json")  # structure is exact
    md = "slope 0.374, 49 patients, CI [1.000, 2.000] | no |"
    assert pair(md, md.replace("0.374", "0.380"), ".md")
    assert not pair(md, md.replace("0.374", "0.700"), ".md")
    assert not pair(md, md.replace("49 patients", "50 patients"), ".md")
    assert not pair(md, md.replace("| no |", "| yes |"), ".md")
