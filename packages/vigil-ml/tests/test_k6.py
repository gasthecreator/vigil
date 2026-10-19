"""Invariants of EXP-K6-001 (PREREG section 8 and Amendment 1) for ``vigil_ml.k6`` and
``vigil_ml.k6_engine``. Synthetic data only."""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import xgboost  # noqa: F401  (must be imported first on macOS)
from vigil_ml import k6
from vigil_ml import k6_engine as E

ROOT = Path(__file__).resolve().parents[3]
TABLE = k6.PanelTable(
    sensitivity={"P1": 0.30, "P2": 0.60, "P3": 0.70},
    false_alert={"P1": 0.01, "P2": 0.03, "P3": 0.06},
)
COST = k6.CostTable()


def _random_G(rng: np.random.Generator, n: int) -> np.ndarray:
    raw = rng.random((n, len(k6.HORIZONS))) * rng.random((n, 1)) ** 2
    return np.maximum.accumulate(np.clip(raw, 0, 1), axis=1)


# 1. monotone in the hazard (single panel) ----------------------------------------------------------
@pytest.mark.parametrize("panel", k6.PANELS)
@pytest.mark.parametrize("w", [0.1, 1.6, 25.6])
def test_interval_is_non_increasing_when_the_hazard_is_raised_for_a_single_panel(panel, w):
    rng = np.random.default_rng(11)
    G = _random_G(rng, 800)
    G2 = np.maximum.accumulate(np.clip(G + rng.random((800, 1)) * 0.3, 0, 1), axis=1)
    avail = {p: p == panel for p in k6.PANELS}
    d1 = k6.plan(G, w, COST, TABLE, avail).delta_days
    d2 = k6.plan(G2, w, COST, TABLE, avail).delta_days
    assert np.all(d2 <= d1)


# 2. limits in w ------------------------------------------------------------------------------------
def test_zero_hazard_gives_the_longest_interval_and_the_cheapest_panel():
    G = np.zeros((1, len(k6.HORIZONS)))
    d = k6.plan(G, 1.6, COST, TABLE)
    assert d.delta_days[0] == max(k6.ACTION_DELTAS)
    per_panel = {p: COST.visit + COST.panel[p] + TABLE.f(p) * COST.imaging for p in k6.PANELS}
    assert k6.PANELS[d.panel_index[0]] == min(per_panel, key=per_panel.get)


def test_a_huge_weight_with_a_real_hazard_gives_the_shortest_interval():
    G = np.array([[0.1, 0.15, 0.2, 0.25, 0.35, 0.5]])
    assert k6.plan(G, 1e9, COST, TABLE).delta_days[0] == min(k6.ACTION_DELTAS)


def test_a_zero_weight_gives_the_longest_interval():
    G = np.array([[0.1, 0.15, 0.2, 0.25, 0.35, 0.5]])
    assert k6.plan(G, 0.0, COST, TABLE).delta_days[0] == max(k6.ACTION_DELTAS)


# 3. availability and cost inputs (M4 integration) ------------------------------------------------------
def test_an_unavailable_panel_is_never_recommended():
    rng = np.random.default_rng(5)
    G = _random_G(rng, 600)
    for w in (0.1, 1.6, 25.6):
        d = k6.plan(G, w, COST, TABLE, {"P1": True, "P2": True, "P3": False})
        assert (d.panel_index != k6.PANELS.index("P3")).all()


def test_no_available_panel_gives_no_schedule_at_all():
    with pytest.raises(k6.NoAvailablePanel):
        k6.plan(np.zeros((1, 6)), 1.0, COST, TABLE, {"P1": False, "P2": False, "P3": False})


def test_changing_panel_prices_changes_the_choice_in_the_expected_direction():
    G = np.array([[0.2, 0.25, 0.3, 0.35, 0.45, 0.6]])
    base = k6.plan(G, 3.2, COST, TABLE)
    pricey = k6.CostTable(visit=1.0, panel={"P1": 1.0, "P2": 2.0, "P3": 2000.0}, imaging=4.0)
    cheap_p3 = k6.CostTable(visit=1.0, panel={"P1": 50.0, "P2": 50.0, "P3": 0.01}, imaging=4.0)
    assert k6.PANELS[k6.plan(G, 3.2, pricey, TABLE).panel_index[0]] != "P3"
    assert k6.PANELS[k6.plan(G, 3.2, cheap_p3, TABLE).panel_index[0]] == "P3"
    assert base.objective[0] > 0


