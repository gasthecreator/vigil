#!/usr/bin/env python3
"""EXP-K5-001 runner. Specification: experiments/EXP-K5-001/PREREG.md. Every number in the outputs is computed here.

    uv run python experiments/EXP-K5-001/run.py --dev        # replications 0..9 -> dev_results.json
    uv run python experiments/EXP-K5-001/run.py --frozen     # replications 0..99 -> results.json, REPORT.md (run ONCE)
    uv run python experiments/EXP-K5-001/run.py --smoke      # 2 tiny replications, nothing written (used by tests)

The estimators (vigil_ml.k5) receive only patient, visit day, laboratory and value. True offsets and the clinical
truth are used here, only to *score* the methods.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for pkg in ("vigil-sim", "vigil-ml", "vigil-core", "vigil-eval"):
    sys.path.insert(0, str(ROOT / "packages" / pkg))

from vigil_ml import k5  # noqa: E402
from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402
from vigil_sim.multilab import (  # noqa: E402
    LabShift,
    MultiLabCohort,
    MultiLabConfig,
    apply_multilab,
    draw_true_beta,
)

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------------------------
# Fixed design (PREREG sections 3 to 7). Written into results.json as `config`.
# ---------------------------------------------------------------------------------------------
CONFIG: Dict[str, Any] = {
    "n_patients_train": 800,
    "n_patients_eval": 800,
    "duration_days": 730.0,
    "tau_grid": [0.07, 0.15, 0.30],
    "switch_grid": [0.10, 0.30],
    "primary_cell": {"tau": 0.15, "switch_fraction": 0.30},
    "sourced_tau": 0.07,
    "new_site_k": [0, 3, 10, 30],
    "rule_rise": 1.25,
    "sens_window_days": 180.0,
    "materiality_far": 0.05,
    "recovered_min_excess": 0.01,
    "h3_recovered_min": 0.5,
    "h3_sens_tolerance": 0.03,
    "h4_coverage": [0.90, 0.99],
    "h5_power": 0.8,
    "h5_median_delay_days": 120.0,
    "h5_null_alarms_per_1000": 1.0,
    "cusum_slack": 0.5,
    "cusum_max_alarms_per_obs": 1.0 / 1500.0,
    "shift_lab": 2,
    "shift_calendar_day": 365.0,
    "shift_deltas": [0.0, 0.10, 0.20, 0.30],
    "power_window_days": 180.0,
    "detector_cell": {"tau": 0.07, "switch_fraction": 0.30},
    "bootstrap_B": 2000,
    "bootstrap_seed": 20261101,
    "bonferroni_m": 3,
    "seeds": {
        "dev": {"base": 100, "step": 10},
        "calibration": {"base": 500000, "step": 10},
        "frozen": {"base": 20261101, "step": 10},
    },
    "control_noise_sd": 0.08,
    "control_slope_sd_per_day": 0.0005,
    "control_level_sd": 0.5,
    "control_level_median": 30.0,
    "n_dev": 10,
    "n_calibration": 20,
    "n_frozen": 100,
}
METHODS = ["pooled", "legacy", "fixed", "k5", "oracle"]


def seeds_for(kind: str, r: int) -> Tuple[int, int, int]:
    s = CONFIG["seeds"][kind]
    base = s["base"] + s["step"] * r
    return base, base + 1, base + 2


# ---------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------
def clinical_cohort(seed: int, n: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=seed).generate_cohort(
        num_patients=n, duration_days=CONFIG["duration_days"]
    )
    return cohort.to_observations_dataframe(), cohort.to_patients_dataframe()


def loglinear_control(obs: pd.DataFrame, pts: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Control (Amendment 2): keep the simulator's visit schedule, replace CA 15-3 by values for which the K5 model
    is exactly true: log y = a_i + b_i t + eps, with no recurrence dynamics. Not a clinical model."""
    rng = np.random.default_rng(seed + 7)
    o = obs[["patient_id", "day", "ca_15_3"]].dropna(subset=["ca_15_3"])
    o = o[o["ca_15_3"] > 0].copy()
    ids = o["patient_id"].unique()
    a = dict(zip(ids, rng.normal(math.log(CONFIG["control_level_median"]), CONFIG["control_level_sd"], len(ids))))
    b = dict(zip(ids, rng.normal(0.0, CONFIG["control_slope_sd_per_day"], len(ids))))
    t = o["day"].to_numpy(dtype=float)
    mu = o["patient_id"].map(a).to_numpy(dtype=float) + o["patient_id"].map(b).to_numpy(dtype=float) * t
    o["ca_15_3"] = np.exp(mu + rng.normal(0.0, CONFIG["control_noise_sd"], len(o)))
    return o


