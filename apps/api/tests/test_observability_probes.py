"""G-09: liveness, readiness, and the token-gated Prometheus /metrics."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from vigil_api.config import settings
from vigil_api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_live_returns_alive(client):
    r = client.get("/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_ready_checks_database(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "database": "ok"}


def test_ready_reports_503_without_leaking_error_detail(client, monkeypatch):
    import vigil_api.observability as obs

    class Boom:
        def connect(self):
            raise RuntimeError("password=hunter2 host=db.internal")

    monkeypatch.setattr(obs, "engine", Boom())
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.json() == {"status": "not_ready", "database": "unavailable"}
    assert "hunter2" not in r.text and "RuntimeError" not in r.text


def test_probes_are_in_the_openapi_schema():
    paths = app.openapi()["paths"]
    for route in ("/live", "/ready", "/metrics"):
        assert route in paths


@pytest.mark.parametrize("env", ["local", "production"])
def test_metrics_disabled_without_token_in_every_profile(client, monkeypatch, env):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", env)
    assert client.get("/metrics").status_code == 403


@pytest.mark.parametrize("env", ["local", "production"])
def test_metrics_with_token_rejects_missing_and_wrong_token(client, monkeypatch, env):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "s3cret-scrape-token")
    monkeypatch.setattr(settings, "ENVIRONMENT", env)
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert (
        client.get("/metrics", headers={"Authorization": "s3cret-scrape-token"}).status_code == 401
    )
    ok = client.get("/metrics", headers={"Authorization": "Bearer s3cret-scrape-token"})
    assert ok.status_code == 200
    assert "vigil_http_requests_total" in ok.text


def test_metric_labels_do_not_contain_identifiers(client, monkeypatch):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "tok")
    client.get("/api/v1/patients/PATIENT-SECRET-123/timeline")
    text = client.get("/metrics", headers={"Authorization": "Bearer tok"}).text
    assert "PATIENT-SECRET-123" not in text
