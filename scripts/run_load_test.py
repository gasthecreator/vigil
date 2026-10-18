#!/usr/bin/env python3
"""scripts/run_load_test.py

Concurrent load test of the Vigil API over real HTTP (uvicorn subprocess + httpx client).
See scripts/http_load_harness.py for exactly what is and is not measured.

Budgets (Master Plan §9.5): p95 <= 200 ms, error rate <= 0.1 %.
Output (script-written only): reports/load/LOAD_TEST_HTTP_RESULTS.json and .md
(`--out-dir` redirects; tests always use a temporary directory).

The earlier in-process results (LOAD_TEST_RESULTS.*, TestClient, local profile, no network) are kept
untouched because the rc.1 hash manifest lists them; they are superseded by these files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import http_load_harness as h  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NAME = "LOAD_TEST_HTTP_RESULTS"


def run_load_test(total_requests: int = 2000, concurrency: int = 10) -> dict:
    return h.run(concurrency=concurrency, max_requests=total_requests, label="load")


def write_reports(results: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {k: v for k, v in results.items() if k != "_records"}
    jp, mp = out_dir / f"{NAME}.json", out_dir / f"{NAME}.md"
    jp.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    ov, b, hst = res["overall_latency"], res["budgets"], res["host"]
    lines = [
        "# Vigil API load test (real HTTP)", "",
        "> Written by `scripts/run_load_test.py`. Do not edit by hand.", "",
        f"- Date (UTC): {res['timestamp_utc']}",
        f"- Transport: **{res['transport']}** to a separate `uvicorn` process (1 worker), staging profile with authentication, SQLite file database, no TLS",
        f"- Host: {hst['platform']}, {hst['cpu_count']} CPUs, Python {hst['python']}",
        f"- Workload: {res['total_requests']} requests, concurrency {res['concurrency']}, {res['duration_seconds']} s, {res['throughput_req_per_sec']} req/s; "
        "mix = reads of patients/triage/continuity plus POSTs through the lab-ingestion pipeline (audit chain, M3/K2/M5)",
        "", "## Budgets", "", "| Metric | Measured | Budget | Verdict |", "|---|---|---|---|",
        f"| p95 latency (all requests) | {b['p95_latency_ms']['measured']} ms | <= {b['p95_latency_ms']['budget']} ms | {b['p95_latency_ms']['status']} |",
        f"| error rate | {b['error_rate_percent']['measured']} % | <= {b['error_rate_percent']['budget']} % | {b['error_rate_percent']['status']} |",
        "", f"Latency: p50 {ov.get('p50_ms')} ms, p90 {ov.get('p90_ms')} ms, p95 {ov.get('p95_ms')} ms, p99 {ov.get('p99_ms')} ms, max {ov.get('max_ms')} ms.", "",
        "## Per endpoint", "", "| Endpoint | n | p50 | p95 | p99 | status codes |", "|---|---|---|---|---|---|",
    ]
    for ep, d in res["endpoints"].items():
        lines.append(f"| `{ep}` | {d['count']} | {d['p50_ms']} | {d['p95_ms']} | {d['p99_ms']} | {d['status_codes']} |")
    lines += ["", "## Limits of this measurement", "",
              "One host runs both client and server, so client and server compete for CPU; one uvicorn worker; SQLite; no TLS or reverse proxy; synthetic data; "
              "10 patients. It says nothing about hospital hardware, PostgreSQL, WAN latency or multi-worker behaviour.", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--requests", type=int, default=2000)
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "reports" / "load")
    a = ap.parse_args()
    res = run_load_test(a.requests, a.concurrency)
    jp, _ = write_reports(res, a.out_dir)
    print(f"wrote {jp}")
    ok = all(v["status"] == "PASS" for v in res["budgets"].values())
    print("budgets:", {k: (v["measured"], v["status"]) for k, v in res["budgets"].items()})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
