"""
vigil_ml.k6

K6 active sensing: when to test next and with which panel. Research module (maturity L0), wired to
nothing. The specification is ``experiments/EXP-K6-001/PREREG.md`` (including its Amendment 1),
committed before this file.

What it is: a calibrated multi-horizon hazard model (``HazardModel``) that returns G(u), the
probability that a patient who is still under surveillance has a detectable recurrence by u days
from now, and a closed-form planner (``plan``) that picks the next interval and panel by minimising
a finite-horizon expected cost (cost per test plus a weight ``w`` on days of undetected detectable
disease). ``w`` is an input, never chosen here: the study sweeps it and reports a frontier. The
planner is a *suggestion* engine; it is never an alerting rule and it outputs no diagnosis.

What it is not: expected information gain on a K1 posterior, reinforcement learning, or anything
fitted to real patients. Everything it has been evaluated on is synthetic.

This module imports no simulator and reads no column of a simulator's latent state or truth: its
inputs are observed arrays (a visit's measurements, symptoms, alerts) and static covariates. Models
are exchanged as plain text and numbers (``HazardModel.to_dict`` / ``from_dict``); there is no
binary object serialisation of any kind.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import xgboost as xgb  # noqa: F401  (imported before anything that may load another OpenMP runtime)
from sklearn.isotonic import IsotonicRegression

# ------------------------------------------------------------------------------------------------
# Fixed design (PREREG sections 3 to 5)
# ------------------------------------------------------------------------------------------------
HORIZONS: Tuple[int, ...] = (0, 28, 56, 91, 182, 364)
H_PLAN: float = 364.0
ACTION_DELTAS: Tuple[int, ...] = (14, 28, 42, 56, 84, 112, 168, 252, 364)
FIXED_DELTAS: Tuple[int, ...] = (28, 42, 56, 91, 119, 182, 273, 364)
PANELS: Tuple[str, ...] = ("P1", "P2", "P3")
ANALYTES: Tuple[str, ...] = ("alp", "ggt", "ast", "alt", "ca_15_3", "cea")
PANEL_ANALYTES: Dict[str, Tuple[str, ...]] = {
    "P1": ("alp", "ggt", "ast", "alt"),
    "P2": ("alp", "ggt", "ast", "alt", "ca_15_3"),
    "P3": ("alp", "ggt", "ast", "alt", "ca_15_3", "cea"),
}
# PREREG section 5 plus Amendment 3: the original nine values and eight halvings below 0.1.
W_GRID: Tuple[float, ...] = tuple(0.1 / 2**k for k in range(8, 0, -1)) + (
    0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6,
)
S_FLOOR: float = 0.02
SYMPTOM_ALERT_GRADE: int = 2
BURDEN_DETECTABLE: float = 12.0

STATIC_NAMES = ("stage", "tnbc", "her2_pos", "er", "pr", "age")
TIME_NAMES = ("days_since_start", "n_visits", "last_interval")
PER_ANALYTE = ("days_since_last", "last_z", "max_z", "log_ratio_first", "slope90")
GLOBAL_NAMES = ("max_symptom", "n_negative_imaging", "days_since_alert")
FEATURE_NAMES: Tuple[str, ...] = (
    STATIC_NAMES
    + TIME_NAMES
    + tuple(f"{a}:{f}" for a in ANALYTES for f in PER_ANALYTE)
    + GLOBAL_NAMES
)
N_FEATURES = len(FEATURE_NAMES)
#: Feature columns that do not use any laboratory history (the "prior-only" ablation).
PRIOR_ONLY_COLUMNS: Tuple[int, ...] = tuple(range(len(STATIC_NAMES) + len(TIME_NAMES)))

HAZARD_PARAMS: Dict[str, Any] = {
    "max_depth": 3,
    "n_estimators": 120,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 20,
    "reg_lambda": 5.0,
}


# ------------------------------------------------------------------------------------------------
# Costs, availability and the panel table (inputs, never constants of the planner)
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CostTable:
    """Cost units (an assumption in price-band units, see PREREG section 3)."""

    visit: float = 1.0
    panel: Dict[str, float] = field(default_factory=lambda: {"P1": 1.0, "P2": 2.0, "P3": 3.0})
    imaging: float = 4.0


@dataclass(frozen=True)
class PanelTable:
    """Detection probability and false-alert probability of the alert rule, per panel."""

    sensitivity: Dict[str, float]
    false_alert: Dict[str, float]

    def s(self, panel: str) -> float:
        return max(S_FLOOR, float(self.sensitivity[panel]))

    def f(self, panel: str) -> float:
        return float(self.false_alert[panel])


class NoAvailablePanel(ValueError):
    """Raised when no panel is available: the planner returns no schedule at all."""


# ------------------------------------------------------------------------------------------------
# Alert rule A (PREREG section 3)
# ------------------------------------------------------------------------------------------------
def calibrate_thresholds(z_by_analyte: Dict[str, np.ndarray], quantile: float = 0.995) -> np.ndarray:
    """Per-analyte threshold: the ``quantile`` of z over non-recurrent post-baseline visits."""
    theta = np.full(len(ANALYTES), np.inf)
    for j, a in enumerate(ANALYTES):
        z = np.asarray(z_by_analyte.get(a, []), dtype=float)
        z = z[np.isfinite(z)]
        if z.size:
            theta[j] = float(np.quantile(z, quantile))
    return theta


def alert_flags(
    z: np.ndarray, panel_mask: np.ndarray, theta: np.ndarray, max_symptom: np.ndarray
) -> np.ndarray:
    """Rule A. ``z`` is (n, A) with NaN for an analyte not measured or without an earlier value;
    ``panel_mask`` is (A,) or (n, A) bool, the analytes the panel includes."""
    z = np.asarray(z, dtype=float)
    ok = np.isfinite(z) & np.asarray(panel_mask, dtype=bool)
    with np.errstate(invalid="ignore"):
        hit = ok & (np.nan_to_num(z, nan=-np.inf) >= theta[None, :])
    return hit.any(axis=1) | (np.asarray(max_symptom) >= SYMPTOM_ALERT_GRADE)


def panel_mask(panel: str) -> np.ndarray:
    return np.array([a in PANEL_ANALYTES[panel] for a in ANALYTES], dtype=bool)


# ------------------------------------------------------------------------------------------------
# Causal history -> features
# ------------------------------------------------------------------------------------------------
class HistoryState:
    """Running per-patient summaries of observed data. Everything here is a function of data
    strictly before ``features`` is called; nothing reads truth."""

    def __init__(self, static: np.ndarray, start_day: float):
        static = np.asarray(static, dtype=float)
        if static.ndim != 2 or static.shape[1] != len(STATIC_NAMES):
            raise ValueError(f"static must have shape (n, {len(STATIC_NAMES)})")
        n, a = static.shape[0], len(ANALYTES)
        self.static = static
        self.start_day = float(start_day)
        self.cnt = np.zeros((n, a))
        self.sum_log = np.zeros((n, a))
        self.first_log = np.full((n, a), np.nan)
        self.last_log = np.full((n, a), np.nan)
        self.last_day = np.full((n, a), np.nan)
        self.prev_log = np.full((n, a), np.nan)
        self.prev_day = np.full((n, a), np.nan)
        self.last_z = np.full((n, a), np.nan)
        self.max_z = np.full((n, a), np.nan)
        self.n_visits = np.zeros(n)
        self.last_visit_day = np.full(n, np.nan)
        self.last_interval = np.full(n, np.nan)
        self.n_neg_img = np.zeros(n)
        self.last_alert_day = np.full(n, np.nan)
        self.max_sym = np.zeros(n)

    def compute_z(self, rows: np.ndarray, log_values: np.ndarray, measured: np.ndarray) -> np.ndarray:
        """z = log(value) minus the mean of earlier measured logs; NaN where not measured or no
        earlier value. Does not change the state."""
        cnt = self.cnt[rows]
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_prev = np.where(cnt > 0, self.sum_log[rows] / np.maximum(cnt, 1.0), np.nan)
        z = np.where(measured & (cnt > 0), log_values - mean_prev, np.nan)
        return z

    def observe(
        self,
        rows: np.ndarray,
        day: float,
        log_values: np.ndarray,
        measured: np.ndarray,
        max_symptom: np.ndarray,
    ) -> np.ndarray:
        """Record one visit for ``rows``. Returns z (computed before the update)."""
        z = self.compute_z(rows, log_values, measured)
        for j in range(len(ANALYTES)):
            m = measured[:, j]
            if not m.any():
                continue
            r = rows[m]
            lv = log_values[m, j]
            self.prev_log[r, j] = self.last_log[r, j]
            self.prev_day[r, j] = self.last_day[r, j]
            first = self.cnt[r, j] == 0
            self.first_log[r[first], j] = lv[first]
            self.cnt[r, j] += 1.0
            self.sum_log[r, j] += lv
            self.last_log[r, j] = lv
            self.last_day[r, j] = day
            zz = z[m, j]
            self.last_z[r, j] = zz
            self.max_z[r, j] = np.where(
                np.isfinite(zz), np.fmax(self.max_z[r, j], zz), self.max_z[r, j]
            )
        prev_visit = self.last_visit_day[rows]
        self.last_interval[rows] = np.where(np.isfinite(prev_visit), day - prev_visit, np.nan)
        self.last_visit_day[rows] = day
        self.n_visits[rows] += 1.0
        self.max_sym[rows] = max_symptom
        return z

    def record_alert(self, rows: np.ndarray, alerted: np.ndarray, negative_imaging: np.ndarray, day: float) -> None:
        a = rows[alerted]
        self.last_alert_day[a] = day
        self.n_neg_img[rows[negative_imaging]] += 1.0

    def features(self, rows: np.ndarray, day: float) -> np.ndarray:
        rows = np.asarray(rows)
        n = rows.size
        out = np.full((n, N_FEATURES), np.nan)
        out[:, :6] = self.static[rows]
        out[:, 6] = day - self.start_day
        out[:, 7] = self.n_visits[rows]
        out[:, 8] = self.last_interval[rows]
        base = 9
        for j in range(len(ANALYTES)):
            c = base + j * len(PER_ANALYTE)
            out[:, c] = day - self.last_day[rows, j]
            out[:, c + 1] = self.last_z[rows, j]
            out[:, c + 2] = self.max_z[rows, j]
            out[:, c + 3] = self.last_log[rows, j] - self.first_log[rows, j]
            dd = self.last_day[rows, j] - self.prev_day[rows, j]
            with np.errstate(invalid="ignore", divide="ignore"):
                out[:, c + 4] = np.where(dd > 0, (self.last_log[rows, j] - self.prev_log[rows, j]) / dd * 90.0, np.nan)
        g = base + len(ANALYTES) * len(PER_ANALYTE)
        out[:, g] = self.max_sym[rows]
        out[:, g + 1] = self.n_neg_img[rows]
        out[:, g + 2] = day - self.last_alert_day[rows]
        return out


# ------------------------------------------------------------------------------------------------
# Multi-horizon hazard model
# ------------------------------------------------------------------------------------------------
def _enforce(G: np.ndarray) -> np.ndarray:
    return np.clip(np.maximum.accumulate(np.clip(np.asarray(G, dtype=float), 0.0, 1.0), axis=-1), 0.0, 1.0)


class HazardModel:
    """One calibrated gradient-boosted classifier per horizon. ``predict_cdf`` returns G at
    ``HORIZONS``, non-decreasing and in [0, 1]."""

    def __init__(self, columns: Optional[Sequence[int]] = None):
        if columns is None:
            selected_columns = tuple(range(N_FEATURES))
        else:
            raw_columns = tuple(columns)
            if not raw_columns or any(
                isinstance(column, (bool, np.bool_))
                or not isinstance(column, (int, np.integer))
                for column in raw_columns
            ):
                raise ValueError("columns must be a non-empty sequence of integer feature indices")
            selected_columns = tuple(int(column) for column in raw_columns)
            if len(set(selected_columns)) != len(selected_columns):
                raise ValueError("columns must not contain duplicate feature indices")
        self.columns: Tuple[int, ...] = selected_columns
        self._boosters: List[Optional[xgb.Booster]] = []
        self._raw_json: List[Optional[str]] = []
        self._const: List[Optional[float]] = []
        self._iso: List[Optional[Tuple[np.ndarray, np.ndarray]]] = []
        self.fitted = False

    # -- fitting -------------------------------------------------------------------------------
    def fit(self, X: np.ndarray, labels: np.ndarray, groups: np.ndarray, seed: int) -> "HazardModel":
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError("X must be a two-dimensional feature matrix")
        if not self.columns or any(c < 0 or c >= X.shape[1] for c in self.columns):
            raise ValueError("columns must select existing feature indices")
        X = X[:, list(self.columns)]
        if np.isinf(X).any():
            raise ValueError("X may contain NaN for missing features but must not contain infinity")
        labels = np.asarray(labels)
        if labels.ndim != 2 or labels.shape != (X.shape[0], len(HORIZONS)):
            raise ValueError(
                f"labels must have shape (n_rows, {len(HORIZONS)}) matching X and HORIZONS"
            )
        if labels.dtype.kind not in "biuf" or not np.isfinite(labels).all():
            raise ValueError("labels must contain finite numeric binary targets")
        if not np.isin(labels, [0, 1]).all():
            raise ValueError("labels must contain only binary values 0 and 1")
        labels = labels.astype(np.uint8, copy=False)
        groups = np.asarray(groups)
        if groups.ndim != 1 or groups.shape[0] != X.shape[0]:
            raise ValueError("groups must be a one-dimensional vector aligned with X rows")
        if groups.dtype.kind in "iufc" and not np.isfinite(groups).all():
            raise ValueError("groups must contain finite patient identifiers")
        if np.unique(groups).size < 2:
            raise ValueError("at least two patient groups are required for grouped train/calibration split")
        rng = np.random.default_rng(seed)
        uniq = rng.permutation(np.unique(groups))
        n_cal = max(1, int(round(0.25 * len(uniq))))
        is_cal = np.isin(groups, uniq[:n_cal])
        tr, ca = ~is_cal, is_cal
        self._boosters, self._raw_json, self._const, self._iso = [], [], [], []
        for h in range(len(HORIZONS)):
            y = labels[:, h]
            if y[tr].min() == y[tr].max():
                self._boosters.append(None)
                self._raw_json.append(None)
                self._const.append(float(y[tr].mean()))
                self._iso.append(None)
                continue
            clf = xgb.XGBClassifier(
                objective="binary:logistic",
                tree_method="hist",
                n_jobs=1,
                random_state=int(seed) + h,
                **HAZARD_PARAMS,
            )
            clf.fit(X[tr], y[tr])
            js = bytes(clf.get_booster().save_raw(raw_format="json")).decode("utf-8")
            booster = self._load_booster(js)  # the model used is the model that is serialised
            raw = booster.predict(xgb.DMatrix(X[ca]))
            iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            iso.fit(raw, y[ca])
            self._boosters.append(booster)
            self._raw_json.append(js)
            self._const.append(None)
            self._iso.append((np.asarray(iso.X_thresholds_, dtype=float), np.asarray(iso.y_thresholds_, dtype=float)))
        self.fitted = True
        return self

    @staticmethod
    def _load_booster(js: str) -> xgb.Booster:
        b = xgb.Booster()
        b.load_model(bytearray(js.encode("utf-8")))
        return b

    # -- prediction ----------------------------------------------------------------------------
    def predict_cdf(self, X: np.ndarray, horizons: Optional[Sequence[int]] = None) -> np.ndarray:
        if not self.fitted:
            raise RuntimeError("HazardModel is not fitted")
        X = np.asarray(X, dtype=float)[:, list(self.columns)]
        idx = range(len(HORIZONS)) if horizons is None else [HORIZONS.index(int(h)) for h in horizons]
        cols = []
        dm = None
        for h in idx:
            if self._const[h] is not None:
                cols.append(np.full(X.shape[0], self._const[h]))
                continue
            if dm is None:
                dm = xgb.DMatrix(X)
            raw = self._boosters[h].predict(dm)
            xs, ys = self._iso[h]
            cols.append(np.interp(raw, xs, ys))
        G = np.column_stack(cols)
        return _enforce(G) if horizons is None else np.clip(G, 0.0, 1.0)

    # -- exchange (text and numbers only) --------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        models = []
        for h in range(len(HORIZONS)):
            if self._const[h] is not None:
                models.append({"kind": "constant", "p": self._const[h]})
            else:
                xs, ys = self._iso[h]
                models.append({"kind": "xgboost_json", "model": self._raw_json[h], "iso_x": xs.tolist(), "iso_y": ys.tolist()})
        return {"schema": "vigil.k6.hazard.v1", "horizons": list(HORIZONS), "columns": list(self.columns), "models": models}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HazardModel":
        if d.get("schema") != "vigil.k6.hazard.v1":
            raise ValueError("unknown schema")
        m = cls(columns=d["columns"])
        m._boosters, m._raw_json, m._const, m._iso = [], [], [], []
        for e in d["models"]:
            if e["kind"] == "constant":
                m._boosters.append(None)
                m._raw_json.append(None)
                m._const.append(float(e["p"]))
                m._iso.append(None)
            else:
                m._boosters.append(cls._load_booster(e["model"]))
                m._raw_json.append(e["model"])
                m._const.append(None)
                m._iso.append((np.asarray(e["iso_x"], dtype=float), np.asarray(e["iso_y"], dtype=float)))
        m.fitted = True
        return m

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "HazardModel":
        return cls.from_dict(json.loads(text))


# ------------------------------------------------------------------------------------------------
# The planner (PREREG section 4, Amendment 1)
# ------------------------------------------------------------------------------------------------
_KNOTS = np.array(HORIZONS, dtype=float)
_TRAPZ = np.zeros(len(HORIZONS))
for _k in range(len(HORIZONS) - 1):
    _w = _KNOTS[_k + 1] - _KNOTS[_k]
    _TRAPZ[_k] += 0.5 * _w
    _TRAPZ[_k + 1] += 0.5 * _w
_TRAPZ = _TRAPZ / H_PLAN  # G_bar = G @ _TRAPZ


@dataclass(frozen=True)
class Decision:
    delta_days: np.ndarray
    panel_index: np.ndarray
    objective: np.ndarray


def plan(
    G: np.ndarray,
    w: float,
    cost: CostTable,
    table: PanelTable,
    available: Optional[Dict[str, bool]] = None,
    deltas: Sequence[int] = ACTION_DELTAS,
) -> Decision:
    """argmin over (delta, panel) of J (PREREG Amendment 1). ``G`` is (n, len(HORIZONS)).

    Raises ``NoAvailablePanel`` when no panel is available: there is then no schedule to suggest.
    """
    if w < 0:
        raise ValueError("w must be non-negative")
    G = _enforce(np.atleast_2d(G))
    avail = {p: True for p in PANELS} if available is None else {p: bool(available.get(p, False)) for p in PANELS}
    use = [p for p in PANELS if avail[p]]
    if not use:
        raise NoAvailablePanel("no panel is available; no schedule is recommended")
    n = G.shape[0]
    g0, gh, gbar = G[:, 0], G[:, -1], G @ _TRAPZ
    D = np.array(deltas, dtype=float)
    J = np.full((n, len(D), len(PANELS)), np.inf)
    for pi, p in enumerate(PANELS):
        if not avail[p]:
            continue
        s, f = table.s(p), table.f(p)
        test = cost.visit + cost.panel[p]
        a = (H_PLAN / D)[None, :] * (test + f * cost.imaging * (1.0 - gbar))[:, None]
        wait = g0 / s + (gh - g0) * (0.5 + (1.0 - s) / s)
        b = w * D[None, :] * wait[:, None]
        J[:, :, pi] = a + b
    flat = J.reshape(n, -1)
    k = np.argmin(flat, axis=1)
    di, pi = np.divmod(k, len(PANELS))
    return Decision(delta_days=D[di].astype(int), panel_index=pi.astype(int), objective=flat[np.arange(n), k])


# ------------------------------------------------------------------------------------------------
# Policies (decide the next interval and panel from features of the current visit)
# ------------------------------------------------------------------------------------------------
class Policy:
    name = "policy"
    needs_features = False

    def decide(self, features: Optional[np.ndarray], n: int, day: float) -> Tuple[np.ndarray, np.ndarray]:  # pragma: no cover
        raise NotImplementedError


class FixedPolicy(Policy):
    needs_features = False

    def __init__(self, delta: int, panel: str):
        self.delta, self.panel = int(delta), panel
        self.name = f"fixed_{delta}_{panel}"

    def decide(self, features, n, day):
        return np.full(n, self.delta, dtype=int), np.full(n, PANELS.index(self.panel), dtype=int)


class StageHeuristicPolicy(Policy):
    """Illustrative stage-based schedule (not from a guideline): I 364 d, II 182 d, III and IV 91 d, panel P2."""

    needs_features = True
    name = "heuristic_stage"
    INTERVAL = {1: 364, 2: 182, 3: 91, 4: 91}

    def decide(self, features, n, day):
        if features is None:
            raise ValueError("stage heuristic requires observed stage features")
        features = np.asarray(features, dtype=float)
        if features.ndim != 2 or features.shape != (n, N_FEATURES):
            raise ValueError(f"features must have shape ({n}, {N_FEATURES})")
        stage_values = features[:, 0]
        if not np.isfinite(stage_values).all():
            raise ValueError("stage heuristic requires a recorded stage for every patient")
        if not np.isin(stage_values, tuple(self.INTERVAL)).all():
            raise ValueError("stage heuristic requires integer stage values from 1 through 4")
        stage = stage_values.astype(int)
        delta = np.array([self.INTERVAL[int(s)] for s in stage], dtype=int)
        return delta, np.full(n, PANELS.index("P2"), dtype=int)


class RiskTriggeredPolicy(Policy):
    """Interval ``short`` if the calibrated G(182) is at least ``theta``, else ``long``; panel P2."""

    needs_features = True

    def __init__(self, hazard: HazardModel, long: int, short: int, theta: float):
        self.hazard, self.long, self.short, self.theta = hazard, int(long), int(short), float(theta)
        self.name = f"risk_triggered_{long}_{short}_{theta:g}"

    def decide(self, features, n, day):
        g182 = self.hazard.predict_cdf(features, horizons=(182,))[:, 0]
        delta = np.where(g182 >= self.theta, self.short, self.long).astype(int)
        return delta, np.full(n, PANELS.index("P2"), dtype=int)


class K6Policy(Policy):
    needs_features = True

    def __init__(
        self,
        hazard: HazardModel,
        table: PanelTable,
        w: float,
        cost: Optional[CostTable] = None,
        available: Optional[Dict[str, bool]] = None,
        label: str = "k6",
        trace: bool = False,
    ):
        self.hazard, self.table, self.w = hazard, table, float(w)
        self.cost = cost or CostTable()
        self.available = available
        self.name = f"{label}_w{w:g}"
        self.trace: Optional[List[np.ndarray]] = [] if trace else None

    def decide(self, features, n, day):
        G = self.hazard.predict_cdf(features)
        if self.trace is not None:
            self.trace.append(G.copy())
        d = plan(G, self.w, self.cost, self.table, self.available)
        return d.delta_days, d.panel_index


class TrainingSchedulePolicy(Policy):
    """Random schedules for generating hazard-model training rows (PREREG section 5). Stateful per patient."""

    needs_features = False
    name = "training_random"

    def __init__(self, n_patients: int, rng: np.random.Generator):
        self.rng = rng
        self.base = rng.choice(np.array([14, 28, 56, 91, 182, 364]), size=n_patients)

    def decide_rows(self, rows: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        keep = self.rng.random(rows.size) < 0.7
        rand = self.rng.choice(np.array(ACTION_DELTAS), size=rows.size)
        delta = np.where(keep, self.base[rows], rand).astype(int)
        panel = self.rng.integers(0, len(PANELS), size=rows.size)
        return delta, panel

    def decide(self, features, n, day):  # pragma: no cover - the engine calls decide_rows
        raise NotImplementedError


# ------------------------------------------------------------------------------------------------
# Planner stability (descriptive; PREREG section 6)
# ------------------------------------------------------------------------------------------------
def perturb_cdf(G: np.ndarray, rng: np.random.Generator, amplitude: float = 0.02) -> np.ndarray:
    return _enforce(np.asarray(G, dtype=float) + rng.uniform(-amplitude, amplitude, size=np.shape(G)))


def stability(
    G: np.ndarray, w: float, cost: CostTable, table: PanelTable, rng: np.random.Generator, amplitude: float = 0.02
) -> Dict[str, float]:
    base = plan(G, w, cost, table)
    pert = plan(perturb_cdf(G, rng, amplitude), w, cost, table)
    steps = {d: i for i, d in enumerate(ACTION_DELTAS)}
    moved = np.array([abs(steps[int(a)] - steps[int(b)]) for a, b in zip(base.delta_days, pert.delta_days)])
    return {
        "n_decisions": int(len(moved)),
        "share_interval_moves_more_than_one_step": float(np.mean(moved > 1)) if len(moved) else float("nan"),
        "share_panel_changes": float(np.mean(base.panel_index != pert.panel_index)) if len(moved) else float("nan"),
    }
