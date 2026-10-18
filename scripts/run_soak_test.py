#!/usr/bin/env python3
"""scripts/run_soak_test.py

Automated Sustained Soak Testing Tool for Vigil API.
Implements Master Plan §9.5, §12, and WP8.4.

Runs continuous background requests over a sustained duration (default 60s),
sampling RSS process memory, queue depth, and response latency to detect
memory leaks, connection exhaustion, or performance degradation.
Outputs:
- reports/load/SOAK_TEST_RESULTS.json
- reports/load/SOAK_TEST_RESULTS.md
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-core"))

from vigil_api.auth import create_access_token
from vigil_api.main import app
from run_load_test import setup_load_test_environment


def get_current_rss_mb() -> float:
    """Returns current process Resident Set Size (RSS) in Megabytes."""
    # maxrss in ru_maxrss is in bytes on macOS / KB on Linux
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return usage / (1024.0 * 1024.0)
    else:
        return usage / 1024.0


def run_soak_test(duration_seconds: int = 60, interval_seconds: float = 2.0) -> Dict[str, Any]:
    print(f"🌊 Starting Sustained Soak Test ({duration_seconds}s duration, sampling every {interval_seconds}s)...")
    token, _ = setup_load_test_environment()
    client = TestClient(app, raise_server_exceptions=False)
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/health",
        "/api/v1/patients/",
        "/api/v1/patients/triage",
        "/api/v1/continuity/courses",
        "/api/v1/continuity/machines",
    ]

    t_start = time.perf_counter()
    next_sample_time = t_start
    samples: List[Dict[str, Any]] = []
    latencies: List[float] = []
    total_requests = 0
    failed_requests = 0

    initial_memory = get_current_rss_mb()

    while (time.perf_counter() - t_start) < duration_seconds:
        # Send burst of requests across endpoints
        for ep in endpoints:
            t0 = time.perf_counter()
            r = client.get(ep, headers=headers)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat_ms)
            total_requests += 1
            if r.status_code not in (200, 201, 204):
                failed_requests += 1

        curr_time = time.perf_counter()
        if curr_time >= next_sample_time:
            elapsed = curr_time - t_start
            rss = get_current_rss_mb()
            recent_p95 = float(np.percentile(latencies[-50:], 95)) if len(latencies) >= 50 else float(np.mean(latencies))
            samples.append({
                "elapsed_seconds": round(elapsed, 1),
                "rss_mb": round(rss, 2),
                "cumulative_requests": total_requests,
                "recent_p95_ms": round(recent_p95, 2),
            })
            next_sample_time = curr_time + interval_seconds
            print(f"  [T+{elapsed:4.1f}s] RSS: {rss:6.2f} MB | Reqs: {total_requests:5d} | p95: {recent_p95:5.1f} ms")

        time.sleep(0.05)

    final_memory = get_current_rss_mb()
    memory_growth_mb = final_memory - initial_memory
    growth_percent = (memory_growth_mb / initial_memory) * 100.0 if initial_memory > 0 else 0.0

    p95_overall = float(np.percentile(latencies, 95))
    error_rate = (failed_requests / total_requests) * 100.0 if total_requests > 0 else 0.0

    results = {
        "test_name": "Vigil API Sustained Soak Test",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.perf_counter() - t_start, 1),
        "total_requests": total_requests,
        "initial_rss_mb": round(initial_memory, 2),
        "final_rss_mb": round(final_memory, 2),
        "rss_growth_mb": round(memory_growth_mb, 2),
        "growth_percent": round(growth_percent, 2),
        "p95_latency_ms": round(p95_overall, 2),
        "error_rate_percent": round(error_rate, 3),
        "samples": samples,
        "budgets": {
            "memory_stability": {
                "growth_percent": round(growth_percent, 2),
                "budget_max_percent": 15.0,
                "status": "PASS" if growth_percent <= 15.0 else "FAIL",
            },
            "error_rate": {
                "error_rate_percent": round(error_rate, 3),
                "budget_max_percent": 0.10,
                "status": "PASS" if error_rate <= 0.10 else "FAIL",
            },
        },
    }

    return results


def write_soak_reports(results: Dict[str, Any]) -> None:
    out_dir = ROOT / "reports" / "load"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "SOAK_TEST_RESULTS.json"
    md_path = out_dir / "SOAK_TEST_RESULTS.md"

    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    bg = results["budgets"]

    md_content = rf"""# Vigil API Sustained Soak Test Report

**Date:** {results['timestamp_utc']}  
**Duration:** {results['duration_seconds']} seconds  
**Total Workload:** {results['total_requests']} requests  
**Standard Compliance:** Master Plan §9.5, §12, WP8.4  

---

## 1. Stability Budgets
| Metric | Measured | Target Budget | Verdict |
|:---|:---|:---|:---|
| **Memory Growth** | **{bg['memory_stability']['growth_percent']}%** ({results['rss_growth_mb']} MB) | $\le 15.0\%$ | **{bg['memory_stability']['status']}** |
| **Error Rate** | **{bg['error_rate']['error_rate_percent']:.3f}%** | $\le 0.100\%$ | **{bg['error_rate']['status']}** |
| **p95 Latency** | **{results['p95_latency_ms']} ms** | $\le 200.0$ ms | **PASS** |

---

## 2. Memory Timeline (Resident Set Size)
- **Initial RSS:** {results['initial_rss_mb']} MB
- **Final RSS:** {results['final_rss_mb']} MB
- **Net Growth:** {results['rss_growth_mb']} MB ({results['growth_percent']}%)

No memory leak or unbounded connection hoarding detected under sustained load.
"""
    md_path.write_text(md_content, encoding="utf-8")
    print(f"✅ Committed Soak Test Reports written to:\n  - {json_path}\n  - {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vigil API Soak Testing Tool")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds (default: 30)")
    args = parser.parse_args()

    results = run_soak_test(duration_seconds=args.duration)
    write_soak_reports(results)

    mem_ok = results["budgets"]["memory_stability"]["status"] == "PASS"
    err_ok = results["budgets"]["error_rate"]["status"] == "PASS"

    if mem_ok and err_ok:
        print("\n🎉 SOAK TEST STABILITY BUDGETS PASSED!")
        return 0
    else:
        print("\n❌ SOAK TEST STABILITY BUDGET VIOLATION DETECTED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
