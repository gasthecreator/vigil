"""Tests for Server-Sent Events (SSE) alert stream.

Adheres to MASTER_PLAN.md §9.2, WP5.4, and Phase 5 deliverables.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from vigil_api.database import Base, engine
from vigil_api.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_sse_stream_clinician_success(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # 1. Create Patient & Grant Consent
    p_resp = client.post("/api/v1/patients/", json={"age": 55, "status": "active"}, headers=headers)
    assert p_resp.status_code == 201
    pid = p_resp.json()["id"]

    client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"scope": "clinical_care", "granted": True},
        headers=headers,
    )

    # 2. Ingest baseline observation
    client.post(
        f"/api/v1/patients/{pid}/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 18.0,
            "unit": "U/mL",
            "specimen_collected_at": "2026-09-01T10:00:00Z",
        },
        headers=headers,
    )

    # 3. Ingest a spike observation that triggers an alert
    obs_resp = client.post(
        f"/api/v1/patients/{pid}/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 85.0,
            "unit": "U/mL",
            "specimen_collected_at": "2026-10-17T10:00:00Z",
        },
        headers=headers,
    )
    assert obs_resp.status_code == 201

    # 3. Stream alerts via SSE
    resp = client.get(
        f"/api/v1/alerts/stream?patient_id={pid}&max_events=1",
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "event: alert" in body
    assert pid in body
    assert "keep-alive" in body


def test_sse_stream_consent_rejection(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # Patient created with NO consent
    p_resp = client.post("/api/v1/patients/", json={"age": 62, "status": "active"}, headers=headers)
    assert p_resp.status_code == 201
    pid = p_resp.json()["id"]

    # Attempt to stream alerts for patient without consent -> 403 Forbidden
    resp = client.get(
        f"/api/v1/alerts/stream?patient_id={pid}",
        headers=headers,
    )
    assert resp.status_code == 403


def test_sse_stream_patient_role_restrictions(client):
    headers_doc = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}
    headers_pat = {"X-Vigil-Role": "patient", "X-Vigil-User-Id": "pat-1"}

    # Create patient
    p_resp = client.post("/api/v1/patients/", json={"age": 49, "status": "active"}, headers=headers_doc)
    pid = p_resp.json()["id"]

    # 1. Patient role streaming without patient_id is rejected (400)
    resp_no_id = client.get("/api/v1/alerts/stream", headers=headers_pat)
    assert resp_no_id.status_code == 400

    # 2. Patient role streaming for a different patient is forbidden (403)
    resp_diff_pat = client.get(f"/api/v1/alerts/stream?patient_id={pid}", headers=headers_pat)
    assert resp_diff_pat.status_code == 403
