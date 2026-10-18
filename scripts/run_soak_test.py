#!/usr/bin/env python3
"""scripts/run_soak_test.py

Sustained soak of the Vigil API over real HTTP (uvicorn subprocess + httpx client).

Measured
  * wall-clock duration actually run, request count, error rate, overall p95;
  * latency drift: p95 of the first vs. last quarter of the run (after warm-up);
  * server memory: *current* RSS of the uvicorn process sampled with `ps` every `--interval` seconds
    (not peak RSS, which can only grow), growth = median of the last quarter vs. median of the first
    quarter after warm-up.

Budgets (fixed here, before any result): error rate <= 0.1 %, overall p95 <= 200 ms,
p95 drift <= 50 %, RSS growth <= 15 %. Warm-up = first 10 % of the run (at least 30 s when the run is long enough).

Output (script-written only): reports/load/SOAK_TEST_HTTP_RESULTS.json and .md.
Default duration is 1800 s (30 min); the scheduled workflow uses the same default.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import http_load_harness as h  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NAME = "SOAK_TEST_HTTP_RESULTS"
SOAK_BUDGETS = {"p95_latency_ms": 200.0, "error_rate_percent": 0.1, "p95_drift_percent": 50.0, "rss_growth_percent": 15.0}


def analyse(res: dict) -> dict:
    rec = res.pop("_records")
    wall = res["duration_seconds"]
    t0 = min(r[0] for r in rec) if rec else 0.0
    warm = min(max(0.1 * wall, 30.0), 0.5 * wall)
    post = [r for r in rec if (r[0] - t0) >= warm]
    span = wall - warm
    q1 = [r[3] for r in post if (r[0] - t0) < warm + span / 4]
    q4 = [r[3] for r in post if (r[0] - t0) >= warm + 3 * span / 4]
    p95 = lambda x: float(np.percentile(x, 95)) if x else float("nan")  # noqa: E731
    drift = 100.0 * (p95(q4) - p95(q1)) / p95(q1) if q1 and q4 else float("nan")
    samples = [s for s in res["server_rss_mb"]["samples"] if s["rss_mb"] is not None and s["elapsed_s"] >= warm]
    m = len(samples)
    first = [s["rss_mb"] for s in samples[: max(m // 4, 1)]]
    last = [s["rss_mb"] for s in samples[-max(m // 4, 1):]]
    growth = 100.0 * (statistics.median(last) - statistics.median(first)) / statistics.median(first) if m >= 4 else float("nan")
    res["soak"] = {
        "warmup_seconds": round(warm, 1),
        "p95_first_quarter_ms": round(p95(q1), 2), "p95_last_quarter_ms": round(p95(q4), 2), "p95_drift_percent": round(drift, 2),
        "rss_median_first_quarter_mb": statistics.median(first) if first else None,
        "rss_median_last_quarter_mb": statistics.median(last) if last else None,
        "rss_growth_percent": round(growth, 2),
        "rss_samples_used": m,
        "budgets": SOAK_BUDGETS,
    }
    ok = lambda v, lim: (v == v) and v <= lim  # noqa: E731  (NaN -> False)
    res["soak"]["verdicts"] = {
        "p95_latency_ms": "PASS" if ok(res["overall_latency"].get("p95_ms", 1e9), SOAK_BUDGETS["p95_latency_ms"]) else "FAIL",
        "error_rate_percent": "PASS" if ok(res["error_rate_percent"], SOAK_BUDGETS["error_rate_percent"]) else "FAIL",
        "p95_drift_percent": "PASS" if ok(drift, SOAK_BUDGETS["p95_drift_percent"]) else "FAIL/UNMEASURABLE",
        "rss_growth_percent": "PASS" if ok(growth, SOAK_BUDGETS["rss_growth_percent"]) else "FAIL/UNMEASURABLE",
    }
    return res


def run_soak_test(duration_seconds: float = 1800.0, concurrency: int = 8, interval_seconds: float = 10.0, n_patients: int = 200) -> dict:
    return analyse(h.run(concurrency=concurrency, duration_seconds=duration_seconds, sample_interval=interval_seconds, label="soak", n_patients=n_patients))


def write_reports(res: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jp, mp = out_dir / f"{NAME}.json", out_dir / f"{NAME}.md"
    jp.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    s, hst, ov = res["soak"], res["host"], res["overall_latency"]
    lines = [
        "# Vigil API soak test (real HTTP)", "", "> Written by `scripts/run_soak_test.py`. Do not edit by hand.", "",
        f"- Date (UTC): {res['timestamp_utc']}",
        f"- Duration actually run: **{res['duration_seconds']} s** (requested {res['requested']['duration_seconds']} s), concurrency {res['concurrency']}, {res['patients']} patients, {res['total_requests']} requests ({res['throughput_req_per_sec']} req/s)",
        f"- Transport: **{res['transport']}** to a separate `uvicorn` process (1 worker), staging profile, SQLite file, no TLS",
        f"- Host: {hst['platform']}, {hst['cpu_count']} CPUs, Python {hst['python']}",
        "", "## Verdicts against budgets fixed before the run", "", "| Metric | Measured | Budget | Verdict |", "|---|---|---|---|",
        f"| overall p95 | {ov.get('p95_ms')} ms | <= {s['budgets']['p95_latency_ms']} | {s['verdicts']['p95_latency_ms']} |",
        f"| error rate | {res['error_rate_percent']} % | <= {s['budgets']['error_rate_percent']} | {s['verdicts']['error_rate_percent']} |",
        f"| p95 drift (last vs first quarter after warm-up) | {s['p95_first_quarter_ms']} -> {s['p95_last_quarter_ms']} ms = {s['p95_drift_percent']} % | <= {s['budgets']['p95_drift_percent']} % | {s['verdicts']['p95_drift_percent']} |",
        f"| server RSS growth (median last vs first quarter after warm-up, {s['rss_samples_used']} samples) | {s['rss_median_first_quarter_mb']} -> {s['rss_median_last_quarter_mb']} MB = {s['rss_growth_percent']} % | <= {s['budgets']['rss_growth_percent']} % | {s['verdicts']['rss_growth_percent']} |",
        "", "RSS is the current resident set of the server process sampled with `ps`; it is not peak RSS.", "",
        "## Limits", "", "One host runs client and server; one worker; SQLite; no TLS; synthetic data growing a single SQLite file and audit chain for the whole run. "
        "A pass is not evidence about hospital hardware or PostgreSQL. Memory 'stability' means growth under the stated threshold over this window, not absence of leaks.", "",
    ]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--duration", type=float, default=1800.0, help="seconds (default 1800 = 30 min)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--patients", type=int, default=200, help="synthetic patients provisioned (default 200; run 1 used 10, see reports/load/README.md)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "reports" / "load")
    a = ap.parse_args()
    res = run_soak_test(a.duration, a.concurrency, a.interval, a.patients)
    jp, _ = write_reports(res, a.out_dir)
    print(f"wrote {jp}")
    print(res["soak"]["verdicts"])
    return 0 if all(v == "PASS" for v in res["soak"]["verdicts"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
