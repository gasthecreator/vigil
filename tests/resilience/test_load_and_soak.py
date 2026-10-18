"""tests/resilience/test_load_and_soak.py

Real-HTTP load and soak harness tests (uvicorn subprocess + httpx client).

* Short runs write only into a temporary directory. They never touch reports/load/ (earlier versions
  of this file overwrote the committed results on every pytest run).
* The committed-result tests check what the committed files claim (transport, duration actually run).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import http_load_harness as h  # noqa: E402
import run_load_test as rlt  # noqa: E402
import run_soak_test as rst  # noqa: E402

REPORTS = ROOT / "reports" / "load"


def _digest_tree() -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(REPORTS.glob("*")) if p.is_file()}


@pytest.fixture(scope="module")
def short_load(tmp_path_factory):
    before = _digest_tree()
    out = tmp_path_factory.mktemp("load")
    res = rlt.run_load_test(total_requests=120, concurrency=4)
    rlt.write_reports(res, out)
    return res, out, before


def test_load_goes_over_http_to_a_separate_authenticated_server(short_load):
    res, _, _ = short_load
    assert res["transport"] == "http"
    assert res["host"]["tls"] is False and res["host"]["uvicorn_workers"] == 1
    assert res["total_requests"] == 120 and res["concurrency"] == 4
    # every request authenticated (a 401 anywhere means the harness measured nothing real)
    for ep, d in res["endpoints"].items():
        assert set(d["status_codes"]) == {"200"}, (ep, d["status_codes"])
    assert "/api/v1/patients/{id}/labs" in res["endpoints"], "write path must be part of the workload"
    assert res["server_rss_mb"]["start"] and res["server_rss_mb"]["end"]


def test_load_budgets_are_evaluated_not_assumed(short_load):
    res, _, _ = short_load
    assert set(res["budgets"]) == {"p95_latency_ms", "error_rate_percent"}
    assert res["budgets"]["error_rate_percent"]["status"] == "PASS"
    assert res["budgets"]["p95_latency_ms"]["measured"] == res["overall_latency"]["p95_ms"]


def test_short_runs_never_modify_committed_reports(short_load):
    _, out, before = short_load
    assert (out / f"{rlt.NAME}.json").exists() and (out / f"{rlt.NAME}.md").exists()
    assert _digest_tree() == before


def test_bad_credentials_are_counted_as_errors_so_the_harness_can_fail():
    with h.running_server() as (base, _token, pid):
        rec, wall, _ = asyncio.run(h._drive(base, "not-a-token", 2, 20, None, {"pid": pid, "interval": 60}))
    statuses = {r[2] for r in rec if r[1] != "/health"}
    assert statuses == {401}


def test_soak_analysis_reports_drift_and_current_rss(tmp_path):
    res = rst.run_soak_test(duration_seconds=12, concurrency=3, interval_seconds=1.0)
    assert res["transport"] == "http"
    assert res["duration_seconds"] >= 11.0
    s = res["soak"]
    assert s["rss_samples_used"] >= 4 and s["rss_median_first_quarter_mb"] and s["rss_median_last_quarter_mb"]
    assert set(s["verdicts"]) == {"p95_latency_ms", "error_rate_percent", "p95_drift_percent", "rss_growth_percent"}
    rst.write_reports(res, tmp_path)
    assert "not peak RSS" in (tmp_path / f"{rst.NAME}.md").read_text()


def test_soak_verdict_fails_when_memory_grows_over_budget():
    base = {"overall_latency": {"p95_ms": 10.0}, "error_rate_percent": 0.0, "duration_seconds": 100.0, "_records": [(float(i), "/x", 200, 10.0) for i in range(100)],
            "server_rss_mb": {"samples": [{"elapsed_s": float(10 + 10 * i), "rss_mb": 100.0 + 10.0 * i, "requests": i} for i in range(9)]}}
    out = rst.analyse(base)
    assert out["soak"]["rss_growth_percent"] > rst.SOAK_BUDGETS["rss_growth_percent"]
    assert out["soak"]["verdicts"]["rss_growth_percent"] == "FAIL/UNMEASURABLE"


def test_committed_soak_result_is_http_and_at_least_30_minutes():
    p = REPORTS / f"{rst.NAME}.json"
    assert p.exists(), "commit the result of `python scripts/run_soak_test.py` (default 1800 s)"
    d = json.loads(p.read_text())
    assert d["transport"] == "http"
    assert d["duration_seconds"] >= 1800, d["duration_seconds"]
    assert d["total_requests"] > 1000


def test_committed_load_result_is_http():
    p = REPORTS / f"{rlt.NAME}.json"
    assert p.exists(), "commit the result of `python scripts/run_load_test.py`"
    d = json.loads(p.read_text())
    assert d["transport"] == "http" and d["total_requests"] >= 1000
