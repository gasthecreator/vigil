#!/usr/bin/env python3
"""EXP-K4-001 runner (study S4). Specification: experiments/EXP-K4-001/PREREG.md. Every number in the outputs is
computed here; none is typed.

    uv run python experiments/EXP-K4-001/run.py --dev        # dev replications 0..2 -> hyperparameters.json, dev_results.json
    uv run python experiments/EXP-K4-001/run.py --frozen     # replications 0..9 -> results.json, REPORT.md (run ONCE)
    uv run python experiments/EXP-K4-001/run.py --smoke      # tiny design, nothing committed (used by tests)
    uv run python experiments/EXP-K4-001/run.py --rerender   # re-derive aggregate + REPORT.md from results.json records

The networks (vigil_ml.k4) receive arrays only: log values, masks, visit days, static values. The classical baselines
receive the feature matrix of `WindowedFeatureExtractor`. Labels are used only to train the supervised arms and to score.
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
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for _pkg in ("vigil-sim", "vigil-ml", "vigil-core", "vigil-eval"):
    sys.path.insert(0, str(ROOT / "packages" / _pkg))

import torch  # noqa: E402
import xgboost  # noqa: E402,F401  (must be imported before torch: the two OpenMP runtimes clash on macOS)
from vigil_core.analytes import ANALYTE_REGISTRY  # noqa: E402
from vigil_eval import compute_calibration_curve, ipcw_brier_score, ipcw_time_dependent_roc_auc  # noqa: E402
from vigil_ml import k4  # noqa: E402
from vigil_ml.baselines import (  # noqa: E402
    GradientBoostingBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)
from vigil_ml.features import WindowedFeatureExtractor  # noqa: E402
from vigil_ml.joint_model import FastLandmarkJointModel  # noqa: E402
from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402

OUT = Path(__file__).resolve().parent
WORK = OUT / "_work"

# ---------------------------------------------------------------------------------------------------------
# Fixed design (PREREG sections 3 to 7), written into results.json as `config`.
# ---------------------------------------------------------------------------------------------------------
CONFIG: Dict[str, Any] = {
    "duration_days": 730.0,
    "horizon_days": 365.0,
    "n_pool": 1000,
    "n_test": 500,
    "n_corpus_per_source": 3000,
    "n_grid": [50, 100, 200, 500, 1000],
    "n_scale": [100, 1000],
    "n_h1": 100,
    "n_h2": 1000,
    "n_canary": 1000,
    "n_canary_perms": 20,
    "families": list(k4.FAMILIES),
    "f3": ["grud", "ct_transformer", "ssm"],
    "sizes": dict(k4.SIZES),
    "lr_scratch_grid": [1e-3, 3e-3],
    "lr_finetune_grid": [3e-4, 1e-3],
    "lr_selection_n": [100, 1000],
    "fit": {"weight_decay": 1e-4, "batch_size": 32, "max_epochs": 120, "patience": 12, "clip": 1.0, "val_fraction": 0.2, "min_val": 10},
    "pretrain": {"lr": 2e-3, "batch_size": 64, "epochs": 25, "mask_rate": 0.25, "val_fraction": 0.1},
    "randomiser": {
        "time_scale_log_uniform": [0.6, 1.6],
        "visit_dropout_max": 0.35,
        "log_noise_sd_max": 0.25,
        "lab_offset_tau_max": 0.25,
        "extra_missing_max": 0.3,
        "min_visits": 2,
    },
    "seeds": {
        "dev": {"base": 700, "step": 100, "n": 3},
        "frozen": {"base": 20261201, "step": 100, "n": 10},
        "offsets": {"pool": 0, "g1": 1, "g2": 2, "g3": 3, "src1": 4, "src2": 5, "src3": 6, "randomiser": 7,
                    "shuffle": 8, "canary": 9, "network": 10},
    },
    "bootstrap_B": 2000,
    "bootstrap_seed": 20261201,
    "bonferroni_m": 3,
    "material_auc": 0.01,
    "material_auc_h3": 0.005,
    "canary_range": [0.45, 0.55],
    "latency_steps": 8,
    "latency_repeats": 200,
    "baselines": ["B1_SingleThreshold", "B2_Velocity", "B3_RegularizedHazard", "B4_GradientBoosting", "K3_JointModel"],
}
SMOKE_CONFIG: Dict[str, Any] = {
    "n_pool": 60,
    "n_test": 40,
    "n_corpus_per_source": 60,
    "n_grid": [50, 60],
    "n_scale": [50, 60],
    "n_h1": 50,
    "n_h2": 60,
    "n_canary": 60,
    "n_canary_perms": 2,
    "pretrain_epochs": 1,
    "max_epochs": 3,
    "latency_repeats": 5,
}
CORPORA = ("pt_all", "pt_offgen", "pt_shuffled")
ANALYTE_ORDER = list(k4.ANALYTES)
REFERENCE_MID = np.array(
    [(ANALYTE_REGISTRY[a].plausibility.reference_low + ANALYTE_REGISTRY[a].plausibility.reference_high) / 2.0 for a in ANALYTE_ORDER]
)
SUBTYPES = ("TNBC", "HR+HER2-", "HER2+")


def design(scope: str) -> Dict[str, Any]:
    cfg = json.loads(json.dumps(CONFIG))
    if scope == "smoke":
        for k, v in SMOKE_CONFIG.items():
            if k == "pretrain_epochs":
                cfg["pretrain"]["epochs"] = v
            elif k == "max_epochs":
                cfg["fit"]["max_epochs"] = v
            else:
                cfg[k] = v
    return cfg


def code_hash() -> str:
    h = hashlib.sha256()
    for p in (ROOT / "packages" / "vigil-ml" / "vigil_ml" / "k4.py", Path(__file__)):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def base_seed(kind: str, r: int) -> int:
    s = CONFIG["seeds"]["frozen" if kind in ("frozen", "smoke") else "dev"]
    return int(s["base"] + s["step"] * r)


# ---------------------------------------------------------------------------------------------------------
# Data: arrays from simulator cohorts. Only the model-facing analyte columns, visit days and baseline clinical
# variables are read; no simulator-internal column is touched.
# ---------------------------------------------------------------------------------------------------------
def cohort_arrays(cohort) -> Tuple[List[str], List[np.ndarray], List[np.ndarray], np.ndarray]:
    obs = cohort.to_observations_dataframe()
    pts = cohort.to_patients_dataframe()
    ids = list(pts["patient_id"])
    sym_cols = [f"symptom_{x}" for x in k4.SYMPTOMS]
    cols = ["patient_id", "day"] + ANALYTE_ORDER + sym_cols
    grouped = {pid: g.sort_values("day", kind="stable") for pid, g in obs[cols].groupby("patient_id", sort=False)}
    days, values = [], []
    for pid in ids:
        g = grouped.get(pid)
        if g is None:
            days.append(np.zeros(0))
            values.append(np.zeros((0, k4.N_CHANNELS)))
        else:
            days.append(g["day"].to_numpy(dtype=float))
            # laboratory values as drawn (NaN = not drawn), then symptom grades / 4 (amendment A4)
            values.append(np.concatenate([g[ANALYTE_ORDER].to_numpy(dtype=float),
                                          g[sym_cols].to_numpy(dtype=float) / k4.SYMPTOM_SCALE], axis=1))
    stage = pts["stage"].astype(str).str.upper().isin(["STAGE III", "STAGE IV"]).to_numpy(dtype=float)
    sub = pts["subtype"].astype(str)
    statics = np.stack(
        [
            (pts["age"].to_numpy(dtype=float) - 50.0) / 10.0,
            pts["er_status"].astype(float).to_numpy(),
            pts["pr_status"].astype(float).to_numpy(),
            pts["her2_status"].astype(float).to_numpy(),
            stage,
        ]
        + [(sub == s).to_numpy(dtype=float) for s in SUBTYPES],
        axis=1,
    )
    assert statics.shape[1] == k4.N_STATIC
    return ids, days, values, statics


def make_sequences(ids, days, values, statics) -> k4.SequenceSet:
    return k4.build_sequences(ids, days, values, statics, REFERENCE_MID)


def randomise_cohort(days, values, rng: np.random.Generator, spec: Dict[str, Any]):
    """Domain randomisation of one unlabelled cohort (PREREG section 3). Cohort-level draws first, then per patient."""
    p_drop = rng.uniform(0.0, spec["visit_dropout_max"])
    sd = rng.uniform(0.0, spec["log_noise_sd_max"])
    p_miss = rng.uniform(0.0, spec["extra_missing_max"])
    tau = rng.uniform(0.0, spec["lab_offset_tau_max"])
    lo, hi = np.log(spec["time_scale_log_uniform"][0]), np.log(spec["time_scale_log_uniform"][1])
    out_d, out_v = [], []
    for d, v in zip(days, values):
        n = len(d)
        scale = float(np.exp(rng.uniform(lo, hi)))
        keep = rng.random(n) >= p_drop
        if n >= spec["min_visits"] and keep.sum() < spec["min_visits"]:
            keep[:] = False
            keep[np.sort(rng.choice(n, size=spec["min_visits"], replace=False))] = True
        d2, v2 = d[keep] * scale, v[keep].copy()
        beta = float(rng.normal(0.0, tau))
        lab = v2[:, : k4.N_LAB]  # randomisation touches laboratory values only; symptom grades are kept
        lab = lab * np.exp(beta) * np.exp(rng.normal(0.0, sd, size=lab.shape))
        lab[rng.random(lab.shape) < p_miss] = np.nan
        v2[:, : k4.N_LAB] = lab
        out_d.append(d2)
        out_v.append(v2)
    return out_d, out_v


def shuffle_values(values: List[np.ndarray], rng: np.random.Generator) -> List[np.ndarray]:
    """PT-shuffled control: permute each analyte's observed values across all (patient, visit) cells."""
    stacked = [np.asarray(v, dtype=float).copy() for v in values]
    for a in range(len(ANALYTE_ORDER)):
        cells = [(i, j) for i, v in enumerate(stacked) for j in range(v.shape[0]) if not np.isnan(v[j, a])]
        vals = np.array([stacked[i][j, a] for i, j in cells])
        vals = vals[rng.permutation(len(vals))]
        for (i, j), x in zip(cells, vals):
            stacked[i][j, a] = x
    return stacked


