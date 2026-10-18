#!/usr/bin/env python3
"""EXP-M7-001: CP-SAT research track (P15-B). Pre-registration: experiments/EXP-M7-001/PREREG.md

Modes
-----
dev      Attempts A1/A2/A3 on the development seeds / cells only. Writes
         experiments/EXP-M7-001/dev_results.json (all attempts, selected attempt chosen BY THIS
         SCRIPT with the pre-registered rule).
frozen   One run of the selected attempt on the frozen seeds, 12 cells x 50 reps, paired with the
         urgency heuristic, FCFS and the greedy proxy. Writes results.json and REPORT.md.
verify   Re-runs the first N replications of one cell and compares with results.json (CI check).

Every number in results.json / REPORT.md is written by this script. Nothing is typed.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "vigil-ml"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_study_m7_twin import (  # noqa: E402
    generate_replication_stream,
    paired_bootstrap_ci,
    simulate_policy_run,
)
from vigil_ml.continuity import ContinuityHarmModel  # noqa: E402
from vigil_ml.scheduler import RadiotherapyScheduler  # noqa: E402
from vigil_ml.scheduler_research import ATTEMPTS, ResearchRadiotherapyScheduler  # noqa: E402

EXP_DIR = ROOT / "experiments" / "EXP-M7-001"
DEV_JSON = EXP_DIR / "dev_results.json"  # persistence visibility: used for selection
DEV_ORACLE_JSON = EXP_DIR / "dev_results_oracle_visibility.json"  # evidence of the leak; NOT used for selection
RESULTS_JSON = EXP_DIR / "results.json"
REPORT_MD = EXP_DIR / "REPORT.md"
M7TWIN_JSON = ROOT / "reports" / "ml" / "STUDY_M7_DIGITAL_TWIN.json"

DEV_SEED_BASE, DEV_REPS = 1000, 20
DEV_CELLS: List[Tuple[float, float]] = [(2.5, 7.0), (3.5, 7.0)]  # reality: allow(R1) pre-registered dev cells
FROZEN_SEED_BASE, FROZEN_REPS = 20261017, 50
LAMBDAS = [2.0, 2.5, 3.0, 3.5]  # reality: allow(R1) pre-registered grid
MTTRS = [3.0, 7.0, 14.0]  # reality: allow(R1) pre-registered grid
ARMS = ("CPSAT_V2", "UrgencyHeuristic", "FCFS", "HarmAwareProxy")
METRICS = ("mean_harm", "wait_harm", "interruption_harm", "unscheduled_harm", "mean_wait", "disparity")


def _cell_key(lam: float, mttr: float) -> str:
    return f"lambda_{lam}_mttr_{int(mttr)}"


def _run_rep(args: Tuple[str, int, int, float, float, str]) -> Dict[str, Any]:
    attempt, seed_base, rep, lam, mttr, visibility = args
    rng = np.random.default_rng(seed_base + rep * 100)
    harm_model = ContinuityHarmModel()
    research = ResearchRadiotherapyScheduler(harm_model, ATTEMPTS[attempt])
    shared = RadiotherapyScheduler(harm_model=harm_model)
    pts, cap = generate_replication_stream(
        rng, horizon_days=60, arrival_rate=lam, linac_capacity=16, num_linacs=2, mtbf_days=21.0, mttr_days=mttr
    )
    out: Dict[str, Any] = {"rep": rep}
    # the sim's "CPSAT" policy calls scheduler.solve; here it is the research scheduler
    out["CPSAT_V2"] = simulate_policy_run(
        "CPSAT",
        pts,
        cap,
        harm_model,
        research,
        cpsat_window=ATTEMPTS[attempt].window_days,
        downtime_visibility=visibility,
    )
    for arm in ("UrgencyHeuristic", "FCFS", "HarmAwareProxy"):
        out[arm] = simulate_policy_run(arm, pts, cap, harm_model, shared)
    return out


def _run_cell(
    attempt: str, seed_base: int, reps: int, lam: float, mttr: float, visibility: str = "persistence"
) -> List[Dict[str, Any]]:
    args = [(attempt, seed_base, r, lam, mttr, visibility) for r in range(reps)]
    with mp.Pool(processes=min(8, mp.cpu_count())) as pool:
        return pool.map(_run_rep, args, chunksize=1)


def _arm_means(cell: List[Dict[str, Any]]) -> Dict[str, float]:
    return {arm: float(np.mean([r[arm]["mean_harm"] for r in cell])) for arm in ARMS}


def _status_totals(cell: List[Dict[str, Any]]) -> Dict[str, int]:
    tot: Dict[str, int] = {}
    for r in cell:
        for k, v in r["CPSAT_V2"]["status_counts"].items():
            tot[k] = tot.get(k, 0) + v
    return tot


def _slim(cell: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-replication values kept in the result file (needed for paired CIs and CI re-checks)."""
    slim = []
    for r in cell:
        row: Dict[str, Any] = {"rep": r["rep"]}
        for arm in ARMS:
            row[arm] = {m: r[arm][m] for m in METRICS}
        row["CPSAT_V2"]["status_counts"] = r["CPSAT_V2"]["status_counts"]
        row["CPSAT_V2"]["mean_solver_objective"] = r["CPSAT_V2"]["mean_solver_objective"]
        slim.append(row)
    return slim