# 4 and 8. hazard model: output shape, calibration of the interface, export parity ----------------------------
def _toy_hazard_data(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k6.N_FEATURES))
    risk = 1 / (1 + np.exp(-(1.5 * X[:, 0] - 0.5)))
    t_event = rng.exponential(1.0 / np.maximum(risk, 1e-3) * 120.0)
    labels = np.column_stack([(t_event <= h).astype(int) for h in k6.HORIZONS])
    groups = np.arange(n) // 3
    return X, labels, groups


def test_hazard_output_is_in_unit_interval_and_non_decreasing_in_horizon():
    X, labels, groups = _toy_hazard_data()
    m = k6.HazardModel().fit(X, labels, groups, seed=1)
    G = m.predict_cdf(X[:500])
    assert G.shape == (500, len(k6.HORIZONS))
    assert (G >= 0).all() and (G <= 1).all()
    assert (np.diff(G, axis=1) >= -1e-12).all()


def test_hazard_model_round_trips_through_text_with_identical_output_and_no_binary_object_format():
    X, labels, groups = _toy_hazard_data(seed=3)
    m = k6.HazardModel().fit(X, labels, groups, seed=2)
    text = m.to_json()
    json.loads(text)  # plain JSON
    m2 = k6.HazardModel.from_json(text)
    assert np.array_equal(m.predict_cdf(X[:700]), m2.predict_cdf(X[:700]))
    for path in (ROOT / "packages/vigil-ml/vigil_ml/k6.py", ROOT / "packages/vigil-ml/vigil_ml/k6_engine.py", ROOT / "experiments/EXP-K6-001/run.py"):
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)} | {
            (n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        }
        assert not (imported & {"pickle", "joblib", "dill", "cloudpickle", "shelve"}), path


def test_hazard_model_with_a_constant_horizon_still_exports_and_predicts():
    X, labels, groups = _toy_hazard_data(n=600)
    labels[:, 0] = 0  # horizon 0 never happens: a constant model
    m = k6.HazardModel().fit(X, labels, groups, seed=1)
    assert m.to_dict()["models"][0]["kind"] == "constant"
    assert np.array_equal(m.predict_cdf(X[:50]), k6.HazardModel.from_json(m.to_json()).predict_cdf(X[:50]))


def test_the_prior_only_model_ignores_laboratory_columns():
    X, labels, groups = _toy_hazard_data(seed=4)
    m = k6.HazardModel(columns=k6.PRIOR_ONLY_COLUMNS).fit(X, labels, groups, seed=1)
    X2 = X.copy()
    X2[:, len(k6.PRIOR_ONLY_COLUMNS) :] = 12345.0
    assert np.array_equal(m.predict_cdf(X[:100]), m.predict_cdf(X2[:100]))


# 5 and 6. causality and the policies never read evaluation columns -----------------------------------------
@dataclass
class ToyWorld:
    day: np.ndarray
    values: np.ndarray
    measured: np.ndarray
    max_sym: np.ndarray
    static: np.ndarray
    burden: np.ndarray
    has_rec: np.ndarray
    t_rec: np.ndarray
    comp_day: np.ndarray
    t_det_idx: np.ndarray
    sym3_idx: np.ndarray

    @property
    def n(self):
        return self.values.shape[0]

    @property
    def g(self):
        return self.values.shape[1]


def make_toy_world(n=500, g=60, seed=0, signal_in_static=True, prodrome_weeks=0) -> ToyWorld:
    """Weekly grid. A patient with stage 4 recurs with probability 0.8 (stage 2 with 0.05), at a week in
    [8, g-6). From that week burden is 20 and CA 15-3 is three times its baseline; if ``prodrome_weeks`` is
    positive, CA 15-3 climbs linearly over that many weeks before it."""
    rng = np.random.default_rng(seed)
    day = 182.0 + 7.0 * np.arange(g)
    stage = rng.choice([2, 4], size=n)
    p = np.where(stage == 4, 0.8, 0.05)
    if not signal_in_static:
        p = np.full(n, 0.45)
    rec = rng.random(n) < p
    onset = rng.integers(8, g - 6, size=n)
    base = np.exp(rng.normal(0.0, 0.05, size=(n, 1, len(k6.ANALYTES)))) * 10.0
    noise = np.exp(rng.normal(0.0, 0.04, size=(n, g, len(k6.ANALYTES))))
    values = base * noise
    burden = np.zeros((n, g))
    k = np.arange(g)[None, :]
    on = rec[:, None] & (k >= onset[:, None])
    burden[on] = 20.0
    ca = values[:, :, 4]
    ca[on] *= 3.0
    if prodrome_weeks > 0:
        ramp = np.clip((k - (onset[:, None] - prodrome_weeks)) / prodrome_weeks, 0, 1)
        ca *= np.where(rec[:, None] & (k < onset[:, None]), 1.0 + 1.0 * ramp, 1.0)
    det = np.where(rec, onset, g)
    return ToyWorld(
        day=day,
        values=values,
        measured=np.ones((n, g, len(k6.ANALYTES)), dtype=bool),
        max_sym=np.zeros((n, g), dtype=np.int8),
        static=np.column_stack([stage, np.zeros(n), np.zeros(n), np.ones(n), np.ones(n), np.full(n, 50.0)]).astype(float),
        burden=burden,
        has_rec=rec,
        t_rec=np.where(rec, day[np.minimum(det, g - 1)] + 30.0, np.nan),
        comp_day=np.full(n, np.inf),
        t_det_idx=det.astype(int),
        sym3_idx=np.full(n, g, dtype=int),
    )


def _theta(w: ToyWorld) -> np.ndarray:
    return k6.calibrate_thresholds(E.threshold_samples(w))


def _train_toy(w: ToyWorld, seed=0, shuffle=False):
    theta = _theta(w)
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(3):
        res = E.simulate(w, k6.TrainingSchedulePolicy(w.n, rng), theta, stop_at_symptoms=True, collect=True)
        rows.append(res.rows)
    cat = {k: np.concatenate([r[k] for r in rows]) for k in rows[0]}
    labels = E.hazard_labels(w, cat["patient"].astype(int), cat["t"].astype(int))
    if shuffle:
        r2 = np.random.default_rng(seed + 99)
        labels = np.column_stack([r2.permutation(labels[:, h]) for h in range(labels.shape[1])])
    haz = k6.HazardModel().fit(cat["X"], labels, cat["patient"].astype(int), seed=seed)
    return theta, haz, E.panel_table_from_rows(cat)


def test_panel_table_counts_every_training_visit_including_those_that_detect():
    """Amendment 4: the table once came out as sensitivity 0 for every panel when the signal is in an
    analyte every panel measures, because visits at which the visiting panel had already detected the
    patient were dropped before counting (and 0 is what an empty count returned)."""
    w = make_toy_world(n=400, seed=5)
    w.values[:, :, 0] = np.where(w.burden > 0, w.values[:, :, 0] * 3.0, w.values[:, :, 0])  # ALP, in P1, P2 and P3
    _, _, table = _train_toy(w, seed=5)
    assert all(table.sensitivity[p] > 0.9 for p in k6.PANELS), table.sensitivity
    assert all(0.0 <= table.false_alert[p] < 0.2 for p in k6.PANELS)
    # and a signal only in CA 15-3 (the default toy world): carried by P2 and P3, absent from P1
    w2 = make_toy_world(n=400, seed=5)
    _, _, t2 = _train_toy(w2, seed=5)
    assert t2.sensitivity["P2"] > 0.9 and t2.sensitivity["P3"] > 0.9 and t2.sensitivity["P1"] < 0.1


def test_decisions_before_a_day_do_not_depend_on_data_from_that_day_on():
    w = make_toy_world(n=300, seed=1)
    theta, haz, table = _train_toy(w, seed=1)
    pol = lambda: k6.K6Policy(haz, table, 1.6)  # noqa: E731
    r1 = E.simulate(w, pol(), theta)
    t0 = 30
    w2 = make_toy_world(n=300, seed=1)
    w2.values[:, t0:, :] *= 7.0
    w2.measured[:, t0:, :] = ~w2.measured[:, t0:, :]
    w2.max_sym[:, t0:] = 3
    r2 = E.simulate(w2, pol(), theta)
    assert np.array_equal(r1.visited[:, :t0], r2.visited[:, :t0])
    assert np.array_equal(r1.panel[:, :t0], r2.panel[:, :t0])
    assert np.array_equal(r1.alerted[:, :t0], r2.alerted[:, :t0])


def test_evaluation_only_arrays_do_not_change_any_decision_or_cost():
    w = make_toy_world(n=300, seed=2)
    theta, haz, table = _train_toy(w, seed=2)
    pols = [k6.FixedPolicy(91, "P2"), k6.StageHeuristicPolicy(), k6.RiskTriggeredPolicy(haz, 182, 56, 0.1), k6.K6Policy(haz, table, 1.6)]
    base = [E.simulate(w, p, theta) for p in pols]
    w2 = make_toy_world(n=300, seed=2)
    rng = np.random.default_rng(0)
    w2.t_rec = rng.normal(size=w2.n) * 1e6
    w2.has_rec = rng.random(w2.n) < 0.5
    w2.t_det_idx = rng.integers(0, w2.g, size=w2.n)
    w2.sym3_idx = rng.integers(0, w2.g, size=w2.n)
    for p, b in zip(pols, base):
        r = E.simulate(w2, p, theta)
        assert np.array_equal(r.visited, b.visited), p.name
        assert np.array_equal(r.vcost, b.vcost), p.name
        assert np.array_equal(r.screen_idx, b.screen_idx), p.name


def test_policy_code_never_names_a_truth_column():
    forbidden_attr = {"burden", "t_rec", "has_rec", "t_det_idx", "sym3_idx", "comp_day"}
    src = (ROOT / "packages/vigil-ml/vigil_ml/k6.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attr, f"k6.py reads .{node.attr}"
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert "latent_" not in node.value and "true_recurrence" not in node.value
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
            assert not any("vigil_sim" in n for n in names), "k6.py must not import the simulator"
    for cls in (k6.FixedPolicy, k6.StageHeuristicPolicy, k6.RiskTriggeredPolicy, k6.K6Policy):
        assert list(inspect.signature(cls.decide).parameters) == ["self", "features", "n", "day"]


# 7. determinism and non-interference ------------------------------------------------------------------------------
def test_simulation_is_deterministic_and_does_not_modify_the_world():
    w = make_toy_world(n=200, seed=3)
    snap = {k: np.copy(getattr(w, k)) for k in ("values", "measured", "max_sym", "burden", "static")}
    theta = _theta(w)
    a = E.simulate(w, k6.FixedPolicy(56, "P3"), theta)
    b = E.simulate(w, k6.FixedPolicy(56, "P3"), theta)
    assert np.array_equal(a.vcost, b.vcost) and np.array_equal(a.screen_idx, b.screen_idx)
    for k, v in snap.items():
        assert np.array_equal(v, getattr(w, k)), k


def test_fixed_schedule_visits_exactly_on_its_grid_and_costs_what_the_table_says():
    w = make_toy_world(n=100, seed=4, signal_in_static=False)
    theta = np.full(len(k6.ANALYTES), np.inf)  # never alert on markers
    r = E.simulate(w, k6.FixedPolicy(91, "P2"), theta)
    visited_idx = np.flatnonzero(r.visited[0])
    assert np.array_equal(visited_idx, np.arange(0, w.g, 13))
    assert np.isclose(r.vcost[0, 0], 1 + 3.0)  # baseline takes P3
    assert np.isclose(r.vcost[0, 13], 1 + 2.0)  # later visits take P2


def test_imaging_confirms_only_at_burden_12_and_a_negative_referral_keeps_the_patient():
    w = make_toy_world(n=1, g=40, seed=5, signal_in_static=False)
    w.has_rec[:] = True
    w.values[:] = 10.0
    w.values[0, 12:, 4] = 40.0  # CA 15-3 jumps at week 12 (alert), burden still below 12
    w.burden[0, :] = 0.0
    w.burden[0, 20:] = 20.0
    w.static[0, 0] = 3.0
    theta = np.log(np.array([1.5] * len(k6.ANALYTES)))
    r = E.simulate(w, k6.FixedPolicy(28, "P2"), theta)
    alerted = np.flatnonzero(r.alerted[0])
    assert alerted.size >= 2 and r.neg_img[0, alerted[0]]  # first alert is a negative referral
    assert r.screen_idx[0] >= 20  # detected only once the burden is 12 or more


# 9. planted signal: K6 beats the fixed frontier when the patient is informative, not when labels are shuffled ------
def _frontier_delay_at(points, cost):
    pts = sorted(points)
    front, best = [], np.inf
    for c, d in pts:
        if d < best:
            front.append((c, d))
            best = d
    if cost < front[0][0] or cost > front[-1][0]:
        return None
    for (c0, d0), (c1, d1) in zip(front[:-1], front[1:]):
        if c0 <= cost <= c1:
            return d0 + (d1 - d0) * (cost - c0) / (c1 - c0) if c1 > c0 else d0
    return front[-1][1]


def _point(w, pol, theta):
    r = E.simulate(w, pol, theta)
    e = E.endpoints(w, r, "B")
    return e["cost"], e["delay"]


def _planted_margin(shuffle: bool, seed: int):
    train = make_toy_world(n=700, seed=seed, prodrome_weeks=0)
    test = make_toy_world(n=700, seed=seed + 50, prodrome_weeks=0)
    theta, haz, table = _train_toy(train, seed=seed, shuffle=shuffle)
    fixed = [_point(test, k6.FixedPolicy(d, p), theta) for d in k6.FIXED_DELTAS for p in k6.PANELS]
    margins = []
    for w in k6.W_GRID:
        c, d = _point(test, k6.K6Policy(haz, table, w), theta)
        ref = _frontier_delay_at(fixed, c)
        if ref is not None:
            margins.append(ref - d)  # positive: K6 earlier than the fixed frontier at the same cost
    return float(np.mean(margins)) if margins else float("nan")


def test_planted_signal_k6_beats_fixed_at_equal_cost_and_shuffled_labels_do_not():
    """PREREG section 8, item 9. The signal is the patient's stage (80 percent against 5 percent recurrence).
    Real: mean over three toy worlds must be positive (earlier than the fixed frontier at equal cost). Shuffled
    labels: mean over five fits must not be positive. The margins are not the study's; a single toy world
    can be small (one of the three seeds here is under 4 days), hence the mean over three."""
    real = float(np.mean([_planted_margin(False, seed=s) for s in (7, 8, 9)]))
    shuffled = float(np.mean([_planted_margin(True, seed=100 + s) for s in range(5)]))
    assert real > 0.0, real
    assert shuffled <= 0.0, shuffled
    assert real - shuffled > 10.0, (real, shuffled)


# 10. planner stability ---------------------------------------------------------------------------------------------
def test_small_perturbations_rarely_move_the_interval_by_more_than_one_step():
    rng = np.random.default_rng(21)
    G = _random_G(rng, 4000)
    s = k6.stability(G, 1.6, COST, TABLE, np.random.default_rng(1), amplitude=0.005)
    assert s["share_interval_moves_more_than_one_step"] < 0.10, s


# the retired stub ---------------------------------------------------------------------------------------------------
def test_the_old_k6_stub_is_retired_and_no_benchmark_scores_it():
    import importlib.util

    assert importlib.util.find_spec("vigil_ml.active_sensing_k6") is None
    import vigil_ml

    for name in ("ActiveSensingEngineK6", "ActiveSensingRecommendation", "TestPanelTier"):
        assert not hasattr(vigil_ml, name)
    assert "ActiveSensingEngineK6" not in (ROOT / "scripts" / "run_benchmarks.py").read_text(encoding="utf-8")