class LabelledCohort:
    """Sequences and landmark rows of one cohort with the row index needed to score a model."""

    def __init__(self, cohort, extractor: WindowedFeatureExtractor, horizon: float):
        self.ids, days, values, statics = cohort_arrays(cohort)
        self.ds = make_sequences(self.ids, days, values, statics)
        obs = cohort.to_observations_dataframe()
        pts = cohort.to_patients_dataframe()
        self.X, y, self.t, self.d = extractor.transform_cohort(pts, obs, horizon_days=horizon)
        self.X = self.X.reset_index(drop=True)
        self.y = pd.Series(np.asarray(y, dtype=float))
        pid_index = {p: i for i, p in enumerate(self.ids)}
        visit_index: Dict[Tuple[str, float], int] = {}
        for i, pid in enumerate(self.ids):
            for j in range(int(self.ds.valid[i].sum())):
                visit_index[(pid, float(self.ds.t[i, j]))] = j
        self.pos_i = np.zeros(len(self.X), dtype=int)
        self.pos_j = np.zeros(len(self.X), dtype=int)
        rows: Dict[Tuple[str, float], float] = {}
        for k, (pid, day) in enumerate(zip(self.X["patient_id"], self.X["eval_day"])):
            key = (pid, float(np.float32(day)))
            if key in rows:
                raise ValueError(f"duplicate landmark row {key}")
            rows[key] = float(self.y.iloc[k])
            self.pos_i[k], self.pos_j[k] = pid_index[pid], visit_index[key]
        self.ds = k4.attach_labels(self.ds, rows)
        self.t = np.asarray(self.t, dtype=float)
        self.d = np.asarray(self.d, dtype=float)

    def rows_of_first(self, n: int) -> np.ndarray:
        keep = set(self.ids[:n])
        return np.array([p in keep for p in self.X["patient_id"]])


class Replication:
    """Everything generated from the seeds of one replication."""

    def __init__(self, kind: str, r: int, scope: str, with_corpus: bool):
        cfg = design(scope)
        s = base_seed(kind, r)
        off = CONFIG["seeds"]["offsets"]
        ex = WindowedFeatureExtractor()
        h = cfg["horizon_days"]

        def cohort(gen: GeneratorType, seed: int, n: int):
            return get_generator(gen, seed=seed).generate_cohort(num_patients=n, duration_days=cfg["duration_days"])

        self.cfg, self.seed = cfg, s
        self.pool = LabelledCohort(cohort(GeneratorType.G1_SMOOTH, s + off["pool"], cfg["n_pool"]), ex, h)
        self.tests = {
            "g1": LabelledCohort(cohort(GeneratorType.G1_SMOOTH, s + off["g1"], cfg["n_test"]), ex, h),
            "g2": LabelledCohort(cohort(GeneratorType.G2_BURST, s + off["g2"], cfg["n_test"]), ex, h),
            "g3": LabelledCohort(cohort(GeneratorType.G3_NOISE, s + off["g3"], cfg["n_test"]), ex, h),
        }
        self.corpora: Dict[str, k4.SequenceSet] = {}
        if with_corpus:
            self.corpora = self._corpora(cohort, cfg, s, off)

    @staticmethod
    def _corpora(cohort, cfg, s, off) -> Dict[str, k4.SequenceSet]:
        rng = np.random.default_rng(s + off["randomiser"])
        parts = []
        for gen, key in ((GeneratorType.G1_SMOOTH, "src1"), (GeneratorType.G2_BURST, "src2"), (GeneratorType.G3_NOISE, "src3")):
            ids, days, values, statics = cohort_arrays(cohort(gen, s + off[key], cfg["n_corpus_per_source"]))
            d2, v2 = randomise_cohort(days, values, rng, cfg["randomiser"])
            parts.append((ids, d2, v2, statics, key))

        def seqs(sel: Sequence[Tuple], values_override: Optional[List[np.ndarray]] = None) -> k4.SequenceSet:
            ids: List[str] = []
            days, vals, st = [], [], []
            for (pid, d, v, stat, key) in sel:
                ids += [f"{key}:{p}" for p in pid]
                days += list(d)
                vals += list(v)
                st.append(stat)
            if values_override is not None:
                vals = values_override
            return make_sequences(ids, days, vals, np.concatenate(st, axis=0))

        all_sel = parts
        out = {"pt_all": seqs(all_sel), "pt_offgen": seqs(parts[1:])}
        flat = [v for (_, _, v, _, _) in all_sel for v in v]
        shuffled = shuffle_values(flat, np.random.default_rng(s + off["shuffle"]))
        out["pt_shuffled"] = seqs(all_sel, shuffled)
        return out


