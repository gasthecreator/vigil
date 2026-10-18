"""
vigil_ml.k6_engine

The environment of EXP-K6-001 (PREREG sections 3 and 6): it runs a policy over a dense world, applies
the alert rule and the imaging confirmation, counts cost, and computes endpoints. A *policy* sees only
what ``vigil_ml.k6.HistoryState`` has recorded (observed measurements, symptoms, its own alerts); this
module is the only place where the world's truth arrays are read, and it reads them for two things
only: the imaging result (burden at least 12) and labels and endpoints. ``world`` is any object with
the attributes of ``vigil_sim.surveillance.DenseWorld``; this module imports no simulator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from vigil_ml import k6

IMAGING_BURDEN = k6.BURDEN_DETECTABLE
DELAY_CAP = 365.0
DELAY_COHORT_MIN, DELAY_COHORT_MAX = 210.0, 1455.0
_PANEL_MASKS = np.array([k6.panel_mask(p) for p in k6.PANELS])
_PANEL_COST_KEYS = k6.PANELS


@dataclass
class SimResult:
    visited: np.ndarray  # (N, G) bool
    vcost: np.ndarray  # (N, G) cost units
    alerted: np.ndarray  # (N, G) bool
    neg_img: np.ndarray  # (N, G) bool
    panel: np.ndarray  # (N, G) int8, -1 where not visited
    screen_idx: np.ndarray  # (N,) grid index of screen detection, G if none
    rows: Optional[Dict[str, np.ndarray]] = None  # training rows when ``collect`` is set
    decisions: Optional[List[Dict[str, np.ndarray]]] = None


def _log(v: np.ndarray) -> np.ndarray:
    return np.log(np.maximum(v, 1e-6))


def simulate(
    world: Any,
    policy: k6.Policy,
    theta: np.ndarray,
    cost: Optional[k6.CostTable] = None,
    *,
    stop_at_symptoms: bool = False,
    collect: bool = False,
) -> SimResult:
    """Run ``policy`` over every patient of ``world`` (visits at grid days only).

    ``stop_at_symptoms`` ends a patient's surveillance at the first symptomatic presentation (used when
    generating training rows). Evaluation runs leave it off: the visits before a presentation are the
    same either way, and scenario A truncates afterwards (``endpoints``).
    """
    cost = cost or k6.CostTable()
    n, g = world.n, world.g
    panel_cost = np.array([cost.panel[p] for p in _PANEL_COST_KEYS])
    hist = k6.HistoryState(world.static, start_day=float(world.day[0]))
    next_idx = np.zeros(n, dtype=int)
    next_panel = np.full(n, k6.PANELS.index("P3"), dtype=int)  # the baseline visit takes the full panel
    alive = np.ones(n, dtype=bool)
    visited = np.zeros((n, g), dtype=bool)
    vcost = np.zeros((n, g))
    alerted_all = np.zeros((n, g), dtype=bool)
    neg_all = np.zeros((n, g), dtype=bool)
    panel_all = np.full((n, g), -1, dtype=np.int8)
    screen_idx = np.full(n, g, dtype=int)
    rows_acc: Dict[str, List[np.ndarray]] = {k: [] for k in ("X", "patient", "t", "alert_P1", "alert_P2", "alert_P3", "detectable")}
    training = hasattr(policy, "decide_rows")
    for t in range(g):
        day = float(world.day[t])
        rows = np.flatnonzero(alive & (next_idx == t) & (day < world.comp_day))
        if stop_at_symptoms and rows.size:
            rows = rows[t < world.sym3_idx[rows]]
        if rows.size == 0:
            continue
        pan = next_panel[rows]
        measured_world = world.measured[rows, t, :]
        measured = measured_world & _PANEL_MASKS[pan]
        logv = _log(world.values[rows, t, :])
        max_sym = world.max_sym[rows, t]
        z_full = hist.compute_z(rows, logv, measured_world) if collect else None
        z = hist.observe(rows, day, logv, measured, max_sym)
        alerted = k6.alert_flags(z, _PANEL_MASKS[pan], theta, max_sym)
        positive = world.burden[rows, t] >= IMAGING_BURDEN
        detected = alerted & positive
        negative = alerted & ~positive
        hist.record_alert(rows, alerted, negative, day)
        visited[rows, t] = True
        vcost[rows, t] = cost.visit + panel_cost[pan] + cost.imaging * alerted
        alerted_all[rows, t] = alerted
        neg_all[rows, t] = negative
        panel_all[rows, t] = pan
        screen_idx[rows[detected]] = t
        alive[rows[detected]] = False
        keep = ~detected
        cont = rows[keep]
        if cont.size == 0:
            continue
        feats = hist.features(cont, day) if (policy.needs_features or collect) else None
        if collect:
            rows_acc["X"].append(feats)
            rows_acc["patient"].append(cont)
            rows_acc["t"].append(np.full(cont.size, t))
            for i, p in enumerate(k6.PANELS):
                rows_acc[f"alert_{p}"].append(k6.alert_flags(z_full[keep], k6.panel_mask(p), theta, max_sym[keep]))
            rows_acc["detectable"].append(positive[keep])
        if training:
            delta, new_pan = policy.decide_rows(cont)
        else:
            delta, new_pan = policy.decide(feats, cont.size, day)
        next_idx[cont] = t + (np.asarray(delta) // 7)
        next_panel[cont] = new_pan
    rows_out = None
    if collect:
        rows_out = {k: (np.concatenate(v) if v else np.zeros((0,))) for k, v in rows_acc.items()}
    return SimResult(visited, vcost, alerted_all, neg_all, panel_all, screen_idx, rows=rows_out)


# ------------------------------------------------------------------------------------------------
# Training material (labels come from truth; features never do)
# ------------------------------------------------------------------------------------------------
def hazard_labels(world: Any, patient: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Label for horizon u: the patient's detectable grid index is at most t + u/7."""
    det = world.t_det_idx[patient]
    return np.column_stack([(det <= t + h / 7.0).astype(int) for h in k6.HORIZONS])