# --------------------------------------------------------------------------------------
def mode_dev(visibility: str) -> None:
    t0 = time.perf_counter()
    results: Dict[str, Any] = {
        "preregistration": "experiments/EXP-M7-001/PREREG.md",
        "downtime_visibility": visibility,
        "seed_base": DEV_SEED_BASE,
        "reps": DEV_REPS,
        "attempts": {},
    }
    for attempt in ("A1", "A2", "A3"):
        per_cell: Dict[str, Any] = {}
        for lam, mttr in DEV_CELLS:
            cell = _run_cell(attempt, DEV_SEED_BASE, DEV_REPS, lam, mttr, visibility)
            m = _arm_means(cell)
            st = _status_totals(cell)
            per_cell[_cell_key(lam, mttr)] = {
                "mean_harm": m,
                "status_counts": st,
                "per_rep_harm_research_vs_urgency": [
                    [r["CPSAT_V2"]["mean_harm"], r["UrgencyHeuristic"]["mean_harm"]] for r in cell
                ],
            }
            print(f"[dev] {attempt} {_cell_key(lam, mttr)} {m} {st}", flush=True)
        mean_dev = float(np.mean([v["mean_harm"]["CPSAT_V2"] for v in per_cell.values()]))
        results["attempts"][attempt] = {
            "cells": per_cell,
            "mean_dev_harm": mean_dev,
            "window_days": ATTEMPTS[attempt].window_days,
        }
    order = ["A1", "A2", "A3"]  # listed by increasing window: ties -> smaller window
    best = min(order, key=lambda a: (round(results["attempts"][a]["mean_dev_harm"], 12), order.index(a)))
    results["selected_attempt"] = best
    results["selection_rule"] = "lowest mean harm over the two development cells; ties -> smaller window (PREREG section 4)"
    results["wall_time_seconds"] = round(time.perf_counter() - t0, 1)
    target = DEV_JSON if visibility == "persistence" else DEV_ORACLE_JSON
    if visibility != "persistence":
        results["note"] = "oracle visibility = scheduler sees future breakdowns; evidence of the leak, not used for selection"
    target.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[{visibility}] attempt chosen by the rule: {best}. Wrote {target}")


# --------------------------------------------------------------------------------------
def _consistency_vs_committed(cell_key: str, means: Dict[str, float]) -> Dict[str, float]:
    """Urgency/FCFS/proxy are recomputed here and must equal the committed M7-TWIN cell means."""
    committed = json.loads(M7TWIN_JSON.read_text())["sweep_grid"][cell_key]["mean_harm"]
    pairs = {
        "UrgencyHeuristic": committed["urgency_heuristic"],
        "FCFS": committed["fcfs"],
        "HarmAwareProxy": committed["greedy_proxy"],
    }
    diffs = {k: abs(round(means[k], 5) - v) for k, v in pairs.items()}
    bad = {k: d for k, d in diffs.items() if d > 1e-5}
    if bad:
        raise SystemExit(f"Baseline arms differ from committed M7-TWIN results in {cell_key}: {bad}")
    return diffs