def fit_inputs(c: MultiLabCohort) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exactly what an estimator may see: patient, visit day, laboratory, value."""
    o = c.observations
    return (
        o["patient_id"].to_numpy(),
        o["day"].to_numpy(dtype=float),
        o["lab"].to_numpy(),
        o["y"].to_numpy(dtype=float),
    )


def estimate_offsets(train: MultiLabCohort) -> Dict[str, Dict[str, float]]:
    """Per-method offsets (dictionary lab -> log offset) for pooled, legacy, fixed and k5."""
    patient, t, lab, y = fit_inputs(train)
    system = k5.build_projected_system(patient, t, lab, y)
    fixed = k5.fit_fixed(system)
    kfit = k5.fit_k5(system)
    labs = sorted(set(str(x) for x in lab))
    return {
        "pooled": {x: 0.0 for x in labs},
        "legacy": k5.fit_legacy_mean_shrinkage(lab, y),
        "fixed": {x: float(b) for x, b in zip(fixed.lab_ids, fixed.beta)},
        "k5": {x: float(b) for x, b in zip(kfit.lab_ids, kfit.beta)},
        "_fits": {"fixed": fixed, "k5": kfit},  # type: ignore[dict-item]
    }


def method_contrast(method: str, offsets: Dict[str, Any], a: int, b: int) -> float:
    off = offsets[method]
    return float(off.get(str(a), 0.0) - off.get(str(b), 0.0))


# ---------------------------------------------------------------------------------------------
# E1: contrasts and coverage
# ---------------------------------------------------------------------------------------------
def e1_contrasts(
    offsets: Dict[str, Any], true_beta: Dict[int, float], pairs: List[Tuple[int, int]]
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    truth = np.array([true_beta[a] - true_beta[b] for a, b in pairs])
    for m in ("pooled", "legacy", "fixed", "k5"):
        est = np.array([method_contrast(m, offsets, a, b) for a, b in pairs])
        out[m] = {"rmse": float(np.sqrt(np.mean((est - truth) ** 2)))}
    out["oracle"] = {"rmse": 0.0}
    for m in ("fixed", "k5"):
        fit = offsets["_fits"][m]
        covered, n = 0, 0
        for (a, b), tr in zip(pairs, truth):
            est, sd = fit.contrast(str(a), str(b))
            if math.isfinite(sd) and sd > 0:
                n += 1
                covered += int(abs(est - tr) <= 1.96 * sd)
        out[m]["covered"], out[m]["n_intervals"] = covered, n
    return out


# ---------------------------------------------------------------------------------------------
# E2: rule R
# ---------------------------------------------------------------------------------------------
def harmonised_log(c: MultiLabCohort, off: Dict[str, float]) -> np.ndarray:
    o = c.observations
    beta = np.array([off.get(str(x), 0.0) for x in o["lab"].to_numpy()], dtype=float)
    return np.log(o["y"].to_numpy(dtype=float)) - beta


def rule_alerts(c: MultiLabCohort, h: np.ndarray) -> np.ndarray:
    """Alert at result j >= 2 when h_j - mean(h_1..h_{j-1}) >= log(1.25), per patient in visit order."""
    o = c.observations
    alert = np.zeros(len(o), dtype=bool)
    rise = math.log(CONFIG["rule_rise"])
    pid = o["patient_id"].to_numpy()
    vis = o["visit_idx"].to_numpy()
    order = np.lexsort((vis, pid))
    run_sum, run_n, prev = 0.0, 0, None
    for idx in order:
        if pid[idx] != prev:
            run_sum, run_n, prev = 0.0, 0, pid[idx]
        if run_n >= 1 and (h[idx] - run_sum / run_n) >= rise:
            alert[idx] = True
        run_sum += h[idx]
        run_n += 1
    return alert


def far_sens(c: MultiLabCohort, alert: np.ndarray, mask: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Patient-level FAR (no recurrence) and Sens (recurrence, result in the 180 days before it)."""
    o = c.observations.assign(alert=alert)
    if mask is not None:
        o = o[mask]
    pts = c.patients.set_index("patient_id")
    far_num = far_den = sens_num = sens_den = sens_excl = 0
    any_alert = o.groupby("patient_id")["alert"].any()
    for pid, row in pts.iterrows():
        if pid not in set(o["patient_id"]):
            continue
        rec = bool(row["true_recurrence_event"])
        if not rec:
            far_den += 1
            far_num += int(bool(any_alert.get(pid, False)))
        else:
            rd = float(row["true_recurrence_day"])
            sub = o[(o["patient_id"] == pid) & (o["day"] <= rd) & (o["day"] >= rd - CONFIG["sens_window_days"])]
            if len(sub) == 0:
                sens_excl += 1
            else:
                sens_den += 1
                sens_num += int(bool(sub["alert"].any()))
    return {
        "far_num": far_num,
        "far_den": far_den,
        "sens_num": sens_num,
        "sens_den": sens_den,
        "sens_excluded": sens_excl,
    }