def threshold_samples(world: Any) -> Dict[str, np.ndarray]:
    """z of every analyte at the post-baseline visits of non-recurrent patients on a 91-day schedule
    with the full panel (13 grid steps), for calibrating rule A (PREREG section 3, item 2)."""
    sched = np.arange(0, world.g, 13)
    nonrec = np.flatnonzero(~world.has_rec)
    out: Dict[str, List[np.ndarray]] = {a: [] for a in k6.ANALYTES}
    sums = np.zeros((nonrec.size, len(k6.ANALYTES)))
    cnt = np.zeros_like(sums)
    for t in sched:
        alive = world.day[t] < world.comp_day[nonrec]
        meas = world.measured[nonrec, t, :] & alive[:, None]
        lv = _log(world.values[nonrec, t, :])
        for j, a in enumerate(k6.ANALYTES):
            ok = meas[:, j] & (cnt[:, j] > 0)
            if ok.any():
                out[a].append((lv[ok, j] - sums[ok, j] / cnt[ok, j]))
        sums = np.where(meas, sums + lv, sums)
        cnt = np.where(meas, cnt + 1.0, cnt)
    return {a: (np.concatenate(v) if v else np.zeros(0)) for a, v in out.items()}


def panel_table_from_rows(rows: Dict[str, np.ndarray]) -> k6.PanelTable:
    det = rows["detectable"].astype(bool)
    sens, fa = {}, {}
    for p in k6.PANELS:
        a = rows[f"alert_{p}"].astype(bool)
        sens[p] = float(a[det].mean()) if det.any() else 0.0
        fa[p] = float(a[~det].mean()) if (~det).any() else 0.0
    return k6.PanelTable(sensitivity=sens, false_alert=fa)


# ------------------------------------------------------------------------------------------------
# Endpoints (PREREG section 6)
# ------------------------------------------------------------------------------------------------
def _effective_sym_idx(world: Any) -> np.ndarray:
    """First symptomatic-presentation index, if it happens before any competing event."""
    day_s = np.where(world.sym3_idx < world.g, world.day[np.minimum(world.sym3_idx, world.g - 1)], np.inf)
    return np.where(day_s < world.comp_day, world.sym3_idx, world.g)


def endpoints(world: Any, res: SimResult, scenario: str = "A") -> Dict[str, float]:
    """Cost, delay and companions for one policy on one world. ``scenario`` A: a patient presents
    with a symptom grade of 3 or more (detected that day); B: screening only."""
    if scenario not in ("A", "B"):
        raise ValueError("scenario must be 'A' or 'B'")
    g = world.g
    days = np.append(world.day, np.inf)
    screen_day = days[res.screen_idx]
    sym_idx = _effective_sym_idx(world)
    sym_day = days[sym_idx]
    if scenario == "A":
        t_det = np.minimum(screen_day, sym_day)
        counted = np.arange(g)[None, :] < sym_idx[:, None]
    else:
        t_det = screen_day
        counted = np.ones((world.n, g), dtype=bool)
    visits = res.visited & counted
    cost_total = np.where(counted, res.vcost, 0.0).sum(axis=1)
    cohort = (
        world.has_rec
        & (world.t_rec >= DELAY_COHORT_MIN)
        & (world.t_rec <= DELAY_COHORT_MAX)
        & (world.comp_day > np.nan_to_num(world.t_rec, nan=np.inf) + 365.0)
    )
    delay_raw = t_det - world.t_rec
    delay = np.where(np.isfinite(delay_raw), np.minimum(delay_raw, DELAY_CAP), DELAY_CAP)
    last_day = float(world.day[-1])
    follow_end = np.minimum(np.minimum(t_det, world.comp_day), last_day)
    years = float(np.clip(follow_end - world.day[0], 0.0, None).sum() / 365.25)
    neg = int((res.neg_img & counted).sum())
    out: Dict[str, float] = {
        "cost": float(cost_total.mean()),
        "visits": float(visits.sum(axis=1).mean()),
        "n_patients": int(world.n),
        "n_delay_cohort": int(cohort.sum()),
        "delay": float(delay[cohort].mean()) if cohort.any() else float("nan"),
        "missed": float((delay_raw[cohort] >= DELAY_CAP).mean()) if cohort.any() else float("nan"),
        "early_28": float(((world.t_rec - t_det)[cohort] >= 28.0).mean()) if cohort.any() else float("nan"),
        "screen_before_symptoms": float((screen_day[cohort] < sym_day[cohort]).mean()) if cohort.any() else float("nan"),
        "overdetection_per_100py": float(100.0 * neg / years) if years > 0 else float("nan"),
        "alerts_per_patient": float((res.alerted & counted).sum(axis=1).mean()),
    }
    for i, p in enumerate(k6.PANELS):
        total = float(visits.sum())
        out[f"panel_share_{p}"] = float(((res.panel == i) & visits).sum() / total) if total else float("nan")
    if scenario == "A":
        pres = sym_idx < g
        idx = np.minimum(sym_idx, g - 1)
        burden_at = world.burden[np.arange(world.n), idx]
        out["presentations_below_12"] = int(((burden_at < IMAGING_BURDEN) & pres).sum())
        out["presentations"] = int(pres.sum())
    return out