def mode_frozen() -> None:
    t0 = time.perf_counter()
    if not DEV_JSON.exists():
        raise SystemExit("dev_results.json missing: run --mode dev first (PREREG section 4).")
    selected = json.loads(DEV_JSON.read_text())["selected_attempt"]
    print(f"[frozen] selected attempt from dev_results.json: {selected}", flush=True)
    out: Dict[str, Any] = {
        "preregistration": "experiments/EXP-M7-001/PREREG.md",
        "synthetic": True,
        "downtime_visibility": "persistence",
        "selected_attempt": selected,
        "seed_base": FROZEN_SEED_BASE,
        "reps": FROZEN_REPS,
        "cells": {},
    }
    for lam in LAMBDAS:
        for mttr in MTTRS:
            key = _cell_key(lam, mttr)
            cell = _run_cell(selected, FROZEN_SEED_BASE, FROZEN_REPS, lam, mttr)
            means = _arm_means(cell)
            cons = _consistency_vs_committed(key, means)
            h = {arm: np.array([r[arm]["mean_harm"] for r in cell]) for arm in ARMS}
            cis = {
                "urgency_minus_research": paired_bootstrap_ci(h["UrgencyHeuristic"] - h["CPSAT_V2"]),
                "fcfs_minus_research": paired_bootstrap_ci(h["FCFS"] - h["CPSAT_V2"]),
                "proxy_minus_research": paired_bootstrap_ci(h["HarmAwareProxy"] - h["CPSAT_V2"]),
            }
            wins_urg = cis["urgency_minus_research"][1] > 0.0
            wins_fcfs = cis["fcfs_minus_research"][1] > 0.0
            objs = [r["CPSAT_V2"]["mean_solver_objective"] for r in cell if r["CPSAT_V2"]["mean_solver_objective"] is not None]
            ch = [r["CPSAT_V2"]["mean_harm"] for r in cell if r["CPSAT_V2"]["mean_solver_objective"] is not None]
            corr = float(np.corrcoef(objs, ch)[0, 1]) if len(objs) > 4 and np.std(objs) > 0 and np.std(ch) > 0 else None
            out["cells"][key] = {
                "arrival_rate": lam,
                "mttr_days": mttr,
                "mean_harm": {k: round(v, 5) for k, v in means.items()},
                "paired_bootstrap_ci_95": {k: list(v) for k, v in cis.items()},  # [mean, low, high]
                "beats_urgency_ci_lower_gt_0": bool(wins_urg),
                "beats_fcfs_ci_lower_gt_0": bool(wins_fcfs),
                "harm_decomposition_research": {
                    m: round(float(np.mean([r["CPSAT_V2"][m] for r in cell])), 5)
                    for m in ("wait_harm", "interruption_harm", "unscheduled_harm")
                },
                "harm_decomposition_urgency": {
                    m: round(float(np.mean([r["UrgencyHeuristic"][m] for r in cell])), 5)
                    for m in ("wait_harm", "interruption_harm", "unscheduled_harm")
                },
                "solver_status_counts": _status_totals(cell),
                "objective_vs_realised_harm_correlation": None if corr is None else round(corr, 4),
                "baseline_consistency_abs_diff_vs_committed_m7twin": cons,
                "per_rep": _slim(cell),
            }
            print(f"[frozen] {key} {out['cells'][key]['mean_harm']} beats_urg={wins_urg} beats_fcfs={wins_fcfs}", flush=True)
    all_ok = all(c["beats_urgency_ci_lower_gt_0"] and c["beats_fcfs_ci_lower_gt_0"] for c in out["cells"].values())
    out["promotion"] = {
        "criterion": "CI lower bound > 0 for (urgency - research) AND (fcfs - research) in all 12 cells",
        "cells_beating_urgency": sum(c["beats_urgency_ci_lower_gt_0"] for c in out["cells"].values()),
        "cells_beating_fcfs": sum(c["beats_fcfs_ci_lower_gt_0"] for c in out["cells"].values()),
        "promoted": bool(all_ok),
        "verdict": "PROMOTION CRITERION MET" if all_ok else "NOT PROMOTED (eliminated by protocol; CP-SAT stays a badged research module)",
    }
    out["wall_time_seconds"] = round(time.perf_counter() - t0, 1)
    RESULTS_JSON.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_report(out, json.loads(DEV_JSON.read_text())), encoding="utf-8")
    print(f"{out['promotion']['verdict']}. Wrote {RESULTS_JSON} and {REPORT_MD}")


