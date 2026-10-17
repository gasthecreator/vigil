"""
tests/test_report_traceability.py

Enforces Overseer Condition D1:
Verifies that every numeric metric in benchmark reports is produced from results.json by code,
and fails if a report table contains a numeric literal not traceable to a results file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_FILE = ROOT / "reports" / "ml" / "BENCHMARK_REPORT.md"
RESULTS_FILE = ROOT / "reports" / "ml" / "results.json"


def test_results_json_exists():
    assert RESULTS_FILE.exists(), f"Benchmark results file missing: {RESULTS_FILE}"


def test_benchmark_report_traceability():
    """
    Parses leaderboard table in BENCHMARK_REPORT.md and verifies 100% of numeric cells
    trace directly to reports/ml/results.json.
    """
    assert REPORT_FILE.exists(), f"Benchmark report missing: {REPORT_FILE}"
    assert RESULTS_FILE.exists(), f"Results JSON missing: {RESULTS_FILE}"

    with open(RESULTS_FILE, "r") as f:
        results_data = json.load(f)

    leaderboard = results_data.get("leaderboard", {})
    assert len(leaderboard) > 0, "No leaderboard data found in results.json"

    report_text = REPORT_FILE.read_text(encoding="utf-8")

    # Match table rows like: | `B4_GRADIENT_BOOSTING` | Non-linear Tree | 0.8141 | 0.0842 | 0.0412 | 245.0 days | 1.45 ms |
    row_pattern = re.compile(
        r"\|\s*`([A-Z0-9_]+)`\s*\|\s*([^|]+)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)\s*days\s*\|\s*([\d\.]+)\s*ms\s*\|"
    )

    matches = list(row_pattern.finditer(report_text))
    assert len(matches) >= len(leaderboard), (
        f"Expected at least {len(leaderboard)} table rows in report, found {len(matches)}"
    )

    for m in matches:
        model_id = m.group(1)
        _family = m.group(2).strip()
        auc = float(m.group(3))
        brier = float(m.group(4))
        ece = float(m.group(5))
        lead_time = float(m.group(6))
        latency = float(m.group(7))

        assert model_id in leaderboard, (
            f"Model ID `{model_id}` in report table not found in results.json"
        )
        expected = leaderboard[model_id]

        assert abs(auc - expected["ipcw_roc_auc"]) < 1e-3, (
            f"[{model_id}] Reported AUC {auc} does not match results.json ({expected['ipcw_roc_auc']})"
        )
        assert abs(brier - expected["brier_score"]) < 1e-3, (
            f"[{model_id}] Reported Brier {brier} does not match results.json ({expected['brier_score']})"
        )
        assert abs(ece - expected["ece"]) < 1e-3, (
            f"[{model_id}] Reported ECE {ece} does not match results.json ({expected['ece']})"
        )
        assert abs(lead_time - expected["lead_time_days"]) < 0.2, (
            f"[{model_id}] Reported lead time {lead_time} does not match results.json ({expected['lead_time_days']})"
        )
        assert abs(latency - expected["latency_p95_ms"]) < 0.1, (
            f"[{model_id}] Reported latency {latency} does not match results.json ({expected['latency_p95_ms']})"
        )


def test_reality_audit_zero_findings():
    """
    Condition R2: scripts/reality_audit.py runs with zero findings.
    """
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "reality_audit.py"), "--require-stub-registry"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"reality_audit.py failed with findings:\n{res.stdout}\n{res.stderr}"
    )