@lru_cache(maxsize=2)
def replication(kind: str, r: int, scope: str, with_corpus: bool) -> Replication:
    return Replication(kind, r, scope, with_corpus)


# ---------------------------------------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------------------------------------
def score_rows(preds: np.ndarray, lc: LabelledCohort, horizon: float) -> Dict[str, float]:
    preds = np.asarray(preds, dtype=float)
    return {
        "auc": float(ipcw_time_dependent_roc_auc(preds, lc.t, lc.d, horizon_time=horizon)),
        "brier": float(ipcw_brier_score(preds, lc.t, lc.d, horizon_time=horizon)),
        "ece": float(compute_calibration_curve(preds, lc.y.values, n_bins=10).expected_calibration_error),
    }


def score_network(net: k4.K4Network, rep: Replication) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for g, lc in rep.tests.items():
        probs = k4.predict_probabilities(net, lc.ds)
        m = score_rows(probs[lc.pos_i, lc.pos_j], lc, rep.cfg["horizon_days"])
        for k, v in m.items():
            out[f"{k}_{g}"] = v
    return out


def fit_config(rep: Replication, lr: float) -> k4.FitConfig:
    f = rep.cfg["fit"]
    return k4.FitConfig(lr=lr, weight_decay=f["weight_decay"], batch_size=f["batch_size"], max_epochs=f["max_epochs"],
                        patience=f["patience"], clip=f["clip"], val_fraction=f["val_fraction"], min_val=f["min_val"])


def pretrain_config(rep: Replication) -> k4.PretrainConfig:
    p = rep.cfg["pretrain"]
    return k4.PretrainConfig(lr=p["lr"], batch_size=p["batch_size"], epochs=p["epochs"], mask_rate=p["mask_rate"],
                             val_fraction=p["val_fraction"])


def train_set(rep: Replication, n: int, permute_seed: Optional[int] = None) -> k4.SequenceSet:
    ds = rep.pool.ds.subset(range(min(n, len(rep.pool.ds))))
    if permute_seed is not None:
        # A1: permute the landmark-row labels over all rows of the training set.
        y = ds.y.copy()
        rows = ds.row_mask
        vals = y[rows]
        y[rows] = vals[np.random.default_rng(permute_seed).permutation(len(vals))]
        ds = k4.SequenceSet(ds.patient_ids, ds.x, ds.m, ds.t, ds.s, ds.valid, y, rows)
    return ds


def record(base: Dict[str, Any], **kw) -> Dict[str, Any]:
    out = dict(base)
    out.update(kw)
    return out


def fit_arm(rep: Replication, base: Dict[str, Any], family: str, size: str, n: int, lr: float, seed: int,
            encoder_state=None, permute_seed: Optional[int] = None):
    ds = train_set(rep, n, permute_seed)
    res = k4.fit_risk_model(family, size, ds, fit_config(rep, lr), seed, encoder_state=encoder_state)
    rec = record(base, size=size, N=n, lr=lr, best_epoch=res.best_epoch, train_seconds=round(res.train_seconds, 2),
                 params=k4.count_parameters(res.network), n_rows=int(ds.row_mask.sum()),
                 n_events=int(ds.y[ds.row_mask].sum()))
    rec.update(score_network(res.network, rep))
    return rec, res.network


# ---------------------------------------------------------------------------------------------------------
# Units of work
# ---------------------------------------------------------------------------------------------------------
def pretrain(rep: Replication, family: str, size: str, corpus: str, seed: int):
    res = k4.pretrain_encoder(family, size, rep.corpora[corpus], pretrain_config(rep), seed)
    info = {"family": family, "size": size, "corpus": corpus, "n_patients": len(rep.corpora[corpus]),
            "initial_val_loss": res.initial_val_loss, "final_val_loss": res.val_losses[-1],
            "val_losses": res.val_losses, "train_seconds": round(res.train_seconds, 2)}
    return res.encoder_state, info


def unit_grid(kind: str, r: int, family: str, scope: str) -> Dict[str, Any]:
    """Development learning-rate grid (PREREG section 7): medium, N in lr_selection_n, G1 test AUC."""
    rep = replication(kind, r, scope, family in CONFIG["f3"])
    cfg, off = rep.cfg, CONFIG["seeds"]["offsets"]
    fi = list(CONFIG["families"]).index(family)
    seed = rep.seed + off["network"] + fi
    recs: List[Dict[str, Any]] = []
    base = {"kind": kind, "rep": r, "family": family}
    ns = [n for n in cfg["lr_selection_n"]] if scope != "smoke" else cfg["n_scale"]
    for lr in cfg["lr_scratch_grid"]:
        for n in ns:
            rec, _ = fit_arm(rep, base | {"arm": "scratch"}, family, "medium", n, lr, seed)
            recs.append(rec)
    pre = []
    if family in cfg["f3"]:
        state, info = pretrain(rep, family, "medium", "pt_all", seed)
        pre.append(record(base, **info))
        for lr in cfg["lr_finetune_grid"]:
            for n in ns:
                rec, _ = fit_arm(rep, base | {"arm": "pt_all"}, family, "medium", n, lr, seed, encoder_state=state)
                recs.append(rec)
    return {"records": recs, "pretrain": pre}


