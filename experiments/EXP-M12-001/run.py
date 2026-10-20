#!/usr/bin/env python3
# ruff: noqa: I001
"""EXP-M12-001 runner. Specification: experiments/EXP-M12-001/PREREG.md.

    uv run python experiments/EXP-M12-001/run.py --dev
    uv run python experiments/EXP-M12-001/run.py --frozen
    uv run python experiments/EXP-M12-001/run.py --smoke
    uv run python experiments/EXP-M12-001/run.py --rerender
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import xgboost  # noqa: F401  # import before other numeric stacks (OpenMP)

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for pkg in ("vigil-sim", "vigil-ml", "vigil-core", "vigil-eval"):
    sys.path.insert(0, str(ROOT / "packages" / pkg))

from vigil_eval.metrics import (  # noqa: E402
    compute_calibration_curve,
    ipcw_brier_score,
    ipcw_time_dependent_roc_auc,
    survival_decision_curve_analysis,
)
from vigil_ml import m12  # noqa: E402
from vigil_ml.baselines import GradientBoostingBaseline  # noqa: E402
from vigil_ml.features import WindowedFeatureExtractor  # noqa: E402
from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402

OUT = Path(__file__).resolve().parent
HORIZON = 365.0
DURATION = 730.0
TAU = 0.07
DELTA = 1.0 / 910.0
THRESHOLD = 0.10
BOOT_B = 2000
BOOT_SEED = 20261220
FAMILY = 2

SITES: List[Dict[str, Any]] = [
    {"id": "A", "train": 400, "test": 200, "interval": 45.0, "p": 0.00},
    {"id": "B", "train": 200, "test": 100, "interval": 90.0, "p": 0.05},
    {"id": "C", "train": 80, "test": 80, "interval": 180.0, "p": 0.25},
    {"id": "D", "train": 150, "test": 80, "interval": 60.0, "p": 0.00},
    {"id": "E", "train": 80, "test": 80, "interval": 120.0, "p": 0.20},
]

CONFIG: Dict[str, Any] = {
    "sites": SITES,
    "duration_days": DURATION,
    "horizon_days": HORIZON,
    "tau": TAU,
    "delta": DELTA,
    "threshold": THRESHOLD,
    "rounds": m12.ROUNDS,
    "local_epochs_fed": m12.LOCAL_EPOCHS_FED,
    "epochs_solo": m12.EPOCHS_SOLO,
    "batch": m12.BATCH,
    "lr": m12.LR,
    "clip_c": m12.CLIP_C,
    "sigma": m12.NOISE_MULT,
    "canary_sigma": 100.0,
    "canary_void_mean_auc": 0.60,
    "n_dev": 3,
    "n_frozen": 10,
    "seeds": {"dev": {"base": 1100, "step": 100}, "frozen": {"base": 20261220, "step": 100}},
}


def seed_base(kind: str, r: int) -> int:
    s = CONFIG["seeds"][kind]
    return int(s["base"] + s["step"] * r)


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, float)):
        x = float(obj)
        return x if math.isfinite(x) else None
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


def prefix_ids(frame: pd.DataFrame, site: str) -> pd.DataFrame:
    out = frame.copy()
    out["patient_id"] = site + ":" + out["patient_id"].astype(str)
    return out


def apply_site(obs: pd.DataFrame, beta: float, p_miss: float, rng: np.random.Generator) -> pd.DataFrame:
    o = obs.copy()
    scale = math.exp(beta)
    for col in ("ca_15_3", "cea"):
        if col not in o.columns:
            continue
        vals = np.array(o[col].to_numpy(dtype=float), copy=True)
        seen = ~np.isnan(vals)
        vals[seen] = vals[seen] * scale
        if p_miss > 0.0:
            drop = seen & (rng.random(len(vals)) < p_miss)
            vals[drop] = np.nan
        o[col] = vals
    return o


def generate_site(
    site: Dict[str, Any], n: int, seed: int, beta: float, rng_miss: np.random.Generator
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=seed).generate_cohort(
        num_patients=n, duration_days=DURATION, nominal_interval_days=float(site["interval"])
    )
    obs = prefix_ids(cohort.to_observations_dataframe(), site["id"])
    pts = prefix_ids(cohort.to_patients_dataframe(), site["id"])
    obs = apply_site(obs, beta, float(site["p"]), rng_miss)
    return obs, pts


def landmark_tables(
    obs: pd.DataFrame, pts: pd.DataFrame
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, int]:
    X, y, times, events = WindowedFeatureExtractor().transform_cohort(pts, obs, HORIZON)
    if X.empty:
        empty = pd.DataFrame()
        z = np.zeros(0, dtype=float)
        return empty, z, z, z, int(pts["patient_id"].nunique()) if len(pts) else 0
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)
    keep: List[int] = []
    seen = 0
    for _pid, grp in X.groupby("patient_id", sort=False):
        seen += 1
        ok = grp[(grp["eval_day"] >= 90.0) & (grp["eval_day"] <= 365.0)]
        if len(ok) == 0:
            continue
        keep.append(int(ok["eval_day"].idxmax()))
    dropped = seen - len(keep)
    if not keep:
        empty = pd.DataFrame()
        z = np.zeros(0, dtype=float)
        return empty, z, z, z, dropped
    X = X.loc[keep].reset_index(drop=True)
    y_arr = y.loc[keep].to_numpy(dtype=np.float32)
    t_arr = np.asarray(times, dtype=float)[keep]
    e_arr = np.asarray(events, dtype=float)[keep]
    return X, y_arr, t_arr, e_arr, dropped


def arrays_from(
    X: pd.DataFrame, cols: Optional[List[str]] = None
) -> Tuple[np.ndarray, List[str]]:
    feat = X.drop(columns=[c for c in ("patient_id",) if c in X.columns]).fillna(0.0)
    if cols is None:
        cols = list(feat.columns)
    feat = feat.reindex(columns=cols, fill_value=0.0)
    return feat.to_numpy(dtype=np.float32), cols


def score_pack(
    prob: np.ndarray, y: np.ndarray, times: np.ndarray, events: np.ndarray
) -> Dict[str, float]:
    if len(prob) == 0:
        raise ValueError("cannot score an empty evaluation cohort")
    if not (len(prob) == len(y) == len(times) == len(events)):
        raise ValueError("probabilities, labels, follow-up, and events must have equal lengths")
    if not np.isfinite(prob).all() or np.any((prob < 0.0) | (prob > 1.0)):
        raise ValueError("probabilities must be finite and within [0, 1]")
    if not np.isfinite(y).all() or not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("calibration requires known binary horizon labels for every row")
    auc = float(ipcw_time_dependent_roc_auc(prob, times, events, HORIZON))
    brier = float(ipcw_brier_score(prob, times, events, HORIZON))
    ece = float(
        compute_calibration_curve(prob, y, n_bins=10, strategy="quantile").expected_calibration_error
    )
    dca = survival_decision_curve_analysis(
        prob, times, events, HORIZON, thresholds=np.array([THRESHOLD], dtype=float)
    )
    return {"auc": auc, "brier": brier, "ece": ece, "nb": float(dca.net_benefit_model[0])}


def concat(parts: Sequence[np.ndarray]) -> np.ndarray:
    if not parts:
        return np.zeros((0, 1), dtype=np.float32)
    return np.concatenate(list(parts), axis=0)


def percentile_ci(values: np.ndarray, lo: float, hi: float, rng: np.random.Generator) -> List[float]:
    n = len(values)
    if n == 0:
        return [float("nan"), float("nan")]
    stats = np.empty(BOOT_B, dtype=float)
    for b in range(BOOT_B):
        idx = rng.integers(0, n, n)
        stats[b] = float(np.mean(values[idx]))
    return [float(np.percentile(stats, 100.0 * lo)), float(np.percentile(stats, 100.0 * hi))]


def replication(job: Tuple[str, int, bool]) -> Dict[str, Any]:
    kind, r, smoke = job
    t0 = time.time()
    sites = list(CONFIG["sites"])
    rounds = int(CONFIG["rounds"])
    e_fed = int(CONFIG["local_epochs_fed"])
    e_solo = int(CONFIG["epochs_solo"])
    if smoke:
        sites = [
            {"id": "A", "train": 24, "test": 16, "interval": 45.0, "p": 0.00},
            {"id": "C", "train": 24, "test": 16, "interval": 180.0, "p": 0.10},
            {"id": "E", "train": 24, "test": 16, "interval": 120.0, "p": 0.10},
        ]
        rounds, e_fed, e_solo = 2, 1, 1
    s = seed_base(kind, r)
    rng_beta = np.random.default_rng(s + 10)
    betas = {st["id"]: float(rng_beta.normal(0.0, TAU)) for st in sites}
    train_X: Dict[str, np.ndarray] = {}
    train_y: Dict[str, np.ndarray] = {}
    test_X: Dict[str, np.ndarray] = {}
    test_y: Dict[str, np.ndarray] = {}
    test_t: Dict[str, np.ndarray] = {}
    test_e: Dict[str, np.ndarray] = {}
    dropped = {}
    n_train = {}
    n_test = {}
    cols: Optional[List[str]] = None
    offset = {"A": 0, "B": 2, "C": 4, "D": 6, "E": 8}
    extractor_tables_train = []
    for st in sites:
        sid = st["id"]
        rng_miss_tr = np.random.default_rng(s + 20 + offset[sid])
        rng_miss_te = np.random.default_rng(s + 21 + offset[sid])
        obs_tr, pts_tr = generate_site(st, int(st["train"]), s + offset[sid], betas[sid], rng_miss_tr)
        obs_te, pts_te = generate_site(
            st, int(st["test"]), s + offset[sid] + 1, betas[sid], rng_miss_te
        )
        Xtr, ytr, _ttr, _etr, dtr = landmark_tables(obs_tr, pts_tr)
        Xte, yte, tte, ete, dte = landmark_tables(obs_te, pts_te)
        dropped[sid] = {"train": dtr, "test": dte}
        arr_tr, cols = arrays_from(Xtr, cols)
        arr_te, cols = arrays_from(Xte, cols)
        train_X[sid], train_y[sid] = arr_tr, ytr
        test_X[sid], test_y[sid], test_t[sid], test_e[sid] = arr_te, yte, tte, ete
        n_train[sid] = int(arr_tr.shape[0])
        n_test[sid] = int(arr_te.shape[0])
        extractor_tables_train.append(Xtr)
    d_in = int(cols and len(cols) or 1)
    init = m12.init_mlp(d_in, np.random.default_rng(s + 11))
    ids = [st["id"] for st in sites]
    xs = [train_X[i] for i in ids]
    ys = [train_y[i] for i in ids]
    x_pool = concat(xs)
    y_pool = concat(ys)
    x_te = concat([test_X[i] for i in ids])
    y_te = concat([test_y[i] for i in ids])
    t_te = concat([test_t[i] for i in ids])
    e_te = concat([test_e[i] for i in ids])

    w_c = m12.train_sgd(init, x_pool, y_pool, e_solo, m12.BATCH, m12.LR, np.random.default_rng(s + 12))
    w_l = {
        i: m12.train_sgd(init, train_X[i], train_y[i], e_solo, m12.BATCH, m12.LR, np.random.default_rng(s + 12))
        for i in ids
    }
    w_f, _ = m12.fedavg_train(
        xs, ys, init, rounds, e_fed, m12.BATCH, m12.LR,
        np.random.default_rng(s + 12), np.random.default_rng(s + 13),
    )
    w_d, dp_steps = m12.fedavg_train(
        xs, ys, init, rounds, e_fed, m12.BATCH, m12.LR,
        np.random.default_rng(s + 12), np.random.default_rng(s + 13),
        dp=(m12.CLIP_C, m12.NOISE_MULT, np.random.default_rng(s + 14)),
    )
    w_canary, _ = m12.fedavg_train(
        xs, ys, init, rounds, e_fed, m12.BATCH, m12.LR,
        np.random.default_rng(s + 12), np.random.default_rng(s + 13),
        dp=(m12.CLIP_C, 100.0, np.random.default_rng(s + 15)),
    )

    df_tr = pd.concat([t.drop(columns=["patient_id"], errors="ignore") for t in extractor_tables_train], ignore_index=True)
    df_tr = df_tr.reindex(columns=cols, fill_value=0.0).fillna(0.0)
    b4 = GradientBoostingBaseline(random_state=s + 11)
    b4.fit(df_tr, pd.Series(y_pool))
    df_te = pd.DataFrame(x_te, columns=cols)
    p_b4 = b4.predict_risk(df_te)

    pooled = {
        "C": score_pack(m12.predict_proba(w_c, x_te), y_te, t_te, e_te),
        "F": score_pack(m12.predict_proba(w_f, x_te), y_te, t_te, e_te),
        "D": score_pack(m12.predict_proba(w_d, x_te), y_te, t_te, e_te),
        "B4": score_pack(p_b4, y_te, t_te, e_te),
    }
    canary = score_pack(m12.predict_proba(w_canary, x_te), y_te, t_te, e_te)
    per_site: Dict[str, Any] = {}
    for i in ids:
        xt, yt, tt, et = test_X[i], test_y[i], test_t[i], test_e[i]
        per_site[i] = {
            "L": score_pack(m12.predict_proba(w_l[i], xt), yt, tt, et),
            "C": score_pack(m12.predict_proba(w_c, xt), yt, tt, et),
            "F": score_pack(m12.predict_proba(w_f, xt), yt, tt, et),
            "D": score_pack(m12.predict_proba(w_d, xt), yt, tt, et),
        }
    small = [i for i in ("C", "E") if i in per_site]
    g_ce = float(np.mean([per_site[i]["C"]["auc"] - per_site[i]["L"]["auc"] for i in small])) if small else 0.0
    eq_f = float(np.mean([per_site[i]["F"]["auc"] - per_site[i]["L"]["auc"] for i in small])) if small else 0.0
    eq_d = float(np.mean([per_site[i]["D"]["auc"] - per_site[i]["L"]["auc"] for i in small])) if small else 0.0
    privacy = {
        i: m12.privacy_ledger_row(n_train[i], int(dp_steps[k]), m12.NOISE_MULT, m12.CLIP_C, DELTA)
        for k, i in enumerate(ids)
    }
    d_f = pooled["C"]["auc"] - pooled["F"]["auc"]
    d_d = pooled["C"]["auc"] - pooled["D"]["auc"]
    return to_jsonable(
        {
            "r": r,
            "kind": kind,
            "seed_base": s,
            "feature_dim": d_in,
            "betas": betas,
            "n_train": n_train,
            "n_test": n_test,
            "dropped": dropped,
            "pooled": pooled,
            "per_site": per_site,
            "D_F": d_f,
            "D_D": d_d,
            "Dnb_D": pooled["C"]["nb"] - pooled["D"]["nb"],
            "G_CE": g_ce,
            "equity_F": eq_f,
            "equity_D": eq_d,
            "privacy": privacy,
            "headline_eps": max(v["eps"] for v in privacy.values()) if privacy else None,
            "canary_auc": canary["auc"],
            "wall_s": time.time() - t0,
        }
    )


def aggregate(reps: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(reps)
    def col(key: str) -> np.ndarray:
        return np.array([float(r[key]) for r in reps], dtype=float)

    def mean_ci(values: np.ndarray, family: bool) -> Dict[str, Any]:
        rng = np.random.default_rng(BOOT_SEED)
        if family:
            lo, hi = 0.05 / FAMILY / 2.0, 1.0 - 0.05 / FAMILY / 2.0
        else:
            lo, hi = 0.025, 0.975
        ci = percentile_ci(values, lo, hi, rng)
        return {
            "mean": float(np.mean(values)),
            "ci": ci,
            "ci_kind": "bonferroni" if family else "95pct",
        }

    d_f = col("D_F")
    d_d = col("D_D")
    dnb = col("Dnb_D")
    g_ce = col("G_CE")
    canary = col("canary_auc")
    auc = {arm: float(np.mean([r["pooled"][arm]["auc"] for r in reps])) for arm in ("B4", "C", "F", "D")}
    h2 = mean_ci(d_f, True)
    h3 = mean_ci(d_d, True)
    h1 = mean_ci(g_ce, False)
    h4 = mean_ci(dnb, False)
    void = bool(float(np.mean(canary)) > CONFIG["canary_void_mean_auc"])
    h2_met = (not void) and h2["mean"] <= 0.03 and h2["ci"][1] <= 0.03
    h3_met = (not void) and h3["mean"] <= 0.03 and h3["ci"][1] <= 0.03
    h4_met_desc = (not void) and h4["mean"] <= 0.03 and h4["ci"][1] <= 0.03
    return {
        "n_replications": n,
        "mean_pooled_auc": auc,
        "D_F": h2,
        "D_D": h3,
        "Dnb_D": h4,
        "G_CE": h1,
        "equity_F": mean_ci(col("equity_F"), False),
        "equity_D": mean_ci(col("equity_D"), False),
        "canary_mean_auc": float(np.mean(canary)),
        "void": void,
        "headline_eps_mean": float(np.mean([r["headline_eps"] for r in reps])),
        "hypotheses": {
            "H1": {"met": bool((not void) and h1["ci"][0] > 0.10), "detail": h1, "role": "descriptive"},
            "H2": {"met": bool(h2_met), "detail": h2, "role": "primary"},
            "H3": {"met": bool(h3_met), "detail": h3, "role": "primary-kill"},
            "H4": {"met": bool(h4_met_desc), "detail": h4, "role": "descriptive"},
            "void": void,
            "kill_rule": {
                "fires": bool(void or not h3_met),
                "fallback": "federated evaluation only",
            },
        },
        "per_site_mean_auc": {
            sid: {
                arm: float(np.mean([r["per_site"][sid][arm]["auc"] for r in reps if sid in r["per_site"]]))
                for arm in ("L", "C", "F", "D")
            }
            for sid in sorted({s for r in reps for s in r["per_site"]})
        },
    }


def render_report(res: Dict[str, Any], elapsed: float) -> str:
    a = res["aggregate"]
    h = a["hypotheses"]
    L: List[str] = []
    L.append("# EXP-M12-001 report (written by `run.py`; do not edit)\n")
    L.append(
        "> **SYNTHETIC DATA ONLY.** Five simulated sites with analyser offsets, visit frequency and "
        "missingness. FederatedAveraging is in-process (no network). DP-SGD and the moments accountant "
        "are implemented in `vigil_ml.m12`. (ε, δ)-DP is not an NDPA/GDPR determination. "
        "Pre-registration: `PREREG.md`.\n"
    )
    L.append(
        f"Replications: {a['n_replications']} ({res.get('kind')}). "
        f"Mean headline ε̂ (max over sites, δ = 1/910): {a['headline_eps_mean']:.3f}. "
        f"Canary (σ = 100) mean pooled AUC: {a['canary_mean_auc']:.4f}. "
        f"**VOID:** {a['void']}. Run time {elapsed:.0f} s.\n"
    )
    L.append("## Hypotheses (computed)\n")
    L.append("| Hypothesis | Result | Detail |\n|---|---|---|")

    def row(name: str, rec: Dict[str, Any], extra: str) -> str:
        tag = "VOID" if a["void"] else ("met" if rec["met"] else "NOT met")
        d = rec["detail"]
        return (
            f"| {name} | {tag} | mean {d['mean']:.4f}, "
            f"{d['ci_kind']} interval [{d['ci'][0]:.4f}, {d['ci'][1]:.4f}] {extra} |"
        )

    L.append(row("H1 (local silos, descriptive)", h["H1"], "; lower bound > 0.10 would support silo failure"))
    L.append(row("H2 (FedAvg within 3 pp of central)", h["H2"], "; need point and Bonferroni UB ≤ 0.03"))
    L.append(row("H3 (FedAvg+DP within 3 pp of central) — kill", h["H3"], "; need point and Bonferroni UB ≤ 0.03"))
    L.append(row("H4 (NB@0.10 drop, descriptive)", h["H4"], "; same 0.03 rule, not in the primary family"))
    kr = h["kill_rule"]
    L.append(
        f"\n**Kill rule fires:** {kr['fires']}. Fallback if it fires: {kr['fallback']}. "
        "Nothing here is wired into a pipeline or a pilot.\n"
    )
    L.append("## Strongest baseline first (mean pooled IPCW AUC at 365 days)\n")
    L.append("| Arm | Mean pooled AUC |\n|---|---|")
    for arm, label in (("B4", "B4 gradient boosting (descriptive ceiling)"), ("C", "C central MLP"),
                       ("F", "F FedAvg"), ("D", "D FedAvg + DP-SGD")):
        L.append(f"| {label} | {a['mean_pooled_auc'][arm]:.4f} |")
    L.append("\n## Per-site mean IPCW AUC\n")
    L.append("| Site | L local | C central | F FedAvg | D FedAvg+DP |\n|---|---|---|---|---|")
    for sid, rowv in a["per_site_mean_auc"].items():
        L.append(
            f"| {sid} | {rowv['L']:.4f} | {rowv['C']:.4f} | {rowv['F']:.4f} | {rowv['D']:.4f} |"
        )
    L.append("\n## Drops versus central (pooled)\n")
    L.append("| Contrast | Mean | Interval |\n|---|---|---|")
    for key, label in (("D_F", "AUC_C − AUC_F"), ("D_D", "AUC_C − AUC_D"), ("Dnb_D", "NB_C − NB_D at 0.10")):
        d = a[key]
        L.append(f"| {label} | {d['mean']:.4f} | {d['ci_kind']} [{d['ci'][0]:.4f}, {d['ci'][1]:.4f}] |")
    L.append(
        "\n## Limits (carried from the pre-registration)\n"
        "Synthetic data; one MLP; one-row-per-patient DP; in-process FedAvg (no Flower process); "
        "no Opacus; no real multi-site data; not a legal privacy claim; not a pilot.\n"
    )
    return "\n".join(L) + "\n"


def run(kind: str, n_rep: int, workers: int, smoke: bool = False) -> List[Dict[str, Any]]:
    jobs = [(kind, r, smoke) for r in range(n_rep)]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(replication, jobs))
    return [replication(j) for j in jobs]


def assert_no_prior_frozen_access() -> None:
    outputs = (OUT / "results.json", OUT / "REPORT.md")
    if any(path.exists() for path in outputs):
        raise RuntimeError("EXP-M12-001 output already exists; frozen test access cannot be repeated")
    access_log = ROOT / "data/audit/frozen_test_access.jsonl"
    if not access_log.exists():
        return
    for line in access_log.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        if record.get("dataset_name", "").startswith("SYNTHETIC-EXP-M12-001-") or record.get(
            "caller"
        ) == "experiments/EXP-M12-001/run.py":
            raise RuntimeError("EXP-M12-001 frozen test access is already logged")


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dev", action="store_true")
    mode.add_argument("--frozen", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--rerender", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    t0 = time.time()
    if args.rerender:
        stored = json.loads((OUT / "results.json").read_text())
        elapsed = float(stored.get("elapsed_s") or 0.0)
        (OUT / "REPORT.md").write_text(render_report(stored, elapsed))
        print("rewrote REPORT.md from results.json")
        return 0
    if args.smoke:
        reps = run("dev", 1, 1, smoke=True)
        agg = aggregate(reps)
        report = render_report({"aggregate": agg, "kind": "smoke"}, 0.0)
        print(json.dumps({"ok": "H3" in report and "B4" in report, "void": agg["void"]}))
        return 0
    if args.dev:
        if (OUT / "dev_results.json").exists():
            raise RuntimeError("EXP-M12-001 development output already exists; refusing overwrite")
        reps = run("dev", CONFIG["n_dev"], args.workers)
        agg = aggregate(reps)
        out = {"config": CONFIG, "kind": "development", "aggregate": agg, "replications": reps}
        (OUT / "dev_results.json").write_text(json.dumps(out, indent=2))
        print(f"wrote dev_results.json in {time.time() - t0:.0f}s")
        return 0
    assert_no_prior_frozen_access()
    reps = run("frozen", CONFIG["n_frozen"], args.workers)
    elapsed = time.time() - t0
    agg = aggregate(reps)
    out = {
        "config": CONFIG,
        "kind": "frozen",
        "elapsed_s": elapsed,
        "aggregate": agg,
        "replications": reps,
    }
    (OUT / "results.json").write_text(json.dumps(out, indent=2))
    (OUT / "REPORT.md").write_text(render_report(out, elapsed))
    print(f"wrote results.json and REPORT.md in {elapsed:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
