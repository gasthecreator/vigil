"""G-09: liveness, readiness, and Prometheus /metrics."""

from __future__ import annotations

from fastapi.testclient import TestClient
from vigil_api.main import app


def test_live_returns_alive():
    client = TestClient(app)
    r = client.get("/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_ready_checks_database():
    client = TestClient(app)
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"


def test_metrics_exposes_prometheus_text():
    client = TestClient(app)
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    assert "vigil_http_requests_total" in r.text


def test_probes_excluded_from_openapi_until_prop0007():
    """Acceptance P14 PUBLIC_EXACT only lists / and /health; keep probes out of schema."""
    paths = app.openapi()["paths"]
    assert "/live" not in paths
    assert "/ready" not in paths
    assert "/metrics" not in paths
