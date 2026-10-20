#!/usr/bin/env python3
"""EXP-K6-001 runner (study S6). Specification: experiments/EXP-K6-001/PREREG.md (with Amendments 1 and 2).
Every number in the outputs is computed here; none is typed.

    uv run python experiments/EXP-K6-001/run.py --dev        # dev replications 0..2 -> dev_results.json (debugging, not evidence)
    uv run python experiments/EXP-K6-001/run.py --frozen     # replications 0..19 -> results.json, REPORT.md (run ONCE)
    uv run python experiments/EXP-K6-001/run.py --smoke      # tiny design, nothing committed (used by tests)
    uv run python experiments/EXP-K6-001/run.py --rerender   # re-derive aggregate + REPORT.md from results.json records

A policy receives only what vigil_ml.k6.HistoryState has recorded. The world's truth arrays are read by the engine
(vigil_ml.k6_engine) for the imaging result and for labels and endpoints, and by this file for the same two purposes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _pkg in ("vigil-sim", "vigil-ml", "vigil-core", "vigil-eval"):
    sys.path.insert(0, str(ROOT / "packages" / _pkg))

import xgboost  # noqa: E402,F401  (imported before anything else that may load an OpenMP runtime)
from vigil_ml import k6  # noqa: E402
from vigil_ml import k6_engine as E  # noqa: E402
from vigil_sim import GeneratorType  # noqa: E402
from vigil_sim.surveillance import build_world  # noqa: E402

OUT = Path(__file__).resolve().parent
WORK = OUT / "_work"

CONFIG: Dict[str, Any] = {
    "n_train_generated": 1800,
    "n_test_generated": 1200,
    "training_passes": 3,
    "canary_shuffles": 5,
    "seeds": {
        "dev": {"base": 900, "step": 100, "n": 3},
        "frozen": {"base": 20261215, "step": 100, "n": 20},
    },
    "bootstrap": {"B": 2000, "seed": 20261215, "alpha_primary": 0.05 / 3.0, "alpha_descriptive": 0.05, "max_dropped": 0.05},
    "w_grid": list(k6.W_GRID),
    "fixed_deltas": list(k6.FIXED_DELTAS),
    "rt": {"long": [119, 182, 273, 364], "short": [28, 56, 91], "theta": [0.05, 0.10, 0.20, 0.40]},
    "stability": {"w": 1.6, "amplitude": 0.02},
    "named_fixed": {"three_month": ["fixed_91_P2"], "six_month": ["fixed_182_P2"]},
    "cost_units": {"visit": 1.0, "panel": {"P1": 1.0, "P2": 2.0, "P3": 3.0}, "imaging": 4.0},
    "alt_cost_units": [
        {"name": "visit 0.5", "visit": 0.5, "panel": {"P1": 1.0, "P2": 2.0, "P3": 3.0}, "imaging": 4.0},
        {"name": "visit 3", "visit": 3.0, "panel": {"P1": 1.0, "P2": 2.0, "P3": 3.0}, "imaging": 4.0},
        {"name": "panels 1, 2, 4", "visit": 1.0, "panel": {"P1": 1.0, "P2": 2.0, "P3": 4.0}, "imaging": 4.0},
    ],
}
SMOKE: Dict[str, Any] = {
    "n_train_generated": 160,
    "n_test_generated": 120,
    "training_passes": 2,
    "canary_shuffles": 1,
    "w_grid": [0.8, 3.2],
    "fixed_deltas": [91, 182],
    "rt": {"long": [182], "short": [56], "theta": [0.1]},
}


def design(scope: str) -> Dict[str, Any]:
    cfg = json.loads(json.dumps(CONFIG))
    if scope == "smoke":
        cfg.update(json.loads(json.dumps(SMOKE)))
    return cfg


def code_hash() -> str:
    h = hashlib.sha256()
    for p in (
        ROOT / "packages" / "vigil-ml" / "vigil_ml" / "k6.py",
        ROOT / "packages" / "vigil-ml" / "vigil_ml" / "k6_engine.py",
        ROOT / "packages" / "vigil-sim" / "vigil_sim" / "surveillance.py",
        Path(__file__),
    ):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def base_seed(kind: str, r: int) -> int:
    s = CONFIG["seeds"]["frozen" if kind in ("frozen", "smoke") else "dev"]
    return int(s["base"] + s["step"] * r)


# -------------------------------------------------------------------------------------------------
# One replication
# -------------------------------------------------------------------------------------------------
def train_models(world, seed: int, cfg: Dict[str, Any]) -> Dict[str, Any]:
    theta = k6.calibrate_thresholds(E.threshold_samples(world))
    rng = np.random.default_rng(seed + 4)
    rows = []
    for _ in range(cfg["training_passes"]):
        res = E.simulate(world, k6.TrainingSchedulePolicy(world.n, rng), theta, stop_at_symptoms=True, collect=True)
        rows.append(res.rows)
    cat = {k: np.concatenate([r[k] for r in rows]) for k in rows[0]}
    patient, t = cat["patient"].astype(int), cat["t"].astype(int)
    labels = E.hazard_labels(world, patient, t)
    hazard = k6.HazardModel().fit(cat["X"], labels, patient, seed=seed + 5)
    prior = k6.HazardModel(columns=k6.PRIOR_ONLY_COLUMNS).fit(cat["X"], labels, patient, seed=seed + 5)
    table = E.panel_table_from_rows(cat)
    return {
        "theta": theta,
        "hazard": hazard,
        "prior": prior,
        "table": table,
        "X": cat["X"],
        "labels": labels,
        "patient": patient,
        "meta": {
            "n_rows": int(len(patient)),
            "positive_rate_by_horizon": {str(h): float(labels[:, i].mean()) for i, h in enumerate(k6.HORIZONS)},
            "thresholds": {a: (float(x) if np.isfinite(x) else None) for a, x in zip(k6.ANALYTES, theta)},
            "sensitivity": {p: float(table.sensitivity[p]) for p in k6.PANELS},
            "false_alert": {p: float(table.false_alert[p]) for p in k6.PANELS},
            "world": world.meta,
        },
    }


def _record(kind: str, r: int, world_name: str, family: str, arm: str, params: Dict[str, Any], world, res, extra=None) -> Dict[str, Any]:
    rec = {
        "kind": kind,
        "rep": r,
        "world": world_name,
        "family": family,
        "arm": arm,
        "params": params,
        "A": E.endpoints(world, res, "A"),
        "B": E.endpoints(world, res, "B"),
    }
    if extra:
        rec.update(extra)
    return rec


def arm_list(cfg: Dict[str, Any], m: Dict[str, Any], full: bool) -> List[Tuple[str, str, Dict[str, Any], Callable[[], k6.Policy]]]:
    arms: List[Tuple[str, str, Dict[str, Any], Callable[[], k6.Policy]]] = []
    for d in cfg["fixed_deltas"]:
        for p in k6.PANELS:
            arms.append(("fixed", f"fixed_{d}_{p}", {"delta": d, "panel": p}, lambda d=d, p=p: k6.FixedPolicy(d, p)))
    arms.append(("heuristic", "heuristic_stage", {}, lambda: k6.StageHeuristicPolicy()))
    for lg in cfg["rt"]["long"]:
        for sh in cfg["rt"]["short"]:
            for th in cfg["rt"]["theta"]:
                arms.append(
                    ("risk", f"risk_{lg}_{sh}_{th:g}", {"long": lg, "short": sh, "theta": th},
                     lambda lg=lg, sh=sh, th=th: k6.RiskTriggeredPolicy(m["hazard"], lg, sh, th))
                )
    variants = [("k6_free", None, m["hazard"], "free")]
    if full:
        variants += [
            ("k6_P1", {"P1": True, "P2": False, "P3": False}, m["hazard"], "P1"),
            ("k6_P2", {"P1": False, "P2": True, "P3": False}, m["hazard"], "P2"),
            ("k6_P3", {"P1": False, "P2": False, "P3": True}, m["hazard"], "P3"),
            ("k6_prior", None, m["prior"], "prior"),
        ]
    for fam, avail, haz, label in variants:
        for w in cfg["w_grid"]:
            arms.append(
                (fam, f"{fam}_w{w:g}", {"w": w, "variant": label},
                 lambda w=w, haz=haz, avail=avail, label=label: k6.K6Policy(haz, m["table"], w, available=avail, label=label))
            )
    return arms


def calibration(world, m: Dict[str, Any], seed: int) -> Dict[str, Any]:
    rng = np.random.default_rng(seed + 12)
    res = E.simulate(world, k6.TrainingSchedulePolicy(world.n, rng), m["theta"], stop_at_symptoms=True, collect=True)
    rows = res.rows
    patient, t = rows["patient"].astype(int), rows["t"].astype(int)
    labels = E.hazard_labels(world, patient, t)
    G = m["hazard"].predict_cdf(rows["X"])
    out: Dict[str, Any] = {"n_rows": int(len(patient)), "ece": {}, "brier": {}}
    for i, h in enumerate(k6.HORIZONS):
        p, y = G[:, i], labels[:, i]
        out["brier"][str(h)] = float(np.mean((p - y) ** 2))
        order = np.argsort(p)
        bins = np.array_split(order, 10)
        ece = sum(len(b) / len(p) * abs(p[b].mean() - y[b].mean()) for b in bins if len(b))
        out["ece"][str(h)] = float(ece)
        if h == 182:
            out["reliability_182"] = [
                {"n": int(len(b)), "mean_predicted": float(p[b].mean()), "mean_observed": float(y[b].mean())} for b in bins if len(b)
            ]
    return out


def run_rep(kind: str, r: int, scope: str) -> Dict[str, Any]:
    cfg = design(scope)
    s = base_seed(kind, r)
    t0 = time.time()
    train = build_world(GeneratorType.G1_SMOOTH, s, cfg["n_train_generated"])
    m = train_models(train, s, cfg)
    worlds = {
        "G1": build_world(GeneratorType.G1_SMOOTH, s + 1, cfg["n_test_generated"]),
        "G2": build_world(GeneratorType.G2_BURST, s + 2, cfg["n_test_generated"]),
        "G3": build_world(GeneratorType.G3_NOISE, s + 3, cfg["n_test_generated"]),
    }
    records: List[Dict[str, Any]] = []
    stab = None
    for wname, world in worlds.items():
        for fam, arm, params, factory in arm_list(cfg, m, full=(wname == "G1")):
            pol = factory()
            if wname == "G1" and arm == f"k6_free_w{cfg['stability']['w']:g}":
                pol.trace = []
            res = E.simulate(world, pol, m["theta"], k6.CostTable())
            records.append(_record(kind, r, wname, fam, arm, params, world, res))
            if getattr(pol, "trace", None):
                G = np.concatenate(pol.trace)
                stab = k6.stability(G, cfg["stability"]["w"], k6.CostTable(), m["table"], np.random.default_rng(s + 11), cfg["stability"]["amplitude"])
    # leakage canary: hazard trained on labels shuffled independently over rows, per horizon
    for j in range(cfg["canary_shuffles"]):
        rng = np.random.default_rng(s + 6 + j)
        shuffled = np.column_stack([rng.permutation(m["labels"][:, h]) for h in range(m["labels"].shape[1])])
        haz = k6.HazardModel().fit(m["X"], shuffled, m["patient"], seed=s + 5)
        for w in cfg["w_grid"]:
            pol = k6.K6Policy(haz, m["table"], w, label="canary")
            res = E.simulate(worlds["G1"], pol, m["theta"], k6.CostTable())
            records.append(_record(kind, r, "G1", "canary", f"canary_w{w:g}", {"w": w}, worlds["G1"], res, extra={"shuffle": j}))
    meta = dict(m["meta"])
    meta.update(
        {
            "rep": r,
            "seed": s,
            "calibration_G1": calibration(worlds["G1"], m, s),
            "stability": stab,
            "test_worlds": {k: w.meta for k, w in worlds.items()},
            "seconds": round(time.time() - t0, 1),
        }
    )
    return {"records": records, "meta": [meta]}


# -------------------------------------------------------------------------------------------------
# Execution (process pool, resumable per replication, keyed by the code hash)
# -------------------------------------------------------------------------------------------------
def _init_worker() -> None:
    import os

    os.environ["OMP_NUM_THREADS"] = "1"


def run_unit(spec: Tuple) -> Tuple[Tuple, Dict[str, Any], float]:
    t0 = time.time()
    kind, r, scope = spec
    return spec, run_rep(kind, r, scope), time.time() - t0


def unit_path(spec: Tuple, tag: str) -> Path:
    kind, r, scope = spec
    return WORK / f"{tag}_{kind}_{r}_{scope}_{code_hash()}.json"


def execute(specs: List[Tuple], tag: str, workers: int) -> List[Tuple[Tuple, Dict[str, Any]]]:
    WORK.mkdir(exist_ok=True)
    done, todo = [], []
    for sp in specs:
        p = unit_path(sp, tag)
        if p.exists():
            done.append((sp, json.loads(p.read_text())))
        else:
            todo.append(sp)
    print(f"[{tag}] {len(done)} replications cached, {len(todo)} to run on {workers} workers", flush=True)
    if workers <= 1:
        for sp in todo:
            _, out, sec = run_unit(sp)
            unit_path(sp, tag).write_text(json.dumps(out))
            done.append((sp, out))
            print(f"  replication {sp[0]} r={sp[1]} done in {sec:.0f}s", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn"), initializer=_init_worker) as pool:
            futs = [pool.submit(run_unit, sp) for sp in todo]
            for f in as_completed(futs):
                sp, out, sec = f.result()
                unit_path(sp, tag).write_text(json.dumps(out))
                done.append((sp, out))
                print(f"  replication {sp[0]} r={sp[1]} done in {sec:.0f}s", flush=True)
    return done


def merge(done: List[Tuple[Tuple, Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {"records": [], "meta": []}
    for _, o in sorted(done, key=lambda kv: (kv[0][0], kv[0][1])):
        out["records"].extend(o["records"])
        out["meta"].extend(o["meta"])
    return out


# -------------------------------------------------------------------------------------------------
# Aggregation (a pure function of the stored records)
# -------------------------------------------------------------------------------------------------
Front = List[Tuple[float, float]]


def frontier(points: List[Tuple[float, float]]) -> Front:
    """Lower-left Pareto set in (cost, delay), cost increasing and delay strictly decreasing."""
    pts = sorted((c, d) for c, d in points if np.isfinite(c) and np.isfinite(d))
    out: Front = []
    best = math.inf
    for c, d in pts:
        if d < best - 1e-12:
            out.append((c, d))
            best = d
    return out


def delay_at(front: Front, cost: float) -> Optional[float]:
    if not front or cost < front[0][0] - 1e-9 or cost > front[-1][0] + 1e-9:
        return None
    for (c0, d0), (c1, d1) in zip(front[:-1], front[1:]):
        if c0 - 1e-9 <= cost <= c1 + 1e-9:
            return d0 + (d1 - d0) * (cost - c0) / (c1 - c0) if c1 > c0 else d0
    return front[-1][1]


def cost_at(front: Front, delay: float) -> Optional[float]:
    if not front or delay > front[0][1] + 1e-9 or delay < front[-1][1] - 1e-9:
        return None
    for (c0, d0), (c1, d1) in zip(front[:-1], front[1:]):
        if d1 - 1e-9 <= delay <= d0 + 1e-9:
            return c0 + (c1 - c0) * (d0 - delay) / (d0 - d1) if d0 > d1 else c0
    return front[-1][0]


class Arms:
    """Per-arm, per-replication arrays for one world and scenario."""

    def __init__(self, records: List[Dict[str, Any]], world: str, scenario: str, reps: List[int], families: Optional[List[str]] = None):
        self.reps = reps
        self.family: Dict[str, str] = {}
        self.params: Dict[str, Dict[str, Any]] = {}
        tmp: Dict[str, Dict[int, Dict[str, float]]] = {}
        for rec in records:
            if rec["world"] != world or rec["family"] == "canary":
                continue
            if families is not None and rec["family"] not in families:
                continue
            a = rec["arm"]
            self.family[a] = rec["family"]
            self.params[a] = rec["params"]
            tmp.setdefault(a, {})[rec["rep"]] = rec[scenario]
        self.names = sorted(tmp)
        self.metrics: Dict[str, Dict[str, np.ndarray]] = {}
        keys = ["cost", "delay", "missed", "early_28", "screen_before_symptoms", "overdetection_per_100py", "visits",
                "alerts_per_patient", "panel_share_P1", "panel_share_P2", "panel_share_P3", "n_delay_cohort"]
        for a in self.names:
            self.metrics[a] = {k: np.array([tmp[a][r][k] for r in reps], dtype=float) for k in keys}

    def mean(self, arm: str, metric: str, counts: Optional[np.ndarray] = None) -> float:
        v = self.metrics[arm][metric]
        return float(v.mean() if counts is None else (v * counts).sum() / counts.sum())

    def points(self, family: str, counts: Optional[np.ndarray] = None) -> List[Tuple[float, float]]:
        return [(self.mean(a, "cost", counts), self.mean(a, "delay", counts)) for a in self.names if self.family[a] == family]


def primary_stats(arms: Arms, budgets: Dict[str, float], d13: float, counts: Optional[np.ndarray] = None, k6_family: str = "k6_free") -> Dict[str, Optional[float]]:
    fx = frontier(arms.points("fixed", counts))
    rk = frontier(arms.points("risk", counts))
    kk = frontier(arms.points(k6_family, counts))
    out: Dict[str, Optional[float]] = {}
    for tag, fam in (("fixed", fx), ("risk", rk)):
        diffs = []
        for b in ("B13", "B26", "Bmid"):
            dk, df = delay_at(kk, budgets[b]), delay_at(fam, budgets[b])
            out[f"diff_vs_{tag}_{b}"] = None if dk is None or df is None else dk - df
            if b != "Bmid":
                diffs.append(out[f"diff_vs_{tag}_{b}"])
        out[f"S{1 if tag == 'fixed' else 2}"] = None if any(x is None for x in diffs) else float(np.mean(diffs))
    ck, cf = cost_at(kk, d13), cost_at(fx, d13)
    out["S3"] = None if ck is None or cf is None or cf <= 0 else 1.0 - ck / cf
    out["cost_k6_at_D13"], out["cost_fixed_at_D13"] = ck, cf
    return out


def budgets_of(arms: Arms) -> Tuple[Dict[str, float], float]:
    b13 = arms.mean("fixed_91_P2", "cost")
    b26 = arms.mean("fixed_182_P2", "cost")
    return {"B13": b13, "B26": b26, "Bmid": math.sqrt(b13 * b26)}, arms.mean("fixed_91_P2", "delay")


def bootstrap_stats(arms: Arms, cfg: Dict[str, Any], keys: List[str], k6_family: str = "k6_free") -> Dict[str, Any]:
    budgets, d13 = budgets_of(arms)
    point = primary_stats(arms, budgets, d13, None, k6_family)
    R, B = len(arms.reps), cfg["bootstrap"]["B"]
    rng = np.random.default_rng(cfg["bootstrap"]["seed"])
    draws: Dict[str, List[float]] = {k: [] for k in keys}
    dropped = {k: 0 for k in keys}
    for _ in range(B):
        counts = np.bincount(rng.integers(0, R, size=R), minlength=R).astype(float)
        st = primary_stats(arms, budgets, d13, counts, k6_family)
        for k in keys:
            if st[k] is None:
                dropped[k] += 1
            else:
                draws[k].append(st[k])
    out: Dict[str, Any] = {"budgets": budgets, "D13": d13, "point": point}
    for k in keys:
        d = np.array(draws[k])
        out[k] = {
            "point": point[k],
            "dropped_share": dropped[k] / B,
            "ci_primary": [float(np.quantile(d, cfg["bootstrap"]["alpha_primary"] / 2)), float(np.quantile(d, 1 - cfg["bootstrap"]["alpha_primary"] / 2))] if len(d) > 20 else None,
            "ci_95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))] if len(d) > 20 else None,
        }
    return out


def canary_stat(records: List[Dict[str, Any]], arms: Arms, budgets: Dict[str, float], cfg: Dict[str, Any]) -> Dict[str, Any]:
    reps = arms.reps
    fx_by_rep = {r: frontier([(arms.metrics[a]["cost"][i], arms.metrics[a]["delay"][i]) for a in arms.names if arms.family[a] == "fixed"]) for i, r in enumerate(reps)}
    can: Dict[Tuple[int, int], List[Tuple[float, float]]] = {}
    for rec in records:
        if rec["family"] == "canary" and rec["world"] == "G1":
            can.setdefault((rec["rep"], rec["shuffle"]), []).append((rec["A"]["cost"], rec["A"]["delay"]))
    per_rep: Dict[int, List[float]] = {r: [] for r in reps}
    skipped = 0
    for (r, _j), pts in sorted(can.items()):
        kf = frontier(pts)
        vals = []
        for b in ("B13", "B26"):
            dk, df = delay_at(kf, budgets[b]), delay_at(fx_by_rep[r], budgets[b])
            if dk is None or df is None:
                skipped += 1
            else:
                vals.append(dk - df)
        if vals:
            per_rep[r].append(float(np.mean(vals)))
    v = np.array([np.mean(per_rep[r]) if per_rep[r] else np.nan for r in reps])
    ok = np.isfinite(v)
    rng = np.random.default_rng(cfg["bootstrap"]["seed"] + 1)
    R = len(reps)
    d = []
    for _ in range(cfg["bootstrap"]["B"]):
        c = np.bincount(rng.integers(0, R, size=R), minlength=R).astype(float) * ok
        if c.sum() > 0:
            d.append(float((np.nan_to_num(v) * c).sum() / c.sum()))
    d = np.array(d)
    evaluable = bool(len(d) > 0)
    lo, hi = (float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))) if evaluable else (None, None)
    return {
        "evaluable": evaluable,
        "mean": float(np.nanmean(v)) if ok.any() else None,
        "ci_95": [lo, hi] if evaluable else None,
        "n_fits": int(len(can)),
        "n_budget_readings_skipped": int(skipped),
        "per_rep": [None if not np.isfinite(x) else float(x) for x in v],
        "void": bool(evaluable and hi < 0.0),
    }


def alt_cost_rescore(arms: Arms, spec: Dict[str, Any]) -> Dict[str, Any]:
    """S1 point estimate with the stored visits, panel shares and alerts rescored under other cost units."""
    cost = {}
    for a in arms.names:
        mt = arms.metrics[a]
        per_visit = spec["visit"] + sum(mt[f"panel_share_{p}"] * spec["panel"][p] for p in k6.PANELS)
        cost[a] = mt["visits"] * per_visit + mt["alerts_per_patient"] * spec["imaging"]
    mean_cost = {a: float(np.mean(cost[a])) for a in arms.names}
    mean_delay = {a: arms.mean(a, "delay") for a in arms.names}

    def fr(fam):
        return frontier([(mean_cost[a], mean_delay[a]) for a in arms.names if arms.family[a] == fam])

    fx, kk = fr("fixed"), fr("k6_free")
    b13, b26 = mean_cost["fixed_91_P2"], mean_cost["fixed_182_P2"]
    diffs = []
    for b in (b13, b26):
        dk, df = delay_at(kk, b), delay_at(fx, b)
        diffs.append(None if dk is None or df is None else dk - df)
    return {"name": spec["name"], "B13": b13, "B26": b26, "S1_point": None if any(x is None for x in diffs) else float(np.mean(diffs))}


def table_rows(arms: Arms, family: str) -> List[Dict[str, Any]]:
    out = []
    for a in arms.names:
        if arms.family[a] != family:
            continue
        mt = arms.metrics[a]
        out.append(
            {
                "arm": a,
                "params": arms.params[a],
                "cost": float(mt["cost"].mean()),
                "delay": float(mt["delay"].mean()),
                "delay_sd_over_reps": float(mt["delay"].std(ddof=1)) if len(mt["delay"]) > 1 else None,
                "missed": float(mt["missed"].mean()),
                "early_28": float(mt["early_28"].mean()),
                "screen_before_symptoms": float(mt["screen_before_symptoms"].mean()),
                "overdetection_per_100py": float(mt["overdetection_per_100py"].mean()),
                "visits": float(mt["visits"].mean()),
                "panel_share": {p: float(mt[f"panel_share_{p}"].mean()) for p in k6.PANELS},
            }
        )
    return sorted(out, key=lambda x: x["cost"])


def aggregate(payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = payload["config"]
    recs = payload["records"]
    reps = sorted({r["rep"] for r in recs})
    agg: Dict[str, Any] = {"reps": reps, "n_reps": len(reps)}
    primary: Dict[str, Any] = {}
    for scen in ("A", "B"):
        arms = Arms(recs, "G1", scen, reps, families=["fixed", "risk", "heuristic", "k6_free"])
        keys = ["S1", "S2", "S3", "diff_vs_fixed_B13", "diff_vs_fixed_B26", "diff_vs_fixed_Bmid",
                "diff_vs_risk_B13", "diff_vs_risk_B26", "diff_vs_risk_Bmid"]
        bs = bootstrap_stats(arms, cfg, keys)
        primary[scen] = bs
        primary[scen]["tables"] = {fam: table_rows(arms, fam) for fam in ("fixed", "risk", "heuristic", "k6_free")}
        # the heuristic as a point against the frontiers
        h = arms.points("heuristic")[0]
        primary[scen]["heuristic_vs_fixed_frontier"] = None if delay_at(frontier(arms.points("fixed")), h[0]) is None else h[1] - delay_at(frontier(arms.points("fixed")), h[0])
        primary[scen]["heuristic_vs_k6_frontier"] = None if delay_at(frontier(arms.points("k6_free")), h[0]) is None else h[1] - delay_at(frontier(arms.points("k6_free")), h[0])
        primary[scen]["heuristic_point"] = {"cost": h[0], "delay": h[1]}
    agg["primary"] = primary
    pa = primary["A"]
    mx = cfg["bootstrap"]["max_dropped"]

    def met(key, test):
        s = pa[key]
        if s["point"] is None or s["ci_primary"] is None or s["dropped_share"] > mx:
            return {"met": False, "reason": "not covered or too many bootstrap draws dropped"}
        return {"met": bool(test(s)), "reason": ""}

    agg["H1"] = {**pa["S1"], **met("S1", lambda s: s["ci_primary"][1] < 0.0)}
    agg["H2"] = {**pa["S2"], **met("S2", lambda s: s["ci_primary"][1] < 0.0)}
    agg["H3"] = {**pa["S3"], **met("S3", lambda s: s["ci_primary"][0] > 0.25)}
    # canary
    arms_a = Arms(recs, "G1", "A", reps, families=["fixed"])
    agg["canary"] = canary_stat(recs, arms_a, pa["budgets"], cfg)
    # variants (descriptive)
    variants = {}
    for fam in ("k6_free", "k6_P1", "k6_P2", "k6_P3", "k6_prior"):
        arms = Arms(recs, "G1", "A", reps, families=["fixed", "risk", fam])
        variants[fam] = bootstrap_stats(arms, cfg, ["diff_vs_fixed_B13", "diff_vs_fixed_B26", "diff_vs_fixed_Bmid"], k6_family=fam)
        variants[fam]["table"] = table_rows(arms, fam)
    agg["variants"] = variants
    # cross-generator (descriptive)
    cross = {}
    for w in ("G2", "G3"):
        arms = Arms(recs, w, "A", reps, families=["fixed", "risk", "heuristic", "k6_free"])
        cross[w] = bootstrap_stats(arms, cfg, ["S1", "S2", "S3"])
        cross[w]["tables"] = {fam: table_rows(arms, fam) for fam in ("fixed", "risk", "heuristic", "k6_free")}
    agg["cross_generator"] = cross
    # cost units
    arms = Arms(recs, "G1", "A", reps, families=["fixed", "risk", "k6_free"])
    agg["cost_unit_sensitivity"] = [alt_cost_rescore(arms, s) for s in cfg["alt_cost_units"]]
    # metadata summaries
    meta = payload["meta"]
    agg["calibration"] = {
        "ece_mean": {h: float(np.mean([m["calibration_G1"]["ece"][h] for m in meta])) for h in meta[0]["calibration_G1"]["ece"]},
        "brier_mean": {h: float(np.mean([m["calibration_G1"]["brier"][h] for m in meta])) for h in meta[0]["calibration_G1"]["brier"]},
        "reliability_182": _pool_reliability([m["calibration_G1"]["reliability_182"] for m in meta]),
    }
    st = [m["stability"] for m in meta if m.get("stability")]
    agg["stability"] = {
        "share_interval_moves_more_than_one_step": float(np.mean([s["share_interval_moves_more_than_one_step"] for s in st])) if st else None,
        "share_panel_changes": float(np.mean([s["share_panel_changes"] for s in st])) if st else None,
        "decisions_per_rep": float(np.mean([s["n_decisions"] for s in st])) if st else None,
    }
    agg["training"] = {
        "rows_mean": float(np.mean([m["n_rows"] for m in meta])),
        "sensitivity_mean": {p: float(np.mean([m["sensitivity"][p] for m in meta])) for p in k6.PANELS},
        "false_alert_mean": {p: float(np.mean([m["false_alert"][p] for m in meta])) for p in k6.PANELS},
    }
    agg["worlds"] = {
        w: {
            "n_eligible_mean": float(np.mean([m["test_worlds"][w]["n_eligible"] for m in meta])),
            "n_generated": int(meta[0]["test_worlds"][w]["n_generated"]),
        }
        for w in ("G1", "G2", "G3")
    }
    pres = [rec["A"] for rec in recs if rec["arm"] == "fixed_91_P2" and rec["world"] == "G1"]
    agg["presentations"] = {"total": int(sum(p["presentations"] for p in pres)), "burden_below_12": int(sum(p["presentations_below_12"] for p in pres))}
    agg["delay_cohort_mean"] = float(np.mean([p["n_delay_cohort"] for p in pres]))
    return agg


def _pool_reliability(tables: List[List[Dict[str, Any]]]) -> List[Dict[str, float]]:
    n_bins = min(len(t) for t in tables)
    out = []
    for i in range(n_bins):
        w = np.array([t[i]["n"] for t in tables], dtype=float)
        out.append(
            {
                "bin": i + 1,
                "mean_predicted": float(np.average([t[i]["mean_predicted"] for t in tables], weights=w)),
                "mean_observed": float(np.average([t[i]["mean_observed"] for t in tables], weights=w)),
                "n": int(w.sum()),
            }
        )
    return out


# -------------------------------------------------------------------------------------------------
# Report (a pure function of results.json)
# -------------------------------------------------------------------------------------------------
def f(x: Optional[float], d: int = 1) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def ci(c: Optional[List[float]], d: int = 1) -> str:
    return "n/a" if not c else f"[{c[0]:.{d}f}, {c[1]:.{d}f}]"


def render_report(res: Dict[str, Any]) -> str:
    a = res["aggregate"]
    cfg = res["config"]
    pa = a["primary"]["A"]
    L: List[str] = []
    w = L.append
    w("# EXP-K6-001 report (written by `run.py`; every number below is computed from `results.json`)")
    w("")
    w("> SYNTHETIC data only. Costs are in assumed units (PREREG section 3), not money. Delay is days from true clinical recurrence "
      "to detection (negative = earlier). Nothing here is evidence about real patients; ESMO guidance (E25) does not recommend "
      "routine markers in asymptomatic patients.")
    w("")
    w(f"Code hash `{res['code_hash']}`; {a['n_reps']} frozen replications; seeds base {res['seed_base']}; run time {res.get('run_seconds')} s; "
      f"bootstrap B = {cfg['bootstrap']['B']} over replications.")
    w("")
    cn = a["canary"]
    w("## 1. Verdicts")
    w("")
    w(f"- **Canary (leakage, one-sided):** mean K6-with-shuffled-labels minus fixed frontier = {f(cn['mean'])} days "
      f"(95% interval {ci(cn['ci_95'])}; {cn['n_fits']} fits; {cn['n_budget_readings_skipped']} budget readings skipped). "
      f"**{'VOID: the upper end is below 0' if cn['void'] else ('Not void' if cn['evaluable'] else 'NOT EVALUABLE: no frontier covered a budget')}** "
      "(rule: void if the upper end of the interval is below 0).")
    for h, name, rule in (("H1", "K6 beats fixed schedules at equal cost", "upper bound of the interval < 0"),
                          ("H2", "K6 beats the risk-triggered schedule at equal cost", "upper bound of the interval < 0"),
                          ("H3", "cost saving at the delay of the 3-month schedule", "lower bound of the interval > 0.25")):
        x = a[h]
        unit = "" if h == "H3" else " days"
        d = 3 if h == "H3" else 1
        w(f"- **{h} ({name}):** {f(x['point'], d)}{unit}, Bonferroni interval {ci(x['ci_primary'], d)}, dropped draws {x['dropped_share']:.3f}; "
          f"rule: {rule}; **{'MET' if x['met'] else 'NOT MET'}**{(' (' + x['reason'] + ')') if x['reason'] else ''}.")
    w("")
    kill = "H1 not met: K6 is not claimed to beat fixed schedules." if not a["H1"]["met"] else (
        "H1 met, H2 not met: risk-triggered schedule suggestions only." if not a["H2"]["met"] else
        "H1 and H2 met: still a simulation claim and a suggestion with reasons shown, nothing clinical.")
    w(f"**Decision under the pre-registered kill rule:** {kill}")
    w("")
    w("## 2. Strongest baselines first (G1, scenario A: symptomatic presentation allowed)")
    w("")
    w("Budgets (cost units per patient, pooled frozen cost of the named schedules): "
      f"B13 = {f(pa['budgets']['B13'], 2)} (fixed 91 days, P2), B26 = {f(pa['budgets']['B26'], 2)} (fixed 182 days, P2), "
      f"Bmid = {f(pa['budgets']['Bmid'], 2)}; D13 = {f(pa['D13'])} days (delay of fixed 91 days, P2).")
    w("")
    for fam, title in (("fixed", "Fixed schedules (24 arms; frontier arms marked *)"), ("risk", "Risk-triggered (48 arms; frontier arms marked *)"),
                       ("heuristic", "Stage heuristic"), ("k6_free", "K6 (17 weights, panels free)")):
        rows = pa["tables"][fam]
        front = {(round(c, 9), round(d, 9)) for c, d in frontier([(r["cost"], r["delay"]) for r in rows])}
        w(f"### {title}")
        w("")
        w("| arm | cost | delay (d) | missed | detected >= 28 d early | overdetection /100 py | visits | panel P1/P2/P3 |")
        w("|---|---|---|---|---|---|---|---|")
        for r in rows:
            star = "*" if (round(r["cost"], 9), round(r["delay"], 9)) in front else ""
            ps = r["panel_share"]
            w(f"| {r['arm']}{star} | {f(r['cost'], 2)} | {f(r['delay'])} | {f(r['missed'], 3)} | {f(r['early_28'], 3)} | "
              f"{f(r['overdetection_per_100py'])} | {f(r['visits'], 1)} | {ps['P1']:.2f}/{ps['P2']:.2f}/{ps['P3']:.2f} |")
        w("")
    w("## 3. K6 minus each frontier at equal cost (days; negative = K6 earlier)")
    w("")
    w("| comparison | at B13 | at B26 | at Bmid |")
    w("|---|---|---|---|")
    for tag, nm in (("fixed", "fixed frontier"), ("risk", "risk-triggered frontier")):
        cells = []
        for b in ("B13", "B26", "Bmid"):
            x = pa[f"diff_vs_{tag}_{b}"]
            cells.append(f"{f(x['point'])} {ci(x['ci_95'])}")
        w(f"| K6 - {nm} | " + " | ".join(cells) + " |")
    w("")
    w(f"The heuristic point is {f(pa['heuristic_vs_fixed_frontier'])} days against the fixed frontier at its cost ({f(pa['heuristic_point']['cost'], 2)} units) and "
      f"{f(pa['heuristic_vs_k6_frontier'])} days against the K6 frontier (n/a = outside the frontier's cost range).")
    w("")
    w("## 4. Scenario B (screening only, no symptomatic presentation; descriptive)")
    w("")
    pb = a["primary"]["B"]
    w(f"S1 = {f(pb['S1']['point'])} {ci(pb['S1']['ci_95'])}; S2 = {f(pb['S2']['point'])} {ci(pb['S2']['ci_95'])}; S3 = {f(pb['S3']['point'], 3)} {ci(pb['S3']['ci_95'], 3)} "
      f"(95% intervals; budgets B13 = {f(pb['budgets']['B13'], 2)}, B26 = {f(pb['budgets']['B26'], 2)}).")
    w("")
    w("## 5. Ablations by panel composition and by information (descriptive; K6 minus fixed frontier, days)")
    w("")
    w("| K6 variant | at B13 | at B26 | at Bmid |")
    w("|---|---|---|---|")
    for fam, d in a["variants"].items():
        cells = [f"{f(d['diff_vs_fixed_' + b]['point'])} {ci(d['diff_vs_fixed_' + b]['ci_95'])}" for b in ("B13", "B26", "Bmid")]
        w(f"| {fam} | " + " | ".join(cells) + " |")
    w("")
    w("## 6. Cross-generator (hazard model, thresholds and panel table trained on G1 only; descriptive; 95% intervals)")
    w("")
    w("| test generator | budgets B13 / B26 | S1 (K6 - fixed, days) | S2 (K6 - risk, days) | S3 (saving) |")
    w("|---|---|---|---|---|")
    for g, d in a["cross_generator"].items():
        w(f"| {g} | {f(d['budgets']['B13'], 2)} / {f(d['budgets']['B26'], 2)} | {f(d['S1']['point'])} {ci(d['S1']['ci_95'])} | "
          f"{f(d['S2']['point'])} {ci(d['S2']['ci_95'])} | {f(d['S3']['point'], 3)} {ci(d['S3']['ci_95'], 3)} |")
    w("")
    w("## 7. Cost-unit sensitivity (stored runs rescored; K6 not re-planned; point estimates)")
    w("")
    w("| cost units | B13 | B26 | S1 (days) |")
    w("|---|---|---|---|")
    for s in a["cost_unit_sensitivity"]:
        w(f"| {s['name']} | {f(s['B13'], 2)} | {f(s['B26'], 2)} | {f(s['S1_point'])} |")
    w("")
    w("## 8. Hazard calibration on G1 test worlds, random-schedule rows (descriptive)")
    w("")
    cal = a["calibration"]
    w("| horizon (days) | ECE | Brier |")
    w("|---|---|---|")
    for h in cal["ece_mean"]:
        w(f"| {h} | {f(cal['ece_mean'][h], 4)} | {f(cal['brier_mean'][h], 4)} |")
    w("")
    w("Reliability of G(182), pooled over replications, ten equal-count bins:")
    w("")
    w("| bin | n | mean predicted | mean observed |")
    w("|---|---|---|---|")
    for b in cal["reliability_182"]:
        w(f"| {b['bin']} | {b['n']} | {f(b['mean_predicted'], 3)} | {f(b['mean_observed'], 3)} |")
    w("")
    w("## 9. Policy stability, training and worlds")
    w("")
    st = a["stability"]
    w(f"- Stability (K6, w = {cfg['stability']['w']}, knots perturbed by up to {cfg['stability']['amplitude']}): the interval moves by more than one grid step in "
      f"{f(st['share_interval_moves_more_than_one_step'], 3)} of decisions and the panel changes in {f(st['share_panel_changes'], 3)} "
      f"({f(st['decisions_per_rep'], 0)} decisions per replication).")
    tr = a["training"]
    w(f"- Training rows per replication (mean): {f(tr['rows_mean'], 0)}. Panel table (mean): sensitivity P1/P2/P3 = "
      + "/".join(f(tr['sensitivity_mean'][p], 3) for p in k6.PANELS) + "; false-alert probability = "
      + "/".join(f(tr['false_alert_mean'][p], 3) for p in k6.PANELS) + ".")
    wd = a["worlds"]
    w("- Eligible test patients per replication (mean) out of "
      + ", ".join(f"{wd[g]['n_generated']} generated: {g} {f(wd[g]['n_eligible_mean'], 0)}" for g in wd)
      + f"; delay cohort per arm (mean, G1) {f(a['delay_cohort_mean'], 0)}.")
    pr = a["presentations"]
    w(f"- Symptomatic presentations at burden below 12 (assumption check, should be 0): {pr['burden_below_12']} of {pr['total']} (fixed 91-day arm, G1, all replications).")
    w("")
    return "\n".join(L) + "\n"


# -------------------------------------------------------------------------------------------------
# Modes
# -------------------------------------------------------------------------------------------------
def refuse_existing_evidence(mode: str) -> None:
    outputs = {
        "dev": (OUT / "dev_results.json",),
        "frozen": (OUT / "results.json", OUT / "REPORT.md"),
        "rerender": (OUT / "REPORT.md",),
    }
    if mode not in outputs:
        raise ValueError(f"unknown persistent K6 mode: {mode}")
    existing = [path.name for path in outputs[mode] if path.exists()]
    if existing:
        names = ", ".join(existing)
        raise RuntimeError(f"EXP-K6-001 {mode} mode refuses to overwrite existing evidence: {names}")


def build_results(kind: str, reps: List[int], scope: str, workers: int, tag: str) -> Dict[str, Any]:
    t0 = time.time()
    done = execute([(kind, r, scope) for r in reps], tag, workers)
    merged = merge(done)
    payload = {
        "config": design(scope),
        "records": merged["records"],
        "meta": merged["meta"],
        "seed_base": base_seed(kind, 0),
        "workers": workers,
        "code_hash": code_hash(),
    }
    payload["aggregate"] = aggregate(payload)
    payload["run_seconds"] = int(time.time() - t0)
    return payload


def mode_dev(workers: int) -> None:
    refuse_existing_evidence("dev")
    res = build_results("dev", list(range(CONFIG["seeds"]["dev"]["n"])), "full", workers, "dev")
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1) + "\n")
    print("[dev] dev_results.json written (development replications; debugging, not evidence)", flush=True)


def mode_frozen(workers: int) -> None:
    refuse_existing_evidence("frozen")
    res = build_results("frozen", list(range(CONFIG["seeds"]["frozen"]["n"])), "full", workers, "frozen")
    (OUT / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    (OUT / "REPORT.md").write_text(render_report(res))
    print("[frozen] results.json and REPORT.md written", flush=True)


def mode_smoke(workers: int) -> Dict[str, Any]:
    import tempfile

    global WORK
    with tempfile.TemporaryDirectory() as d:
        WORK = Path(d)
        res = build_results("smoke", [0, 1], "smoke", workers, "smoke")
        render_report(res)
        return res


def mode_rerender() -> None:
    refuse_existing_evidence("rerender")
    res = json.loads((OUT / "results.json").read_text())
    res["aggregate"] = json.loads(json.dumps(aggregate(res)))
    (OUT / "REPORT.md").write_text(render_report(res))


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    for k in ("dev", "frozen", "smoke", "rerender"):
        g.add_argument(f"--{k}", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.dev:
        mode_dev(a.workers)
    elif a.frozen:
        mode_frozen(a.workers)
    elif a.smoke:
        res = mode_smoke(a.workers)
        print(json.dumps({k: res["aggregate"][k] for k in ("H1", "H2", "H3")}, indent=1, default=str))
    else:
        mode_rerender()
    return 0


if __name__ == "__main__":
    sys.exit(main())