def render_report(res: Dict[str, Any], dev: Dict[str, Any]) -> str:
    L: List[str] = []
    L.append("# EXP-M7-001 report: CP-SAT research track (SYNTHETIC)\n")
    L.append(
        "*Generated by `scripts/run_study_m7_cpsat_v2.py --mode frozen`; every number below is read from "
        "`results.json` / `dev_results.json`. Synthetic simulator only; no real-patient evidence.*\n"
    )
    p = res["promotion"]
    L.append(
        f"**Verdict (computed against PREREG section 5): {p['verdict']}** (beats urgency in "
        f"{p['cells_beating_urgency']}/12 cells, beats FCFS in {p['cells_beating_fcfs']}/12 cells; the criterion needs 12/12 for both).\n"
    )
    first = next(iter(dev["attempts"].values()))
    L.append("## Development phase (development seeds only)\n")
    L.append("| attempt | window (d) | mean dev harm (research) | " + " | ".join(f"urgency {k}" for k in first["cells"]) + " |")
    L.append("|---|---|---|" + "---|" * len(first["cells"]))
    for a, v in dev["attempts"].items():
        urg = " | ".join(f"{c['mean_harm']['UrgencyHeuristic']:.5f}" for c in v["cells"].values())
        L.append(f"| {a} | {v['window_days']} | {v['mean_dev_harm']:.5f} | {urg} |")
    L.append(f"\nSelected by the pre-registered rule: **{res['selected_attempt']}** (`{dev['selection_rule']}`).\n")
    L.append("## Frozen evaluation (50 replications per cell, seeds 20261017 + 100 r)\n")
    L.append(
        "Harm = mean cumulative harm per evaluated patient (harm-model units); lower is better. "
        "CI = paired bootstrap 95% of (baseline - research); positive = research better. "
        "The greedy proxy column is secondary and not part of the promotion rule.\n"
    )
    L.append("| cell | proxy | urgency | FCFS | research | delta vs urgency [CI] | delta vs FCFS [CI] | beats urgency | beats FCFS |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for k, c in res["cells"].items():
        m = c["mean_harm"]
        u = c["paired_bootstrap_ci_95"]["urgency_minus_research"]
        f = c["paired_bootstrap_ci_95"]["fcfs_minus_research"]
        L.append(
            f"| {k} | {m['HarmAwareProxy']:.5f} | {m['UrgencyHeuristic']:.5f} | {m['FCFS']:.5f} | {m['CPSAT_V2']:.5f} | "
            f"{u[0]:+.5f} [{u[1]:+.5f}, {u[2]:+.5f}] | {f[0]:+.5f} [{f[1]:+.5f}, {f[2]:+.5f}] | "
            f"{'yes' if c['beats_urgency_ci_lower_gt_0'] else 'no'} | {'yes' if c['beats_fcfs_ci_lower_gt_0'] else 'no'} |"
        )
    L.append("\n## Solver diagnostics per cell\n")
    L.append("| cell | status counts | corr(objective, realised harm) | research wait / interruption / unscheduled | urgency wait / interruption / unscheduled |")
    L.append("|---|---|---|---|---|")
    for k, c in res["cells"].items():
        r, u = c["harm_decomposition_research"], c["harm_decomposition_urgency"]
        L.append(
            f"| {k} | {c['solver_status_counts']} | {c['objective_vs_realised_harm_correlation']} | "
            f"{r['wait_harm']:.5f} / {r['interruption_harm']:.5f} / {r['unscheduled_harm']:.5f} | "
            f"{u['wait_harm']:.5f} / {u['interruption_harm']:.5f} / {u['unscheduled_harm']:.5f} |"
        )
    L.append(
        "\nBaseline arms were recomputed in this run and match the committed M7-TWIN cell means within 1e-5 "
        "(the script aborts otherwise)."
    )
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------------------
def mode_verify(n_reps: int) -> int:
    """CI check: re-run the first n replications of cell (2.5, 7) and compare to results.json."""
    res = json.loads(RESULTS_JSON.read_text())
    key = _cell_key(2.5, 7.0)
    cell = _run_cell(res["selected_attempt"], FROZEN_SEED_BASE, n_reps, 2.5, 7.0)
    stored = {r["rep"]: r for r in res["cells"][key]["per_rep"]}
    bad = []
    for r in cell:
        for arm in ARMS:
            for m in METRICS:
                a, b = r[arm][m], stored[r["rep"]][arm][m]
                if abs(a - b) > 1e-9:
                    bad.append((r["rep"], arm, m, a, b))
    if bad:
        print(f"MISMATCH ({len(bad)}): {bad[:5]}")
        return 1
    print(f"OK: first {n_reps} replications of {key} reproduce results.json exactly.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("dev", "frozen", "verify"), required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--visibility", choices=("persistence", "oracle"), default="persistence")
    a = ap.parse_args()
    if a.mode == "dev":
        mode_dev(a.visibility)
    elif a.mode == "frozen":
        mode_frozen()
    else:
        return mode_verify(a.reps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