def unit_family(kind: str, r: int, family: str, hp: Dict[str, Any], scope: str) -> Dict[str, Any]:
    """The frozen design for one family in one replication."""
    in_f3 = family in CONFIG["f3"]
    rep = replication(kind, r, scope, in_f3)
    cfg, off = rep.cfg, CONFIG["seeds"]["offsets"]
    fi = list(CONFIG["families"]).index(family)
    seed = rep.seed + off["network"] + fi
    lr_s, lr_f = hp["lr_scratch"][family], hp["lr_finetune"].get(family)
    base = {"kind": kind, "rep": r, "family": family}
    recs: List[Dict[str, Any]] = []
    pre: List[Dict[str, Any]] = []
    exports: List[Dict[str, Any]] = []
    keep_net = None
    for n in cfg["n_grid"]:
        rec, net = fit_arm(rep, base | {"arm": "scratch"}, family, "medium", n, lr_s, seed)
        recs.append(rec)
        if n == cfg["n_h2"]:
            keep_net = net
    if r == 0:
        exports.append(export_check(rep, family, keep_net))
    if family == "grud":
        for k in range(cfg["n_canary_perms"]):  # A3: a model fitted to permuted labels scatters widely, so many permutations
            rec, _ = fit_arm(rep, base | {"arm": "canary_permuted_labels", "perm": k}, family, "medium", cfg["n_canary"],
                             lr_s, seed + 1000 * (k + 1), permute_seed=rep.seed + off["canary"] + 1000 * k)
            recs.append(rec)
    if in_f3:
        for corpus in CORPORA:
            state, info = pretrain(rep, family, "medium", corpus, seed)
            pre.append(record(base, **info))
            for n in cfg["n_grid"]:
                rec, _ = fit_arm(rep, base | {"arm": corpus}, family, "medium", n, lr_f, seed, encoder_state=state)
                recs.append(rec)
        for size in ("small", "large"):
            for n in cfg["n_scale"]:
                rec, _ = fit_arm(rep, base | {"arm": "scratch"}, family, size, n, lr_s, seed)
                recs.append(rec)
            state, info = pretrain(rep, family, size, "pt_all", seed)
            pre.append(record(base, **info))
            for n in cfg["n_scale"]:
                rec, _ = fit_arm(rep, base | {"arm": "pt_all"}, family, size, n, lr_f, seed, encoder_state=state)
                recs.append(rec)
    cost = []
    if r == 0:
        for size in ("small", "medium", "large"):
            net = k4.build_network(family, size, seed)
            lat = k4.measure_latency(net, steps=cfg["latency_steps"], repeats=cfg["latency_repeats"])
            cost.append({"family": family, "size": size, "params": k4.count_parameters(net),
                         "state_bytes": k4.state_bytes(net), **lat})
    return {"records": recs, "pretrain": pre, "exports": exports, "cost": cost}


def export_check(rep: Replication, family: str, net: k4.K4Network) -> Dict[str, Any]:
    """Safetensors round trip (exact) and ONNX parity on the G1 test sequences, using the trained N=n_h2 network."""
    import tempfile

    import onnxruntime as ort

    lc = rep.tests["g1"]
    sel = np.arange(min(50, len(lc.ds)))
    sub = lc.ds.subset(sel)
    x, m, t, s, v = (torch.from_numpy(a) for a in (sub.x, sub.m, sub.t, sub.s, sub.valid.astype(np.float32)))
    net.eval()
    with torch.no_grad():
        ref = torch.sigmoid(net(x, m, t, s, v)).numpy()
    with tempfile.TemporaryDirectory() as d:
        sf, ox = Path(d) / "m.safetensors", Path(d) / "m.onnx"
        k4.save_safetensors(net, sf, {"study": "EXP-K4-001"})
        back = k4.load_safetensors(sf)
        with torch.no_grad():
            round_trip = torch.sigmoid(back(x, m, t, s, v)).numpy()
        k4.export_onnx(net, ox)
        sess = ort.InferenceSession(str(ox), providers=["CPUExecutionProvider"])
        got = sess.run(None, {"x": sub.x, "m": sub.m, "t": sub.t, "s": sub.s, "valid": sub.valid.astype(np.float32)})[0]
    real = sub.valid
    return {"family": family, "safetensors_exact": bool(np.array_equal(ref, round_trip)),
            "onnx_max_abs_diff": float(np.max(np.abs(got[real] - ref[real]))), "n_sequences": int(len(sel))}


def make_baseline(name: str):
    return {
        "B1_SingleThreshold": lambda: SingleThresholdBaseline(),
        "B2_Velocity": lambda: VelocityBaseline(),
        "B3_RegularizedHazard": lambda: RegularizedCoxHazardBaseline(C=1.0),
        "B4_GradientBoosting": lambda: GradientBoostingBaseline(max_depth=3, n_estimators=100),
        "K3_JointModel": lambda: FastLandmarkJointModel(horizon_days=365.0),
    }[name]()


def unit_baselines(kind: str, r: int, scope: str) -> Dict[str, Any]:
    rep = replication(kind, r, scope, False)
    recs: List[Dict[str, Any]] = []
    for n in rep.cfg["n_grid"]:
        keep = rep.pool.rows_of_first(n)
        X, y = rep.pool.X[keep], rep.pool.y[keep]
        for name in rep.cfg["baselines"]:
            failed = False
            t0 = time.time()
            model = make_baseline(name)
            try:
                model.fit(X, y)
            except Exception:  # a one-class or degenerate set: recorded, constant prediction used
                failed = True  # recorded in the record as fit_failed
            rec = {"kind": kind, "rep": r, "family": name, "arm": "classical", "size": "-", "N": n, "lr": None,
                   "n_rows": int(len(y)), "n_events": int(y.sum()), "fit_failed": failed,
                   "train_seconds": round(time.time() - t0, 2)}
            for g, lc in rep.tests.items():
                preds = np.full(len(lc.X), float(y.mean() if len(y) else 0.0)) if failed else np.asarray(model.predict_risk(lc.X), dtype=float)
                for k, v in score_rows(preds, lc, rep.cfg["horizon_days"]).items():
                    rec[f"{k}_{g}"] = v
            recs.append(rec)
    return {"records": recs, "pretrain": [], "exports": [], "cost": []}


# ---------------------------------------------------------------------------------------------------------
# Execution (process pool, resumable per unit, keyed by the code hash)
# ---------------------------------------------------------------------------------------------------------
def _init_worker() -> None:
    torch.set_num_threads(1)
    import os

    os.environ["OMP_NUM_THREADS"] = "1"


def run_unit(spec: Tuple) -> Tuple[Tuple, Dict[str, Any], float]:
    t0 = time.time()
    torch.set_num_threads(1)
    stage, kind, r, family, hp, scope = spec
    if stage == "grid":
        out = unit_grid(kind, r, family, scope)
    elif stage == "family":
        out = unit_family(kind, r, family, hp, scope)
    elif stage == "baselines":
        out = unit_baselines(kind, r, scope)
    else:
        raise ValueError(stage)
    return spec, out, time.time() - t0


def unit_path(spec: Tuple, tag: str) -> Path:
    stage, kind, r, family, _, scope = spec
    return WORK / f"{tag}_{stage}_{kind}_{r}_{family or 'all'}_{scope}_{code_hash()}.json"