def e2_rule(eval_c: MultiLabCohort, offsets: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    methods = {m: offsets[m] for m in ("pooled", "legacy", "fixed", "k5")}
    methods["oracle"] = {str(k): v for k, v in eval_c.true_beta.items()}
    for m, off in methods.items():
        h = harmonised_log(eval_c, off)
        out[m] = far_sens(eval_c, rule_alerts(eval_c, h))
    return out


# ---------------------------------------------------------------------------------------------
# E3 / E4: detector
# ---------------------------------------------------------------------------------------------
def lab_streams(
    c: MultiLabCohort, h: np.ndarray
) -> Dict[int, Dict[str, np.ndarray]]:
    o = c.observations
    r = k5.one_step_residuals(o["patient_id"].to_numpy(), o["calendar_day"].to_numpy(), h)
    out: Dict[int, Dict[str, np.ndarray]] = {}
    for lab in sorted(set(o["lab"].to_numpy().tolist())):
        sel = (o["lab"].to_numpy() == lab) & np.isfinite(r)
        idx = np.flatnonzero(sel)
        idx = idx[np.argsort(o["calendar_day"].to_numpy()[idx], kind="stable")]
        out[int(lab)] = {"r": r[idx], "cal": o["calendar_day"].to_numpy()[idx], "obs_index": idx}
    return out


def chart_alarms(x: np.ndarray, slack: float, h_star: float) -> List[int]:
    s, alarms = 0.0, []
    for n, v in enumerate(x):
        s = max(0.0, s + float(v) - slack)
        if s >= h_star:
            alarms.append(n)
            s = 0.0
    return alarms


def calibrate_detector(n_rep: int, kind: str = "calibration") -> Dict[str, float]:
    tau, sw = CONFIG["detector_cell"]["tau"], CONFIG["detector_cell"]["switch_fraction"]
    resid: List[np.ndarray] = []
    per_stream: List[np.ndarray] = []
    per_stream_nonrec: List[np.ndarray] = []
    for r in range(n_rep):
        s_tr, s_ev, s_lab = seeds_for(kind, r)
        beta = draw_true_beta(s_lab, tau, 6)
        tr_obs, tr_pts = clinical_cohort(s_tr, CONFIG["n_patients_train"])
        ev_obs, ev_pts = clinical_cohort(s_ev, CONFIG["n_patients_eval"])
        train = apply_multilab(tr_obs, tr_pts, MultiLabConfig(tau, sw, s_lab + 1_000_000), beta)
        ev = apply_multilab(ev_obs, ev_pts, MultiLabConfig(tau, sw, s_lab + 2_000_000), beta)
        harm = k5.LabHarmoniserK5().fit(*fit_inputs(train))
        h = np.log(harm.harmonise(ev.observations["lab"].to_numpy(), ev.observations["y"].to_numpy()))
        rec = ev.patients.set_index("patient_id")["true_recurrence_event"].astype(bool)
        pid_of_obs = ev.observations["patient_id"].to_numpy()
        for lab, st in lab_streams(ev, h).items():
            per_stream.append(st["r"])
            resid.append(st["r"])
            nonrec = ~rec.reindex(pid_of_obs[st["obs_index"]]).to_numpy()
            per_stream_nonrec.append(st["r"][nonrec])
    sigma_r = k5.mad_sd(np.concatenate(resid))
    std_streams = [s / sigma_r for s in per_stream]
    n_res = int(sum(len(s) for s in std_streams))
    h_star = k5.calibrate_cusum_threshold(
        std_streams, slack=CONFIG["cusum_slack"], max_alarms_per_obs=CONFIG["cusum_max_alarms_per_obs"]
    )
    slack = CONFIG["cusum_slack"]
    achieved = k5.cusum_alarm_count(std_streams, slack, h_star) / max(n_res, 1)
    # Diagnostic (added by Amendment 2; not used to choose anything): alarm rate against threshold, all residuals
    # and only residuals of patients without a recurrence event.
    nonrec_std = [s / sigma_r for s in per_stream_nonrec]
    n_nonrec = int(sum(len(s) for s in nonrec_std))
    curve = {
        f"{t:g}": {
            "all_per_1000": 1000.0 * k5.cusum_alarm_count(std_streams, slack, t) / max(n_res, 1),
            "non_recurrent_per_1000": 1000.0 * k5.cusum_alarm_count(nonrec_std, slack, t) / max(n_nonrec, 1),
        }
        for t in (2, 5, 10, 15, 30, 60)
    }
    return {
        "sigma_r": sigma_r, "h_star": h_star, "n_streams": len(std_streams), "n_residuals": n_res,
        "achieved_alarms_per_1000_at_h_star": 1000.0 * achieved,
        "target_alarms_per_1000": 1000.0 * CONFIG["cusum_max_alarms_per_obs"],
        "target_attained": bool(achieved <= CONFIG["cusum_max_alarms_per_obs"]),
        "diagnostic_alarm_rate_vs_threshold": curve,
    }


def e3_e4(
    ev_obs: pd.DataFrame, ev_pts: pd.DataFrame, harmoniser: k5.LabHarmoniserK5, beta: Dict[int, float],
    s_lab: int, det: Dict[str, float],
) -> Dict[str, Any]:
    tau, sw = CONFIG["detector_cell"]["tau"], CONFIG["detector_cell"]["switch_fraction"]
    out: Dict[str, Any] = {}
    shift_lab, t0 = CONFIG["shift_lab"], CONFIG["shift_calendar_day"]
    for delta in CONFIG["shift_deltas"]:
        shift = LabShift(shift_lab, delta, t0) if delta != 0.0 else None
        ev = apply_multilab(ev_obs, ev_pts, MultiLabConfig(tau, sw, s_lab + 2_000_000, shift=shift), beta)
        hv = np.log(harmoniser.harmonise(ev.observations["lab"].to_numpy(), ev.observations["y"].to_numpy()))
        streams = lab_streams(ev, hv)
        null_alarms = null_resid = 0
        shifted: Dict[str, Any] = {}
        alarm_cal_shift: Optional[float] = None
        for lab, st in streams.items():
            z = st["r"] / det["sigma_r"]
            al = chart_alarms(z, CONFIG["cusum_slack"], det["h_star"])
            if lab == shift_lab and delta != 0.0:
                after = [n for n in al if t0 <= st["cal"][n] <= t0 + CONFIG["power_window_days"]]
                before = [n for n in al if st["cal"][n] < t0]
                shifted["pre_shift_alarms"] = len(before)
                shifted["n_residuals"] = int(len(z))
                if after:
                    n0 = after[0]
                    alarm_cal_shift = float(st["cal"][n0])
                    shifted["detected"] = True
                    shifted["delay_days"] = float(st["cal"][n0] - t0)
                    shifted["delay_results"] = int(np.sum((st["cal"] >= t0) & (np.arange(len(z)) <= n0)))
                else:
                    shifted["detected"] = False
                null_alarms += len(before)
                null_resid += int(np.sum(st["cal"] < t0))
            else:
                null_alarms += len(al)
                null_resid += int(len(z))
        out[f"delta_{delta:.2f}"] = {
            "null_alarms": int(null_alarms),
            "null_residuals": int(null_resid),
            "shifted": shifted,
        }
        if delta == 0.20:
            out["e4"] = e4_withholding(ev, hv, streams[shift_lab], det, alarm_cal_shift)
    return out


def e4_withholding(
    ev: MultiLabCohort, hv: np.ndarray, st_shift: Dict[str, np.ndarray], det: Dict[str, float],
    alarm_cal: Optional[float],
) -> Dict[str, Any]:
    o = ev.observations
    alert = rule_alerts(ev, hv)
    post = (o["lab"].to_numpy() == CONFIG["shift_lab"]) & (o["calendar_day"].to_numpy() >= CONFIG["shift_calendar_day"])
    # patients with at least one result at the shifted laboratory after the shift
    keep_patients = set(o.loc[post, "patient_id"].tolist())
    cohort_mask = o["patient_id"].isin(keep_patients).to_numpy()
    plain = far_sens(ev, alert & post, cohort_mask)
    if alarm_cal is None:
        withheld = plain
    else:
        w_alert = alert & post & (o["calendar_day"].to_numpy() < alarm_cal)
        withheld = far_sens(ev, w_alert, cohort_mask)
    return {"without_withholding": plain, "with_withholding": withheld, "alarm_calendar_day": alarm_cal}


# ---------------------------------------------------------------------------------------------
# One replication
# ---------------------------------------------------------------------------------------------
def replication(args: Tuple[str, int, Dict[str, float], bool]) -> Dict[str, Any]:
    kind, r, det, smoke = args
    s_tr, s_ev, s_lab = seeds_for(kind, r)
    n_tr = 150 if smoke else CONFIG["n_patients_train"]
    n_ev = 150 if smoke else CONFIG["n_patients_eval"]
    tr_obs, tr_pts = clinical_cohort(s_tr, n_tr)
    ev_obs, ev_pts = clinical_cohort(s_ev, n_ev)
    res: Dict[str, Any] = {"r": r, "seeds": [s_tr, s_ev, s_lab], "cells": {}}

    cells: List[Tuple[float, float, bool]] = [(t, p, False) for t in CONFIG["tau_grid"] for p in CONFIG["switch_grid"]]
    pc = CONFIG["primary_cell"]
    cells.append((pc["tau"], pc["switch_fraction"], True))  # case-mix scenario
    for tau, sw, case_mix in cells:
        key = f"tau{tau:.2f}_sw{sw:.2f}" + ("_casemix" if case_mix else "")
        beta = draw_true_beta(s_lab, tau, 6)
        train = apply_multilab(tr_obs, tr_pts, MultiLabConfig(tau, sw, s_lab + 1_000_000, case_mix=case_mix), beta)
        ev = apply_multilab(ev_obs, ev_pts, MultiLabConfig(tau, sw, s_lab + 2_000_000, case_mix=case_mix), beta)
        off = estimate_offsets(train)
        pairs = [(a, b) for a in range(6) for b in range(a + 1, 6)]
        res["cells"][key] = {
            "tau": tau, "switch_fraction": sw, "case_mix": case_mix,
            "tau_hat": float(off["_fits"]["k5"].tau),
            "e1": e1_contrasts(off, beta, pairs),
            "e2": e2_rule(ev, off),
        }

    # control: the K5 model is exactly true (Amendment 2); primary cell only
    ptau, psw = pc["tau"], pc["switch_fraction"]
    beta = draw_true_beta(s_lab, ptau, 6)
    ctr = apply_multilab(loglinear_control(tr_obs, tr_pts, s_tr), tr_pts, MultiLabConfig(ptau, psw, s_lab + 1_000_000), beta)
    off = estimate_offsets(ctr)
    res["control_loglinear"] = {
        "tau_hat": float(off["_fits"]["k5"].tau),
        "e1": e1_contrasts(off, beta, [(a, b) for a in range(6) for b in range(a + 1, 6)]),
    }

    # new-site scenario in the primary cell
    tau, sw = pc["tau"], pc["switch_fraction"]
    beta8 = draw_true_beta(s_lab, tau, 8)
    res["new_site"] = {}
    for k in CONFIG["new_site_k"]:
        mode = "new_site_training" if k > 0 else "network"
        train = apply_multilab(
            tr_obs, tr_pts,
            MultiLabConfig(tau, sw, s_lab + 3_000_000, mode=mode, new_site_switchers=k), beta8
        )
        evn = apply_multilab(ev_obs, ev_pts, MultiLabConfig(tau, sw, s_lab + 4_000_000, mode="new_site_eval"), beta8)
        off = estimate_offsets(train)
        pairs = [(a, b) for a in (6, 7) for b in range(6)]
        res["new_site"][f"k{k}"] = {"e1": e1_contrasts(off, beta8, pairs), "e2": e2_rule(evn, off)}

    # detector (frozen replications and development only; thresholds come from calibration replications)
    if det:
        dtau, dsw = CONFIG["detector_cell"]["tau"], CONFIG["detector_cell"]["switch_fraction"]
        beta = draw_true_beta(s_lab, dtau, 6)
        train = apply_multilab(tr_obs, tr_pts, MultiLabConfig(dtau, dsw, s_lab + 1_000_000), beta)
        harm = k5.LabHarmoniserK5().fit(*fit_inputs(train))
        res["detector"] = e3_e4(ev_obs, ev_pts, harm, beta, s_lab, det)
    return res


# ---------------------------------------------------------------------------------------------
# Aggregation, hypotheses
# ---------------------------------------------------------------------------------------------
def rate(d: Dict[str, float], num: str, den: str) -> float:
    return d[num] / d[den] if d[den] else float("nan")


def boot_ci(values_fn, n_rep: int, B: int, seed: int, level: float) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(B):
        idx = rng.integers(0, n_rep, n_rep)
        stats.append(values_fn(idx))
    stats = np.array([s for s in stats if np.isfinite(s)])
    a = (1 - level) / 2
    return float(np.quantile(stats, a)), float(np.quantile(stats, 1 - a))


def aggregate(
    reps: List[Dict[str, Any]], bootstrap_replicates: Optional[int] = None
) -> Dict[str, Any]:
    n = len(reps)
    B = CONFIG["bootstrap_B"] if bootstrap_replicates is None else bootstrap_replicates
    if B < 1:
        raise ValueError("bootstrap_replicates must be at least one")
    seed = CONFIG["bootstrap_seed"]
    lvl_family = 1 - 0.05 / CONFIG["bonferroni_m"]
    agg: Dict[str, Any] = {"n_replications": n, "cells": {}, "new_site": {}}

    def far_sens_mean(cell_key: str, m: str, idx: np.ndarray, src: str = "cells") -> Tuple[float, float]:
        far, sens = [], []
        for i in idx:
            d = reps[i][src][cell_key]["e2"][m] if src == "cells" else reps[i]["new_site"][cell_key]["e2"][m]
            far.append(rate(d, "far_num", "far_den"))
            sens.append(rate(d, "sens_num", "sens_den"))
        return float(np.nanmean(far)), float(np.nanmean(sens))

    for key in reps[0]["cells"]:
        cell: Dict[str, Any] = {"tau": reps[0]["cells"][key]["tau"], "switch_fraction": reps[0]["cells"][key]["switch_fraction"],
                                "case_mix": reps[0]["cells"][key]["case_mix"]}
        cell["tau_hat_mean"] = float(np.mean([r["cells"][key]["tau_hat"] for r in reps]))
        cell["e1_rmse"] = {m: float(np.mean([r["cells"][key]["e1"][m]["rmse"] for r in reps])) for m in METHODS}
        for m in ("fixed", "k5"):
            cov = sum(r["cells"][key]["e1"][m]["covered"] for r in reps)
            tot = sum(r["cells"][key]["e1"][m]["n_intervals"] for r in reps)
            cell.setdefault("e1_coverage", {})[m] = cov / tot if tot else None
        all_idx = np.arange(n)
        cell["e2"] = {}
        for m in METHODS:
            far, sens = far_sens_mean(key, m, all_idx)
            cell["e2"][m] = {"far": far, "sens": sens}
        far_p, far_o = cell["e2"]["pooled"]["far"], cell["e2"]["oracle"]["far"]
        cell["excess_far_pooled"] = far_p - far_o
        cell["h1_material"] = bool(far_p - far_o >= CONFIG["materiality_far"])
        cell["recovered_fraction"] = {}
        for m in ("legacy", "fixed", "k5"):
            if far_p - far_o >= CONFIG["recovered_min_excess"]:
                def stat(idx, m=m, key=key):
                    fp, _ = far_sens_mean(key, "pooled", idx)
                    fo, _ = far_sens_mean(key, "oracle", idx)
                    fm, _ = far_sens_mean(key, m, idx)
                    return (fp - fm) / (fp - fo) if (fp - fo) > 1e-9 else float("nan")
                est = (far_p - cell["e2"][m]["far"]) / (far_p - far_o)
                lo, hi = boot_ci(stat, n, B, seed, 0.95)
                lo_f, _ = boot_ci(stat, n, B, seed, lvl_family)
                cell["recovered_fraction"][m] = {"estimate": est, "ci95": [lo, hi], "ci_family_lower": lo_f}
            else:
                cell["recovered_fraction"][m] = None
        agg["cells"][key] = cell

    ctl: Dict[str, Any] = {
        "tau_hat_mean": float(np.mean([r["control_loglinear"]["tau_hat"] for r in reps])),
        "e1_rmse": {m: float(np.mean([r["control_loglinear"]["e1"][m]["rmse"] for r in reps])) for m in METHODS},
        "e1_coverage": {},
    }
    for m in ("fixed", "k5"):
        cov = sum(r["control_loglinear"]["e1"][m]["covered"] for r in reps)
        tot = sum(r["control_loglinear"]["e1"][m]["n_intervals"] for r in reps)
        ctl["e1_coverage"][m] = cov / tot if tot else None
    agg["control_loglinear"] = ctl

    for kk in reps[0]["new_site"]:
        ns: Dict[str, Any] = {"e1_rmse": {m: float(np.mean([r["new_site"][kk]["e1"][m]["rmse"] for r in reps])) for m in METHODS}}
        for m in ("fixed", "k5"):
            cov = sum(r["new_site"][kk]["e1"][m]["covered"] for r in reps)
            tot = sum(r["new_site"][kk]["e1"][m]["n_intervals"] for r in reps)
            ns.setdefault("e1_coverage", {})[m] = cov / tot if tot else None
            ns.setdefault("n_intervals", {})[m] = tot
        diff = np.array([r["new_site"][kk]["e1"]["fixed"]["rmse"] - r["new_site"][kk]["e1"]["k5"]["rmse"] for r in reps])
        ns["rmse_fixed_minus_k5"] = {"mean": float(diff.mean())}
        for lvl_name, lvl in (("ci95", 0.95), ("ci_family", lvl_family)):
            lo, hi = boot_ci(lambda idx: float(diff[idx].mean()), n, B, seed, lvl)
            ns["rmse_fixed_minus_k5"][lvl_name] = [lo, hi]
        far_sens = {}
        for m in ("pooled", "fixed", "k5", "oracle"):
            f, s = far_sens_mean(kk, m, np.arange(n), src="new_site")
            far_sens[m] = {"far": f, "sens": s}
        ns["e2_descriptive"] = far_sens
        agg["new_site"][kk] = ns

    if "detector" in reps[0]:
        det: Dict[str, Any] = {}
        for dk in [k for k in reps[0]["detector"] if k.startswith("delta_")]:
            rows = [r["detector"][dk] for r in reps]
            null_alarms = sum(x["null_alarms"] for x in rows)
            null_res = sum(x["null_residuals"] for x in rows)
            entry: Dict[str, Any] = {"null_alarms_per_1000": 1000.0 * null_alarms / max(null_res, 1),
                                     "null_alarms": null_alarms, "null_residuals": null_res}
            sh = [x["shifted"] for x in rows if x["shifted"]]
            if sh:
                detected = [s for s in sh if s.get("detected")]
                entry["power"] = len(detected) / len(sh)
                entry["n_replications"] = len(sh)
                if detected:
                    d = np.array([s["delay_days"] for s in detected])
                    dr = np.array([s["delay_results"] for s in detected])
                    entry["delay_days_median"] = float(np.median(d))
                    entry["delay_days_iqr"] = [float(np.quantile(d, 0.25)), float(np.quantile(d, 0.75))]
                    entry["delay_results_median"] = float(np.median(dr))
            det[dk] = entry
        e4 = {}
        for arm in ("without_withholding", "with_withholding"):
            f_n = sum(r["detector"]["e4"][arm]["far_num"] for r in reps)
            f_d = sum(r["detector"]["e4"][arm]["far_den"] for r in reps)
            s_n = sum(r["detector"]["e4"][arm]["sens_num"] for r in reps)
            s_d = sum(r["detector"]["e4"][arm]["sens_den"] for r in reps)
            e4[arm] = {"far": f_n / f_d if f_d else None, "far_num": f_n, "far_den": f_d,
                       "sens": s_n / s_d if s_d else None, "sens_num": s_n, "sens_den": s_d}
        agg["detector"] = det
        agg["e4_descriptive"] = e4
    agg["hypotheses"] = judge(agg)
    return agg


def judge(agg: Dict[str, Any]) -> Dict[str, Any]:
    h: Dict[str, Any] = {}
    cells = agg["cells"]
    h["H1"] = {k: {"excess_far_pooled": c["excess_far_pooled"], "met": c["h1_material"]}
               for k, c in cells.items() if not c["case_mix"]}
    ns = agg["new_site"]
    h2 = {}
    for kk in ("k3", "k10"):
        if kk in ns:
            lo = ns[kk]["rmse_fixed_minus_k5"]["ci_family"][0]
            h2[kk] = {"mean_diff": ns[kk]["rmse_fixed_minus_k5"]["mean"], "ci_family": ns[kk]["rmse_fixed_minus_k5"]["ci_family"],
                      "met": bool(lo > 0)}
    h["H2"] = h2
    pk = f"tau{CONFIG['primary_cell']['tau']:.2f}_sw{CONFIG['primary_cell']['switch_fraction']:.2f}"
    c = cells[pk]
    rf = c["recovered_fraction"]["k5"]
    if rf is None:
        h["H3"] = {"met": None, "reason": "lab effect not material in the primary cell"}
    else:
        sens_ok = c["e2"]["k5"]["sens"] >= c["e2"]["oracle"]["sens"] - CONFIG["h3_sens_tolerance"]
        h["H3"] = {"recovered_fraction": rf, "sens_k5": c["e2"]["k5"]["sens"], "sens_oracle": c["e2"]["oracle"]["sens"],
                   "met": bool(rf["ci_family_lower"] >= CONFIG["h3_recovered_min"] and sens_ok)}
    lo_c, hi_c = CONFIG["h4_coverage"]
    h["H4"] = {k: {"coverage_k5": c["e1_coverage"]["k5"], "met": bool(c["e1_coverage"]["k5"] is not None and lo_c <= c["e1_coverage"]["k5"] <= hi_c)}
               for k, c in cells.items() if not c["case_mix"]}
    if "detector" in agg and "delta_0.20" in agg["detector"]:
        d = agg["detector"]["delta_0.20"]
        null_rate = agg["detector"]["delta_0.00"]["null_alarms_per_1000"]
        h["H5"] = {"power": d.get("power"), "median_delay_days": d.get("delay_days_median"),
                   "null_alarms_per_1000": null_rate,
                   "met": bool(d.get("power", 0) >= CONFIG["h5_power"]
                               and d.get("delay_days_median", 1e9) <= CONFIG["h5_median_delay_days"]
                               and null_rate <= CONFIG["h5_null_alarms_per_1000"])}
    # kill rule
    fixed_rf = c["recovered_fraction"].get("fixed")
    k5_rf = c["recovered_fraction"].get("k5")
    h3_failed = (h["H3"].get("met") is False)
    k5_beats_fixed = bool(fixed_rf and k5_rf and k5_rf["ci95"][0] > fixed_rf["ci95"][1])
    h2_any = any(v["met"] for v in h2.values()) if h2 else False
    h["kill_rule"] = {"h3_failed": h3_failed, "k5_beats_fixed_on_e2": k5_beats_fixed, "h2_met_any": h2_any,
                      "fires": bool(h3_failed or (not k5_beats_fixed and not h2_any))}
    return h


# ---------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------
def render_report(res: Dict[str, Any], det: Dict[str, float], elapsed: float) -> str:
    a = res["aggregate"]
    L: List[str] = []
    L.append("# EXP-K5-001 report (written by `run.py`; do not edit)\n")
    L.append("> **SYNTHETIC DATA ONLY.** Laboratory spreads: tau = 0.07 is anchored by E23 (a spread across laboratories in a Chinese EQA programme, not a bias estimate); tau = 0.15 and 0.30 are assumptions. Rule R (a 25 percent rise) is a study rule, not a clinical criterion. Pre-registration: `PREREG.md`.\n")
    L.append(f"Replications: {a['n_replications']} (frozen seeds). Detector calibration: sigma_r = {det['sigma_r']:.4f}, threshold h* = {det['h_star']:.2f} from {det['n_streams']} null streams ({det['n_residuals']} residuals). **Calibration target of {det['target_alarms_per_1000']:.2f} alarms per 1,000 residuals attained: {det['target_attained']}** (achieved {det['achieved_alarms_per_1000_at_h_star']:.2f} per 1,000 at h* = {det['h_star']:.2f}). Run time {elapsed:.0f} s.\n")
    L.append("Diagnostic added by Amendment 2 (alarm rate per 1,000 calibration residuals against threshold; not used to choose anything):\n")
    L.append("| threshold | all residuals | residuals of patients without recurrence only |\n|---|---|---|")
    for t, v in det["diagnostic_alarm_rate_vs_threshold"].items():
        L.append(f"| {t} | {v['all_per_1000']:.2f} | {v['non_recurrent_per_1000']:.2f} |")
    L.append("")
    L.append("## Hypotheses (computed)\n")
    h = a["hypotheses"]
    L.append("| Hypothesis | Result | Detail |\n|---|---|---|")
    for k, v in h["H1"].items():
        L.append(f"| H1 `{k}` | {'met' if v['met'] else 'NOT met'} | excess FAR of pooled over oracle = {v['excess_far_pooled']:.4f} (threshold 0.05) |")
    for k, v in h["H2"].items():
        L.append(f"| H2 `{k}` | {'met' if v['met'] else 'NOT met'} | RMSE(fixed) - RMSE(K5) = {v['mean_diff']:.4f}, Bonferroni interval [{v['ci_family'][0]:.4f}, {v['ci_family'][1]:.4f}] |")
    h3 = h["H3"]
    if h3.get("met") is None:
        L.append(f"| H3 | not evaluable | {h3['reason']} |")
    else:
        rf = h3["recovered_fraction"]
        L.append(f"| H3 | {'met' if h3['met'] else 'NOT met'} | recovered fraction {rf['estimate']:.3f}, 95% [{rf['ci95'][0]:.3f}, {rf['ci95'][1]:.3f}], Bonferroni lower {rf['ci_family_lower']:.3f}; Sens K5 {h3['sens_k5']:.3f} vs oracle {h3['sens_oracle']:.3f} |")
    for k, v in h["H4"].items():
        cv = v["coverage_k5"]
        L.append(f"| H4 `{k}` | {'met' if v['met'] else 'NOT met'} | K5 95% interval coverage {('%.3f' % cv) if cv is not None else 'n/a'} |")
    if "H5" in h:
        v = h["H5"]
        L.append(f"| H5 | {'met' if v['met'] else 'NOT met'} | power {v['power']}, median delay {v['median_delay_days']} days, null alarms per 1000 results {v['null_alarms_per_1000']:.3f} |")
    kr = h["kill_rule"]
    L.append(f"\n**Kill rule fires:** {kr['fires']} (H3 failed: {kr['h3_failed']}; K5 beats fixed on E2 with non-overlapping interval: {kr['k5_beats_fixed_on_e2']}; H2 met at k=3 or 10: {kr['h2_met_any']}).\n")

    L.append("## E1: contrast RMSE (log units, mean over replications; lower is better; oracle is 0 by definition)\n")
    L.append("| Cell | pooled | legacy | fixed | K5 | tau_hat mean (true tau) | coverage fixed | coverage K5 |\n|---|---|---|---|---|---|---|---|")
    for k, c in a["cells"].items():
        e = c["e1_rmse"]
        cf, ck = c["e1_coverage"]["fixed"], c["e1_coverage"]["k5"]
        L.append(f"| `{k}` | {e['pooled']:.4f} | {e['legacy']:.4f} | {e['fixed']:.4f} | {e['k5']:.4f} | {c['tau_hat_mean']:.3f} ({c['tau']:.2f}) | {('%.3f' % cf) if cf is not None else 'n/a'} | {('%.3f' % ck) if ck is not None else 'n/a'} |")
    c = a["control_loglinear"]
    L.append("\n## Control (Amendment 2): the K5 model is exactly true (log-linear patient trajectories on the simulator's visit schedule), cell tau 0.15, switching 0.30\n")
    L.append("| pooled | legacy | fixed | K5 | tau_hat mean (true 0.15) | coverage fixed | coverage K5 |\n|---|---|---|---|---|---|---|")
    e = c["e1_rmse"]
    L.append(f"| {e['pooled']:.4f} | {e['legacy']:.4f} | {e['fixed']:.4f} | {e['k5']:.4f} | {c['tau_hat_mean']:.3f} | {c['e1_coverage']['fixed']:.3f} | {c['e1_coverage']['k5']:.3f} |")
    L.append("\n## E2: rule R, false alarms (FAR) and sensitivity, mean over replications\n")
    L.append("| Cell | method | FAR | Sens | recovered fraction (95% CI) |\n|---|---|---|---|---|")
    for k, c in a["cells"].items():
        for m in ("pooled", "legacy", "fixed", "k5", "oracle"):
            e = c["e2"][m]
            rf = c["recovered_fraction"].get(m) if m in ("legacy", "fixed", "k5") else None
            rfs = f"{rf['estimate']:.3f} [{rf['ci95'][0]:.3f}, {rf['ci95'][1]:.3f}]" if rf else ("n/a (excess < 0.01)" if m in ("legacy", "fixed", "k5") else "")
            L.append(f"| `{k}` | {m} | {e['far']:.4f} | {e['sens']:.4f} | {rfs} |")
    L.append("\n## New sites (cell tau 0.15, switching 0.30): E1 contrast RMSE new laboratory vs network, and descriptive E2 on switchers to a new laboratory\n")
    L.append("| k switching patients per new lab | RMSE pooled | RMSE legacy | RMSE fixed | RMSE K5 | fixed - K5 (95% CI) | coverage fixed | coverage K5 | FAR pooled | FAR fixed | FAR K5 | FAR oracle |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for kk, ns in a["new_site"].items():
        e = ns["e1_rmse"]
        d = ns["rmse_fixed_minus_k5"]
        cf, ck = ns["e1_coverage"]["fixed"], ns["e1_coverage"]["k5"]
        f = ns["e2_descriptive"]
        L.append(f"| {kk[1:]} | {e['pooled']:.4f} | {e['legacy']:.4f} | {e['fixed']:.4f} | {e['k5']:.4f} | {d['mean']:.4f} [{d['ci95'][0]:.4f}, {d['ci95'][1]:.4f}] | {('%.3f' % cf) if cf is not None else 'n/a'} | {('%.3f' % ck) if ck is not None else 'n/a'} | {f['pooled']['far']:.4f} | {f['fixed']['far']:.4f} | {f['k5']['far']:.4f} | {f['oracle']['far']:.4f} |")
    if "detector" in a:
        L.append("\n## E3: laboratory-stream detector (shifted laboratory 2 from calendar day 365; tau 0.07, switching 0.30)\n")
        L.append("| delta | null alarms per 1000 results | power (within 180 d) | median delay (days) | IQR delay (days) | median delay (lab results) |\n|---|---|---|---|---|---|")
        for dk, d in a["detector"].items():
            L.append(f"| {dk[6:]} | {d['null_alarms_per_1000']:.3f} | {d.get('power', 'n/a') if 'power' in d else 'n/a'} | {d.get('delay_days_median', 'n/a')} | {d.get('delay_days_iqr', 'n/a')} | {d.get('delay_results_median', 'n/a')} |")
        L.append("\n## E4 (descriptive): shifted laboratory, delta 0.20, rule R among patients with a post-shift result there\n")
        L.append("| arm | FAR | Sens | FAR n/d | Sens n/d |\n|---|---|---|---|---|")
        for arm, v in a["e4_descriptive"].items():
            L.append(f"| {arm} | {v['far']} | {v['sens']} | {v['far_num']}/{v['far_den']} | {v['sens_num']}/{v['sens_den']} |")
    L.append("\n## Limits (carried from the pre-registration)\nSynthetic data; proportional laboratory bias only; offsets identified only through patients who change laboratory; no reference-material anchoring; one analyte; a single step change as the only temporal drift; rule R is a study rule.\n")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------
def run(kind: str, n_rep: int, det: Optional[Dict[str, float]], workers: int, smoke: bool = False) -> List[Dict[str, Any]]:
    jobs = [(kind, r, det or {}, smoke) for r in range(n_rep)]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(replication, jobs))
    return [replication(j) for j in jobs]


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dev", action="store_true")
    mode.add_argument("--frozen", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    t0 = time.time()
    if args.smoke:
        det = {"sigma_r": 0.2, "h_star": 6.0, "n_streams": 1, "n_residuals": 1, "target_alarms_per_1000": 0.67,
               "achieved_alarms_per_1000_at_h_star": 0.0, "target_attained": True,
               "diagnostic_alarm_rate_vs_threshold": {"2": {"all_per_1000": 1.0, "non_recurrent_per_1000": 1.0}}}
        reps = run("dev", 2, det, 1, smoke=True)
        agg = aggregate(reps, bootstrap_replicates=len(reps))
        report = render_report({"aggregate": agg}, det, 0.0)
        print(json.dumps({"ok": "H1" in report and "Control" in report, "cells": list(agg["cells"])}))
        return 0
    if args.dev:
        det = calibrate_detector(CONFIG["n_calibration"], kind="calibration")
        reps = run("dev", CONFIG["n_dev"], det, args.workers)
        agg = aggregate(reps)
        out = {"config": CONFIG, "kind": "development", "detector_calibration": det, "aggregate": agg}
        (OUT / "dev_results.json").write_text(json.dumps(out, indent=2))
        print(f"wrote dev_results.json in {time.time() - t0:.0f}s")
        return 0
    det = calibrate_detector(CONFIG["n_calibration"], kind="calibration")
    reps = run("frozen", CONFIG["n_frozen"], det, args.workers)
    agg = aggregate(reps)
    elapsed = time.time() - t0
    out = {"config": CONFIG, "kind": "frozen", "detector_calibration": det, "aggregate": agg,
           "replications": reps}
    (OUT / "results.json").write_text(json.dumps(out, indent=2))
    (OUT / "REPORT.md").write_text(render_report(out, det, elapsed))
    print(f"wrote results.json and REPORT.md in {elapsed:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
