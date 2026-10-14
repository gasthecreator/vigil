"""Automated verification suite for FastAPI endpoints."""

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/opt/libomp/lib"

import pytest
from fastapi.testclient import TestClient

from sentinel.main import app
from sentinel.database import Base, engine


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_root_and_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["system"] == "Sentinel"

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["ml_engine_loaded"] is True


def test_patient_workflow(client):
    # 1. Create Patient
    p_resp = client.post("/api/v1/patients/", json={"age": 52, "status": "active"})
    assert p_resp.status_code == 201
    p_data = p_resp.json()
    patient_id = p_data["id"]
    assert p_data["age"] == 52

    # 2. Submit Baseline Profile
    b_resp = client.post(
        f"/api/v1/patients/{patient_id}/baseline",
        json={
            "tumor_stage": 2,
            "er_status": True,
            "pr_status": True,
            "her2_status": False,
            "has_hypertension": False,
            "renal_history": False,
        },
    )
    assert b_resp.status_code == 200
    b_data = b_resp.json()
    assert "target_organ_susceptibility_vector" in b_data
    organ_vec = b_data["target_organ_susceptibility_vector"]
    assert "bone" in organ_vec
    assert "liver" in organ_vec

    # 3. Submit Normal Lab Result
    l1_resp = client.post(
        f"/api/v1/patients/{patient_id}/labs",
        json={
            "date_drawn": "2025-01-10T08:30:00",
            "alt_level": 22.0,
            "ast_level": 20.0,
            "creatinine": 0.85,
            "ca_15_3": 17.0,
            "wbc_count": 6.2,
        },
    )
    assert l1_resp.status_code == 200
    l1_data = l1_resp.json()
    assert "calculated_metastasis_risk" in l1_data
    assert l1_data["triage_flag"] is False
    assert l1_data["calculated_metastasis_risk"] < 0.40

    # 4. Submit Anomaly Lab Result
    l2_resp = client.post(
        f"/api/v1/patients/{patient_id}/labs",
        json={
            "date_drawn": "2025-04-10T08:30:00",
            "alt_level": 95.0,
            "ast_level": 88.0,
            "creatinine": 0.90,
            "ca_15_3": 68.0,
            "wbc_count": 10.8,
        },
    )
    assert l2_resp.status_code == 200
    l2_data = l2_resp.json()
    assert l2_data["triage_flag"] is True
    assert l2_data["calculated_metastasis_risk"] >= 0.75
    assert "ACTIONABLE ALERT" in l2_data["justification_text"]

    # 5. Check Trajectory Endpoint
    t_resp = client.get(f"/api/v1/patients/{patient_id}/trajectory")
    assert t_resp.status_code == 200
    trajectory = t_resp.json()
    assert len(trajectory) == 2
    assert trajectory[0]["alt_level"] == 22.0
    assert trajectory[1]["alt_level"] == 95.0
    assert trajectory[1]["triage_flag"] is True

    # 6. Check Triage Queue
    q_resp = client.get("/api/v1/patients/triage")
    assert q_resp.status_code == 200
    queue = q_resp.json()
    assert len(queue) >= 1
    # First item should have high risk
    assert queue[0]["latest_risk"] >= 0.75

    # 7. Check Simulation Endpoint
    s_resp = client.post(
        f"/api/v1/patients/{patient_id}/simulate",
        json={
            "hypothetical_lab": {
                "alt_level": 120.0,
                "ast_level": 110.0,
                "creatinine": 0.95,
                "ca_15_3": 85.0,
                "wbc_count": 11.5,
            }
        },
    )
    assert s_resp.status_code == 200
    sim_data = s_resp.json()
    assert sim_data["projected_risk"] >= 0.75
