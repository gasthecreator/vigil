"""tests/resilience/test_load_and_soak.py

Automated Load & Soak Verification Suite.
Enforces Master Plan §9.5 (Performance Budgets), §12, and WP8.4.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_load_test import run_load_test, write_reports
from run_soak_test import run_soak_test, write_soak_reports


def test_api_load_and_latency_budgets():
    """Asserts that concurrent load testing meets p95 latency and error rate budgets."""
    results = run_load_test(total_requests=150, concurrency=5)
    write_reports(results)

    # Validate results structure
    assert results["total_requests"] == 150
    assert results["concurrency"] == 5
    assert results["throughput_req_per_sec"] > 0

    # Validate budgets
    assert results["budgets"]["p95_latency_ms"]["status"] == "PASS"
    assert results["budgets"]["error_rate_percent"]["status"] == "PASS"
    assert results["overall_latency"]["p95_ms"] <= 200.0
    assert results["error_rate_percent"] <= 0.10

    # Verify committed artifacts
    json_path = ROOT / "reports" / "load" / "LOAD_TEST_RESULTS.json"
    md_path = ROOT / "reports" / "load" / "LOAD_TEST_RESULTS.md"
    assert json_path.exists()
    assert md_path.exists()

    with open(json_path) as f:
        data = json.load(f)
    assert data["budgets"]["p95_latency_ms"]["status"] == "PASS"


def test_api_sustained_soak_memory_stability():
    """Asserts that continuous soak workload maintains memory stability and zero leaks."""
    results = run_soak_test(duration_seconds=5, interval_seconds=1.0)
    write_soak_reports(results)

    # Validate results structure
    assert results["duration_seconds"] >= 4.5
    assert results["total_requests"] > 0

    # Validate stability budget
    assert results["budgets"]["memory_stability"]["status"] == "PASS"
    assert results["budgets"]["error_rate"]["status"] == "PASS"
    assert results["growth_percent"] <= 15.0

    # Verify committed artifacts
    json_path = ROOT / "reports" / "load" / "SOAK_TEST_RESULTS.json"
    md_path = ROOT / "reports" / "load" / "SOAK_TEST_RESULTS.md"
    assert json_path.exists()
    assert md_path.exists()