def execute(specs: List[Tuple], tag: str, workers: int) -> List[Tuple[Tuple, Dict[str, Any]]]:
    WORK.mkdir(exist_ok=True)
    done: List[Tuple[Tuple, Dict[str, Any]]] = []
    todo = []
    for sp in specs:
        p = unit_path(sp, tag)
        if p.exists():
            done.append((sp, json.loads(p.read_text())))
        else:
            todo.append(sp)
    print(f"[{tag}] {len(done)} units cached, {len(todo)} to run on {workers} workers", flush=True)
    if workers <= 1:
        for sp in todo:
            _, out, sec = run_unit(sp)
            unit_path(sp, tag).write_text(json.dumps(out))
            done.append((sp, out))
            print(f"  unit {sp[0]} {sp[1]} r={sp[2]} {sp[3]} done in {sec:.0f}s", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn"), initializer=_init_worker) as pool:
            futs = [pool.submit(run_unit, sp) for sp in todo]
            for f in as_completed(futs):
                sp, out, sec = f.result()
                unit_path(sp, tag).write_text(json.dumps(out))
                done.append((sp, out))
                print(f"  unit {sp[0]} {sp[1]} r={sp[2]} {sp[3]} done in {sec:.0f}s", flush=True)
    return done


def merge(done: List[Tuple[Tuple, Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    order = sorted(done, key=lambda kv: (kv[0][1], kv[0][2], kv[0][0], kv[0][3] or ""))
    out: Dict[str, List[Dict[str, Any]]] = {"records": [], "pretrain": [], "exports": [], "cost": []}
    for _, o in order:
        for k in out:
            out[k].extend(o.get(k, []))
    return out


# ---------------------------------------------------------------------------------------------------------
# Selection on development data
# ---------------------------------------------------------------------------------------------------------
def select_hyperparameters(dev: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, Any]:
    ns = cfg["lr_selection_n"]
    hp: Dict[str, Any] = {"lr_scratch": {}, "lr_finetune": {}, "grid": {}}
    for fam in cfg["families"]:
        for arm, key, grid in (("scratch", "lr_scratch", cfg["lr_scratch_grid"]), ("pt_all", "lr_finetune", cfg["lr_finetune_grid"])):
            sub = dev[(dev.family == fam) & (dev.arm == arm) & (dev.N.isin(ns)) & (dev["size"] == "medium")]
            if sub.empty:
                continue
            means = {float(lr): float(sub[sub.lr == lr].auc_g1.mean()) for lr in grid}
            best = max(sorted(means), key=lambda lr: (means[lr], -lr))  # ties go to the smaller rate
            hp[key][fam] = best
            hp["grid"][f"{fam}/{arm}"] = {str(k): v for k, v in means.items()}
    return hp


def designated_family(dev_full: pd.DataFrame, cfg: Dict[str, Any]) -> Tuple[str, Dict[str, float]]:
    sub = dev_full[(dev_full.arm == "scratch") & (dev_full["size"] == "medium") & (dev_full.N == cfg["n_h2"])]
    sub = sub[sub.family.isin(cfg["families"])]
    means = {f: float(sub[sub.family == f].auc_g1.mean()) for f in cfg["families"]}
    return max(cfg["families"], key=lambda f: means[f]), means


# ---------------------------------------------------------------------------------------------------------
# Aggregation (a pure function of the records)
# ---------------------------------------------------------------------------------------------------------
class Boot:
    def __init__(self, n_reps: int, B: int, seed: int):
        self.idx = np.random.default_rng(seed).integers(0, n_reps, size=(B, n_reps))

    def ci(self, per_rep: np.ndarray, level: float) -> Tuple[float, float]:
        d = per_rep[self.idx].mean(axis=1)
        a = (1.0 - level) / 2.0
        return float(np.quantile(d, a)), float(np.quantile(d, 1.0 - a))


def per_rep(df: pd.DataFrame, reps: List[int], metric: str = "auc_g1") -> np.ndarray:
    s = df.groupby("rep")[metric].mean()
    return np.array([float(s[r]) for r in reps])


def pick(df: pd.DataFrame, **kw) -> pd.DataFrame:
    m = np.ones(len(df), dtype=bool)
    for k, v in kw.items():
        m &= (df[k] == v).to_numpy() if not isinstance(v, (list, tuple)) else df[k].isin(v).to_numpy()
    return df[m]


def aggregate(payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = payload["config"]
    df = pd.DataFrame(payload["records"])
    reps = sorted(int(r) for r in df["rep"].unique())
    boot = Boot(len(reps), cfg["bootstrap_B"], cfg["bootstrap_seed"])
    lvl_p = 1.0 - 0.05 / cfg["bonferroni_m"]
    f3, ns = cfg["f3"], cfg["n_grid"]
    baselines = cfg["baselines"]
    designated = payload["hyperparameters"]["designated_family"]
    out: Dict[str, Any] = {"replications": reps}

    def mean_ci(sub: pd.DataFrame, metric: str = "auc_g1") -> Dict[str, float]:
        v = per_rep(sub, reps, metric)
        lo, hi = boot.ci(v, 0.95)
        return {"mean": float(v.mean()), "lo": lo, "hi": hi}

    # canary
    can = pick(df, arm="canary_permuted_labels")
    cmean = float(per_rep(can, reps).mean())
    lo, hi = cfg["canary_range"]
    out["canary"] = {"mean_auc_g1": cmean, "range": [lo, hi], "void": bool(not (lo <= cmean <= hi)), "per_rep": per_rep(can, reps).tolist(),
                     "n_fits": int(len(can)), "sd_per_fit": float(can.auc_g1.std())}

    # tables: mean AUC [CI] per (family, size, arm, N), metrics on all three test cohorts
    table = []
    for (fam, size, arm, n), g in df[df.arm != "canary_permuted_labels"].groupby(["family", "size", "arm", "N"]):
        row = {"family": fam, "size": size, "arm": arm, "N": int(n), "n_reps": int(g.rep.nunique())}
        for gen in ("g1", "g2", "g3"):
            for met in ("auc", "brier", "ece"):
                v = per_rep(g, reps, f"{met}_{gen}")
                row[f"{met}_{gen}"] = float(v.mean())
            lo, hi = boot.ci(per_rep(g, reps, f"auc_{gen}"), 0.95)
            row[f"auc_{gen}_lo"], row[f"auc_{gen}_hi"] = lo, hi
        row["train_seconds_mean"] = float(g.train_seconds.mean())
        row["best_epoch_mean"] = float(g.best_epoch.mean()) if "best_epoch" in g and g.best_epoch.notna().any() else None
        table.append(row)
    out["table"] = table

    # strongest baseline per N
    strongest = {}
    for n in ns:
        means = {b: float(per_rep(pick(df, family=b, arm="classical", N=n), reps).mean()) for b in baselines}
        best = max(means, key=lambda b: means[b])
        strongest[str(n)] = {"name": best, "mean_auc_g1": means[best], "all": means}
    out["strongest_baseline"] = strongest

    # H1
    d1 = np.mean(
        [per_rep(pick(df, family=f, arm="pt_all", size="medium", N=cfg["n_h1"]), reps)
         - per_rep(pick(df, family=f, arm="scratch", size="medium", N=cfg["n_h1"]), reps) for f in f3], axis=0)
    lo, hi = boot.ci(d1, lvl_p)
    out["H1"] = {"delta": float(d1.mean()), "lo": lo, "hi": hi, "level": lvl_p, "threshold": cfg["material_auc"],
                 "met": bool(lo > cfg["material_auc"]),
                 "per_family": {f: float((per_rep(pick(df, family=f, arm="pt_all", size="medium", N=cfg["n_h1"]), reps)
                                          - per_rep(pick(df, family=f, arm="scratch", size="medium", N=cfg["n_h1"]), reps)).mean()) for f in f3}}
    # H2
    des = per_rep(pick(df, family=designated, arm="scratch", size="medium", N=cfg["n_h2"]), reps)
    h2 = {}
    for b in baselines:
        d = des - per_rep(pick(df, family=b, arm="classical", N=cfg["n_h2"]), reps)
        lo, hi = boot.ci(d, lvl_p)
        h2[b] = {"delta": float(d.mean()), "lo": lo, "hi": hi, "beats": bool(lo > 0.0)}
    out["H2"] = {"designated_family": designated, "level": lvl_p, "per_baseline": h2, "met": bool(all(v["beats"] for v in h2.values()))}
    # H3
    def scale_delta(a: str, b: str) -> np.ndarray:
        return np.mean(
            [per_rep(pick(df, family=f, arm="scratch", size=a, N=cfg["n_h2"]), reps)
             - per_rep(pick(df, family=f, arm="scratch", size=b, N=cfg["n_h2"]), reps) for f in f3], axis=0)

    d3 = scale_delta("large", "medium")
    lo, hi = boot.ci(d3, lvl_p)
    thr = cfg["material_auc_h3"]
    cls = "scale helps" if lo > thr else ("scale does not help" if hi < thr else "inconclusive")
    d3s = scale_delta("medium", "small")
    slo, shi = boot.ci(d3s, 0.95)
    out["H3"] = {"delta_large_minus_medium": float(d3.mean()), "lo": lo, "hi": hi, "level": lvl_p, "threshold": thr,
                 "class": cls, "medium_minus_small": {"delta": float(d3s.mean()), "lo": slo, "hi": shi}}

    # descriptive: pre-training variants against scratch, label-efficiency, family ranking, crossing points
    desc_pt = []
    for arm in CORPORA:
        for n in ns:
            ds_ = np.mean([per_rep(pick(df, family=f, arm=arm, size="medium", N=n), reps)
                           - per_rep(pick(df, family=f, arm="scratch", size="medium", N=n), reps) for f in f3], axis=0)
            lo, hi = boot.ci(ds_, 0.95)
            desc_pt.append({"arm": arm, "N": n, "delta_vs_scratch": float(ds_.mean()), "lo": lo, "hi": hi})
    out["pretraining_vs_scratch"] = desc_pt
    out["ranking_n1000"] = sorted(
        ({"family": f, "mean_auc_g1": float(per_rep(pick(df, family=f, arm="scratch", size="medium", N=cfg["n_h2"]), reps).mean())}
         for f in cfg["families"]), key=lambda r: -r["mean_auc_g1"])
    cross = {}
    for f in cfg["families"]:
        cross[f] = None
        for n in ns:
            if float(per_rep(pick(df, family=f, arm="scratch", size="medium", N=n), reps).mean()) >= strongest[str(n)]["mean_auc_g1"]:
                cross[f] = n
                break
    out["smallest_n_reaching_strongest_baseline"] = cross
    pre = pd.DataFrame(payload["pretrain"])
    if len(pre):
        g = pre.groupby(["family", "size", "corpus"]).agg(initial=("initial_val_loss", "mean"), final=("final_val_loss", "mean"), n=("rep", "count"))
        out["pretrain_loss"] = [{"family": k[0], "size": k[1], "corpus": k[2], "initial_val_loss": float(v.initial),
                                 "final_val_loss": float(v.final), "n": int(v.n)} for k, v in g.iterrows()]
    else:
        out["pretrain_loss"] = []
    fails = df[df.get("fit_failed", False) == True] if "fit_failed" in df else df.iloc[0:0]  # noqa: E712
    out["baseline_fit_failures"] = int(len(fails))
    return out


# ---------------------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------------------
def fmt(x: Optional[float], d: int = 4) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}"


def render_report(res: Dict[str, Any]) -> str:
    cfg, agg, hp = res["config"], res["aggregate"], res["hyperparameters"]
    reps = agg["replications"]
    L: List[str] = []
    L.append("# EXP-K4-001 report (study S4): deep irregular-time models, pre-training and scale")
    L.append("")
    L.append("> **SYNTHETIC DATA ONLY.** Nothing here is evidence about real patients. Every number below was written by "
             "`experiments/EXP-K4-001/run.py` from `results.json`; the design is `PREREG.md` (with its amendments).")
    L.append("")
    L.append(f"Replications: {len(reps)} ({reps[0]} to {reps[-1]}); base seed {res['seed_base']}; run time {res['run_seconds']} s on {res['workers']} workers "
             f"(machine-dependent); code hash `{res['code_hash']}`.")
    L.append("")
    if agg["canary"]["void"]:
        L.append(f"## VOID: the leakage canary failed (mean AUC {fmt(agg['canary']['mean_auc_g1'])}, accepted range {agg['canary']['range']}). "
                 "Every result below is declared void.")
        L.append("")
    L.append("## 1. Verdicts (pre-registered primary family, Bonferroni level "
             f"{fmt(agg['H1']['level'], 4)})")
    h1, h2, h3 = agg["H1"], agg["H2"], agg["H3"]
    L.append("")
    L.append("| Hypothesis | Quantity | Estimate | Interval | Rule | Verdict |")
    L.append("|---|---|---|---|---|---|")
    L.append(f"| H1 pre-training helps (N={cfg['n_h1']}, medium, mean of {len(cfg['f3'])} families) | AUC(PT-all) - AUC(scratch) | "
             f"{fmt(h1['delta'])} | [{fmt(h1['lo'])}, {fmt(h1['hi'])}] | lower > {h1['threshold']} | **{'MET' if h1['met'] else 'NOT MET'}** |")
    worst = min(h2["per_baseline"].items(), key=lambda kv: kv[1]["lo"])
    L.append(f"| H2 `{h2['designated_family']}` beats every classical baseline (N={cfg['n_h2']}) | weakest margin vs `{worst[0]}` | "
             f"{fmt(worst[1]['delta'])} | [{fmt(worst[1]['lo'])}, {fmt(worst[1]['hi'])}] | every lower bound > 0 | **{'MET' if h2['met'] else 'NOT MET'}** |")
    L.append(f"| H3 scale helps (N={cfg['n_h2']}, large vs medium) | AUC(large) - AUC(medium) | {fmt(h3['delta_large_minus_medium'])} | "
             f"[{fmt(h3['lo'])}, {fmt(h3['hi'])}] | helps if lower > {h3['threshold']}; does not help if upper < {h3['threshold']} | **{h3['class'].upper()}** |")
    L.append("")
    L.append("Consequences by the pre-registered kill rules: "
             + ("pre-training is claimed to help when labels are scarce (synthetic data only)" if h1["met"] else "**no pre-training is claimed or shipped; no pre-trained checkpoint is exported or registered**")
             + "; "
             + (f"`{h2['designated_family']}` beat every classical baseline in this synthetic study" if h2["met"] else "**K4 is not claimed to beat classical models and stays outside every production ensemble**")
             + "; "
             + ("a large network helped" if h3["class"] == "scale helps" else "**medium is the largest size anyone is told to use**") + ".")
    L.append("")
    L.append("### H2 detail (designated family chosen on development replications: "
             f"`{h2['designated_family']}`)")
    L.append("")
    L.append("| Baseline | AUC difference (designated minus baseline) | Interval | Beats |")
    L.append("|---|---|---|---|")
    for b, v in h2["per_baseline"].items():
        L.append(f"| `{b}` | {fmt(v['delta'])} | [{fmt(v['lo'])}, {fmt(v['hi'])}] | {'yes' if v['beats'] else 'no'} |")
    L.append("")
    L.append("## 2. Leakage canary")
    L.append("")
    L.append(f"GRU-D, medium, N={cfg['n_canary']}, {cfg['n_canary_perms']} label permutations per replication (all training rows, amendments A1 and A3), true test labels: mean G1 AUC "
             f"**{fmt(agg['canary']['mean_auc_g1'])}** over {agg['canary']['n_fits']} fits (standard deviation of one fit {fmt(agg['canary']['sd_per_fit'])}; accepted range {agg['canary']['range']}) -> **{'VOID' if agg['canary']['void'] else 'passes'}**.")
    L.append("")
    L.append("## 3. Strongest classical baseline first (G1 test, IPCW AUC at 365 days, mean over replications)")
    L.append("")
    L.append("| N | Strongest baseline | AUC | " + " | ".join(cfg["baselines"]) + " |")
    L.append("|---|---|---|" + "---|" * len(cfg["baselines"]))
    for n in cfg["n_grid"]:
        s = agg["strongest_baseline"][str(n)]
        L.append(f"| {n} | `{s['name']}` | {fmt(s['mean_auc_g1'])} | " + " | ".join(fmt(s["all"][b]) for b in cfg["baselines"]) + " |")
    L.append("")
    tab = pd.DataFrame(agg["table"])
    L.append("## 4. Zoo: six families, medium, trained from scratch (G1 AUC mean [95% interval over replications])")
    L.append("")
    L.append("| Family | " + " | ".join(f"N={n}" for n in cfg["n_grid"]) + " |")
    L.append("|---|" + "---|" * len(cfg["n_grid"]))
    for f in cfg["families"]:
        cells = []
        for n in cfg["n_grid"]:
            r = tab[(tab.family == f) & (tab["size"] == "medium") & (tab.arm == "scratch") & (tab.N == n)].iloc[0]
            cells.append(f"{fmt(r.auc_g1, 3)} [{fmt(r.auc_g1_lo, 3)}, {fmt(r.auc_g1_hi, 3)}]")
        L.append(f"| `{f}` | " + " | ".join(cells) + " |")
    L.append("")
    L.append("Ranking at N=%d: " % cfg["n_h2"] + ", ".join(f"`{r['family']}` {fmt(r['mean_auc_g1'], 3)}" for r in agg["ranking_n1000"]) + ".")
    L.append("")
    L.append("Smallest N at which a family (scratch, medium) reaches the strongest baseline's mean AUC at that N: "
             + ", ".join(f"`{f}`: {v if v is not None else 'never'}" for f, v in agg["smallest_n_reaching_strongest_baseline"].items()) + ".")
    L.append("")
    L.append("## 5. Pre-training (descriptive except H1): mean over the F3 families of AUC(arm) - AUC(scratch), medium")
    L.append("")
    L.append("| Arm | " + " | ".join(f"N={n}" for n in cfg["n_grid"]) + " |")
    L.append("|---|" + "---|" * len(cfg["n_grid"]))
    for arm in CORPORA:
        cells = []
        for n in cfg["n_grid"]:
            r = next(x for x in agg["pretraining_vs_scratch"] if x["arm"] == arm and x["N"] == n)
            cells.append(f"{fmt(r['delta_vs_scratch'], 3)} [{fmt(r['lo'], 3)}, {fmt(r['hi'], 3)}]")
        L.append(f"| `{arm}` | " + " | ".join(cells) + " |")
    L.append("")
    L.append("Masked-loss on 10% held-out corpus patients (mean over replications):")
    L.append("")
    L.append("| Family | Size | Corpus | Initial loss | Final loss |")
    L.append("|---|---|---|---|---|")
    for p in agg["pretrain_loss"]:
        L.append(f"| `{p['family']}` | {p['size']} | `{p['corpus']}` | {fmt(p['initial_val_loss'])} | {fmt(p['final_val_loss'])} |")
    L.append("")
    L.append("## 6. Scale (G1 AUC mean over replications, F3 families)")
    L.append("")
    L.append("| Family | Arm | Size | " + " | ".join(f"N={n}" for n in cfg["n_scale"]) + " |")
    L.append("|---|---|---|" + "---|" * len(cfg["n_scale"]))
    for f in cfg["f3"]:
        for arm in ("scratch", "pt_all"):
            for size in ("small", "medium", "large"):
                cells = []
                for n in cfg["n_scale"]:
                    q = tab[(tab.family == f) & (tab["size"] == size) & (tab.arm == arm) & (tab.N == n)]
                    cells.append(fmt(q.iloc[0].auc_g1, 3) if len(q) else "n/a")
                L.append(f"| `{f}` | {arm} | {size} | " + " | ".join(cells) + " |")
    L.append("")
    L.append(f"Medium minus small (scratch, N={cfg['n_h2']}, F3 mean): {fmt(h3['medium_minus_small']['delta'])} "
             f"[{fmt(h3['medium_minus_small']['lo'])}, {fmt(h3['medium_minus_small']['hi'])}] (95%, descriptive).")
    L.append("")
    L.append("## 7. Cross-generator tests (trained on G1 labels only; AUC mean, medium, scratch)")
    L.append("")
    L.append("| Model | N | G1 AUC | G2 AUC | G3 AUC | G1 ECE | G1 Brier |")
    L.append("|---|---|---|---|---|---|---|")
    for n in (cfg["n_h2"],):
        for b in cfg["baselines"]:
            r = tab[(tab.family == b) & (tab.arm == "classical") & (tab.N == n)].iloc[0]
            L.append(f"| `{b}` | {n} | {fmt(r.auc_g1, 3)} | {fmt(r.auc_g2, 3)} | {fmt(r.auc_g3, 3)} | {fmt(r.ece_g1, 3)} | {fmt(r.brier_g1, 3)} |")
        for f in cfg["families"]:
            r = tab[(tab.family == f) & (tab["size"] == "medium") & (tab.arm == "scratch") & (tab.N == n)].iloc[0]
            L.append(f"| `{f}` | {n} | {fmt(r.auc_g1, 3)} | {fmt(r.auc_g2, 3)} | {fmt(r.auc_g3, 3)} | {fmt(r.ece_g1, 3)} | {fmt(r.brier_g1, 3)} |")
    L.append("")
    L.append("## 8. Cost (machine-dependent; measured on the machine that ran the study, one thread, 8 visits)")
    L.append("")
    L.append("| Family | Size | Parameters | State bytes | Latency median ms | p95 ms |")
    L.append("|---|---|---|---|---|---|")
    for c in res["cost"]:
        L.append(f"| `{c['family']}` | {c['size']} | {c['params']} | {c['state_bytes']} | {fmt(c['median_ms'], 2)} | {fmt(c['p95_ms'], 2)} |")
    L.append("")
    L.append("## 9. Export checks (safetensors exact round trip and ONNX parity, replication 0, N=%d model)" % cfg["n_h2"])
    L.append("")
    L.append("| Family | Safetensors exact | ONNX max abs difference | Sequences |")
    L.append("|---|---|---|---|")
    for e in res["exports"]:
        L.append(f"| `{e['family']}` | {e['safetensors_exact']} | {e['onnx_max_abs_diff']:.2e} | {e['n_sequences']} |")
    L.append("")
    L.append("## 10. Selected hyper-parameters (development replications only; `hyperparameters.json`)")
    L.append("")
    L.append("| Family | Scratch lr | Fine-tune lr |")
    L.append("|---|---|---|")
    for f in cfg["families"]:
        L.append(f"| `{f}` | {hp['lr_scratch'].get(f)} | {hp['lr_finetune'].get(f, 'n/a')} |")
    L.append("")
    L.append(f"Designated family for H2: `{hp['designated_family']}`. Baseline fits that failed and fell back to a constant prediction: "
             f"{agg['baseline_fit_failures']}.")
    L.append("")
    L.append("## 11. Not built (PREREG section 4)")
    L.append("")
    L.append("TabPFN-style prior-fitted networks, the contrastive pre-training objective, the adjoint and log-signature options of Neural CDE, "
             "and the GRU-ODE-Bayes variational observation model were not built and are not approximated.")
    L.append("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------------------------------------
def specs_full(kind: str, reps: List[int], hp: Dict[str, Any], scope: str) -> List[Tuple]:
    heavy_first = ["gru_ode_bayes", "neural_cde", "ssm", "ct_transformer", "grud", "gruwe"]
    sp = [("family", kind, r, f, hp, scope) for r in reps for f in heavy_first]
    sp += [("baselines", kind, r, None, None, scope) for r in reps]
    return sp


def build_results(kind: str, reps: List[int], hp: Dict[str, Any], scope: str, workers: int, tag: str) -> Dict[str, Any]:
    t0 = time.time()
    done = execute(specs_full(kind, reps, hp, scope), tag, workers)
    merged = merge(done)
    cfg = design(scope)
    payload = {
        "config": cfg, "hyperparameters": hp, "records": merged["records"], "pretrain": merged["pretrain"],
        "exports": merged["exports"], "cost": merged["cost"],
        "seed_base": base_seed(kind, 0), "workers": workers, "code_hash": code_hash(),
    }
    payload["aggregate"] = aggregate(payload)
    payload["run_seconds"] = int(time.time() - t0)
    return payload


def mode_dev(workers: int) -> None:
    kind, reps = "dev", list(range(CONFIG["seeds"]["dev"]["n"]))
    t0 = time.time()
    done = execute([("grid", kind, r, f, None, "full") for r in reps for f in CONFIG["families"]], "grid", workers)
    merged = merge(done)
    dev = pd.DataFrame(merged["records"])
    hp = select_hyperparameters(dev, CONFIG)
    hp["selected_on"] = {"replications": [base_seed(kind, r) for r in reps], "n": CONFIG["lr_selection_n"], "size": "medium"}
    # designated family: scratch medium N=1000 at the selected scratch rate (the grid already has both rates; read the selected one)
    sel = dev[(dev.arm == "scratch") & (dev["size"] == "medium") & (dev.N == CONFIG["n_h2"])]
    sel = sel[[bool(abs(lr - hp["lr_scratch"][f]) < 1e-12) for f, lr in zip(sel.family, sel.lr)]]
    des, means = designated_family(sel, CONFIG)
    hp["designated_family"], hp["designated_means_dev_auc"] = des, means
    (OUT / "hyperparameters.json").write_text(json.dumps(hp, indent=2) + "\n")
    (OUT / "dev_grid.json").write_text(json.dumps({"records": merged["records"], "pretrain": merged["pretrain"],
                                                   "code_hash": code_hash(), "run_seconds": int(time.time() - t0)}, indent=1) + "\n")
    print(f"[dev] hyperparameters.json written; designated family {des}", flush=True)


def mode_dev_pipeline(workers: int) -> None:
    hp = json.loads((OUT / "hyperparameters.json").read_text())
    res = build_results("dev", list(range(CONFIG["seeds"]["dev"]["n"])), hp, "full", workers, "devfull")
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1) + "\n")
    print("[dev] dev_results.json written (pipeline check on development replications; not evidence)", flush=True)


def mode_frozen(workers: int) -> None:
    hp = json.loads((OUT / "hyperparameters.json").read_text())
    res = build_results("frozen", list(range(CONFIG["seeds"]["frozen"]["n"])), hp, "full", workers, "frozen")
    (OUT / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    (OUT / "REPORT.md").write_text(render_report(res))
    print("[frozen] results.json and REPORT.md written", flush=True)


def mode_smoke(workers: int) -> Dict[str, Any]:
    import tempfile

    global WORK
    with tempfile.TemporaryDirectory() as d:
        WORK = Path(d)
        specs = [("grid", "smoke", 0, f, None, "smoke") for f in CONFIG["families"]]
        done = execute(specs, "grid", workers)
        dev = pd.DataFrame(merge(done)["records"])
        cfg = design("smoke")
        cfg["lr_selection_n"] = cfg["n_scale"]
        hp = select_hyperparameters(dev, cfg)
        hp["designated_family"] = "grud"
        res = build_results("smoke", [0, 1], hp, "smoke", workers, "smoke")
        render_report(res)
        return res


def mode_rerender() -> None:
    res = json.loads((OUT / "results.json").read_text())
    res["aggregate"] = json.loads(json.dumps(aggregate(res)))
    (OUT / "REPORT.md").write_text(render_report(res))


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    for k in ("dev", "dev-pipeline", "frozen", "smoke", "rerender"):
        g.add_argument(f"--{k}", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.dev:
        mode_dev(a.workers)
    elif a.dev_pipeline:
        mode_dev_pipeline(a.workers)
    elif a.frozen:
        mode_frozen(a.workers)
    elif a.smoke:
        res = mode_smoke(a.workers)
        print(json.dumps(res["aggregate"]["H1"], indent=1))
    else:
        mode_rerender()
    return 0


if __name__ == "__main__":
    sys.exit(main())
