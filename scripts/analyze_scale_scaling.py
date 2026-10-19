#!/usr/bin/env python3
"""Fit how the triage/timeline p95 grow with cohort size and extrapolate to the plan size (MASTER_PLAN 9.5).

Reads reports/perf/scale_runs/size_*.json (written by scripts/run_scale_test_postgres.py, one per size) and writes
reports/perf/SCALE_SCALING.json. Never hand-edit that file. A budget is reported as met at plan size only if the
*measured* run reached plan size; otherwise the verdict is the extrapolation, labelled as such.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "reports" / "perf" / "scale_runs"
OUT = ROOT / "reports" / "perf" / "SCALE_SCALING.json"
PLAN_PATIENTS = 100_000
BUDGETS = {"triage_p95_ms": 400.0, "timeline_p95_ms": 600.0}


def _fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return my - slope * mx, slope


def main() -> int:
    runs = sorted(
        (json.loads(p.read_text()) for p in RUNS.glob("size_*.json")),
        key=lambda r: r["run"]["n_patients"],
    )
    if len(runs) < 2:
        raise SystemExit("need runs at >= 2 cohort sizes in reports/perf/scale_runs/")
    xs = [float(r["run"]["n_patients"]) for r in runs]
    out: dict = {
        "study": "SCALE_SCALING",
        "plan_patients": PLAN_PATIENTS,
        "sizes_measured": [int(x) for x in xs],
        "obs_per_patient": sorted({r["run"]["obs_per_patient"] for r in runs}),
        "metrics": {},
    }
    all_ok = True
    for key, budget in BUDGETS.items():
        ys = [float(r["metrics"][key]) for r in runs]
        intercept, slope = _fit(xs, ys)
        at_plan = intercept + slope * PLAN_PATIENTS
        reached = max(xs) >= PLAN_PATIENTS
        ok = (ys[-1] <= budget) if reached else (at_plan <= budget)
        all_ok &= ok
        out["metrics"][key] = {
            "measured_p95_ms": dict(zip([int(x) for x in xs], [round(y, 1) for y in ys])),
            "slope_ms_per_patient": slope,
            "extrapolated_at_plan_size_ms": round(at_plan, 1),
            "budget_ms": budget,
            "basis": "measured" if reached else "linear extrapolation (plan size not run)",
            "meets_budget_at_plan_size": bool(ok),
            "patients_within_budget_linear_estimate": (
                int((budget - intercept) / slope) if slope > 0 else None
            ),
        }
    out["verdict"] = (
        "MET at plan size" if all_ok else "NOT MET at plan size (see metrics; fix or file a proposal, do not reword the budget)"
    )
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out["metrics"], indent=1))
    print(out["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
