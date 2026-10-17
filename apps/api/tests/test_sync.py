"""Tests for Offline Sync Service with Idempotency and LWW Conflict Resolution.

Adheres to MASTER_PLAN.md §9.2, WP5.5, and Phase 5 deliverables.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def test_offline_sync_batch_successful_replay(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # 1. Create Patient & Grant Consent
    p_resp = client.post("/api/v1/patients/", json={"age": 52, "status": "active"}, headers=headers)
    assert p_resp.status_code == 201
    pid = p_resp.json()["id"]

    client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"scope": "clinical_care", "granted": True},
        headers=headers,
    )

    # 2. Build Offline Sync Batch with 2 observations
    now = datetime.now(timezone.utc)
    batch_payload = {
        "sync_id": "SYNC-BATCH-001",
        "client_device_id": "tablet-clinic-A",
        "client_timestamp": now.isoformat(),
        "mutations": [
            {
                "client_mutation_id": "mut-001",
                "entity_type": "observation",
                "action": "create",
                "patient_id": pid,
                "client_updated_at": (now - timedelta(hours=2)).isoformat(),
                "payload": {
                    "analyte_code": "ca_15_3",
                    "value": 19.5,
                    "unit": "U/mL",
                    "specimen_collected_at": (now - timedelta(hours=2)).isoformat(),
                },
            },
            {
                "client_mutation_id": "mut-002",
                "entity_type": "observation",
                "action": "create",
                "patient_id": pid,
                "client_updated_at": (now - timedelta(hours=1)).isoformat(),
                "payload": {
                    "analyte_code": "alt",
                    "value": 24.0,
                    "unit": "U/L",
                    "specimen_collected_at": (now - timedelta(hours=1)).isoformat(),
                },
            },
        ],
    }

    # 3. Submit Batch
    resp = client.post("/api/v1/sync/batch", json=batch_payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_mutations"] == 2
    assert data["applied_count"] == 2
    assert data["already_applied_count"] == 0
    assert data["conflict_count"] == 0
    assert data["rejected_count"] == 0

    # 4. Replay IDENTICAL batch to test Idempotency
    replay_resp = client.post("/api/v1/sync/batch", json=batch_payload, headers=headers)
    assert replay_resp.status_code == 200
    replay_data = replay_resp.json()
    assert replay_data["total_mutations"] == 2
    assert replay_data["applied_count"] == 0
    assert replay_data["already_applied_count"] == 2
    assert replay_data["results"][0]["status"] == "already_applied"


def test_offline_sync_lww_conflict_resolution(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # 1. Create Patient & Consent
    p_resp = client.post("/api/v1/patients/", json={"age": 58, "status": "active"}, headers=headers)
    pid = p_resp.json()["id"]
    client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"scope": "clinical_care", "granted": True},
        headers=headers,
    )

    # 2. Ingest baseline then spike to produce an Alert and FollowUpTask
    t0 = datetime.now(timezone.utc) - timedelta(days=5)
    client.post(
        f"/api/v1/patients/{pid}/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 18.0,
            "unit": "U/mL",
            "specimen_collected_at": t0.isoformat(),
        },
        headers=headers,
    )
    t1 = t0 + timedelta(days=2)
    obs_resp = client.post(
        f"/api/v1/patients/{pid}/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 85.0,
            "unit": "U/mL",
            "specimen_collected_at": t1.isoformat(),
        },
        headers=headers,
    )
    assert obs_resp.status_code == 201
    task_id = obs_resp.json()["follow_up_task"]["id"]

    # 3. Simulate server updated the task at t2
    t2 = t1 + timedelta(days=1)
    client.patch(
        f"/api/v1/follow-up/tasks/{task_id}",
        json={"notes": "Server updated note at t2", "status": "in_progress"},
        headers=headers,
    )

    # 4. Now client tries to sync an offline mutation that was created at t0 (older than server t2)
    stale_payload = {
        "sync_id": "SYNC-STALE-002",
        "client_timestamp": t2.isoformat(),
        "mutations": [
            {
                "client_mutation_id": "mut-stale-001",
                "entity_type": "follow_up_task",
                "action": "update",
                "entity_id": task_id,
                "patient_id": pid,
                "client_updated_at": t0.isoformat(),  # Stale!
                "payload": {
                    "notes": "Stale offline edit",
                    "status": "pending",
                },
            }
        ],
    }

    r_stale = client.post("/api/v1/sync/batch", json=stale_payload, headers=headers)
    assert r_stale.status_code == 200
    stale_res = r_stale.json()
    assert stale_res["conflict_count"] == 1
    assert stale_res["results"][0]["status"] == "conflict_server_wins"

    # 5. Client syncs an edit created at t3 (newer than server updated_at) -> Client wins!
    t3 = datetime.now(timezone.utc) + timedelta(minutes=5)
    fresh_payload = {
        "sync_id": "SYNC-FRESH-003",
        "client_timestamp": t3.isoformat(),
        "mutations": [
            {
                "client_mutation_id": "mut-fresh-001",
                "entity_type": "follow_up_task",
                "action": "update",
                "entity_id": task_id,
                "patient_id": pid,
                "client_updated_at": t3.isoformat(),  # Newer!
                "payload": {
                    "notes": "Fresh offline edit from clinician",
                    "status": "completed",
                },
            }
        ],
    }

    r_fresh = client.post("/api/v1/sync/batch", json=fresh_payload, headers=headers)
    assert r_fresh.status_code == 200
    fresh_res = r_fresh.json()
    assert fresh_res["applied_count"] == 1
    assert fresh_res["results"][0]["status"] == "applied"


def test_offline_sync_unconsented_patient_rejected(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # Patient with NO consent
    p_resp = client.post("/api/v1/patients/", json={"age": 60, "status": "active"}, headers=headers)
    pid = p_resp.json()["id"]

    now = datetime.now(timezone.utc)
    batch_payload = {
        "sync_id": "SYNC-NOCONSENT-004",
        "client_timestamp": now.isoformat(),
        "mutations": [
            {
                "client_mutation_id": "mut-noconsent-001",
                "entity_type": "observation",
                "patient_id": pid,
                "client_updated_at": now.isoformat(),
                "payload": {"analyte_code": "ca_15_3", "value": 20.0, "unit": "U/mL"},
            }
        ],
    }

    resp = client.post("/api/v1/sync/batch", json=batch_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rejected_count"] == 1
    assert data["results"][0]["status"] == "rejected"
    assert "Consent" in data["results"][0]["error"]
