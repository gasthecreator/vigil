"""Automated verification suite for Vigil FastAPI endpoints.

Remediates Defect A9, A16 (removes machine-specific libomp path),
and adds tests for CORS and environment profiles (A5, A6).
"""

import os

os.environ["OMP_NUM_THREADS"] = "1"

import pytest
from fastapi.testclient import TestClient
from vigil_api.config import settings
from vigil_api.database import Base, SessionLocal, engine
from vigil_api.main import app
from vigil_api.ml.inference import VigilEngine
from vigil_api.models.patient import RiskInference


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
    data = r.json()
    assert data["system"] == "Vigil"
    assert "disclaimer" in data
    assert data["is_synthetic"] is True

    h = client.get("/health")
    assert h.status_code == 200
    h_data = h.json()
    assert h_data["ml_engine_loaded"] is False
    assert h_data["ml_model_status"] == "quarantined_no_validated_model"
    assert h_data["is_synthetic"] is True


def test_patient_workflow(client):
    # 1. Create Patient
    p_resp = client.post("/api/v1/patients/", json={"age": 52, "status": "active"})
    assert p_resp.status_code == 201
    p_data = p_resp.json()
    patient_id = p_data["id"]
    assert p_data["age"] == 52
    client.post(f"/api/v1/patients/{patient_id}/consent", json={"scope": "full", "granted": True})

    # 2. Submit Baseline Profile (Uses Literature/SEER priors)
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
    assert b_data["target_organ_susceptibility_vector"] is None

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
    assert l1_data["status"] == "unavailable"
    assert l1_data["calculated_metastasis_risk"] is None
    assert l1_data["triage_flag"] is None

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
    assert l2_data["status"] == "unavailable"
    assert l2_data["calculated_metastasis_risk"] is None
    assert l2_data["triage_flag"] is None
    assert "validated recurrence-risk model is unavailable" in l2_data["message"]

    # 5. Check Trajectory Endpoint
    t_resp = client.get(f"/api/v1/patients/{patient_id}/trajectory")
    assert t_resp.status_code == 200
    trajectory = t_resp.json()
    assert len(trajectory) == 2
    assert trajectory[0]["alt_level"] == 22.0
    assert trajectory[1]["alt_level"] == 95.0
    assert trajectory[1]["calculated_metastasis_risk"] is None
    assert trajectory[1]["ci_lower"] is None
    assert trajectory[1]["ci_upper"] is None
    assert trajectory[1]["triage_flag"] is None

    # 6. Check Triage Queue
    q_resp = client.get("/api/v1/patients/triage")
    assert q_resp.status_code == 200
    queue = q_resp.json()
    assert len(queue) >= 1
    assert queue[0]["latest_risk"] is None
    assert queue[0]["triage_flag"] is None

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
    assert sim_data["status"] == "abstained"
    assert sim_data["projected_risk"] is None
    assert sim_data["delta_risk"] is None
    assert sim_data["triage_flag"] is None

    # Historical heuristic rows stay hidden even if present in storage.
    db = SessionLocal()
    try:
        assert db.query(RiskInference).filter_by(patient_id=patient_id).count() == 0
        db.add(
            RiskInference(
                patient_id=patient_id,
                lab_result_id=l2_data["lab_result_id"],
                calculated_metastasis_risk=0.99,
                triage_flag=True,
                justification_text="historical quarantined output",
            )
        )
        db.commit()
    finally:
        db.close()

    detail = client.get(f"/api/v1/patients/{patient_id}").json()
    assert detail["latest_risk"] is None
    assert detail["triage_flag"] is None
    assert "historical quarantined output" not in str(detail)
    trajectory = client.get(f"/api/v1/patients/{patient_id}/trajectory").json()
    assert all(point["calculated_metastasis_risk"] is None for point in trajectory)
    assert all(point["triage_flag"] is None for point in trajectory)
    cohort = client.get("/api/v1/analytics/cohort", headers={"X-Vigil-Role": "clinician"}).json()
    assert cohort["risk_metrics_status"] == "unavailable"
    assert cohort["average_cohort_risk"] is None
    assert cohort["critical_alerts"] is None


def test_legacy_inference_methods_fail_closed():
    engine = VigilEngine()
    with pytest.raises(RuntimeError, match="quarantined"):
        engine.predict_baseline_susceptibility({"er_status": True})
    with pytest.raises(RuntimeError, match="quarantined"):
        engine.predict_risk("patient", {"ca_15_3": 100})


def test_cors_security(client):
    """Verifies that CORS origins do not include wildcard '*' (Defect A5)."""
    assert "*" not in settings.CORS_ORIGINS
    for origin in settings.CORS_ORIGINS:
        assert origin.startswith("http://") or origin.startswith("https://")


def test_demo_seeding_gating(client, monkeypatch):
    """Verifies that seed-demo-cohort is blocked outside 'local' environment (Defect A6) and requires admin (S5-2)."""
    # In local environment (default), it succeeds for admin
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    r_local = client.post(
        "/api/v1/analytics/seed-demo-cohort?num_patients=2", headers={"X-Vigil-Role": "admin"}
    )
    assert r_local.status_code == 201
    seeded = r_local.json()
    assert "no recurrence-risk estimates were generated" in seeded["message"]
    db = SessionLocal()
    try:
        assert (
            db.query(RiskInference)
            .filter(RiskInference.patient_id.in_(seeded["patient_ids"]))
            .count()
            == 0
        )
    finally:
        db.close()

    # In production environment, it is forbidden/unauthorized (HTTP 401 or 403)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    r_prod = client.post(
        "/api/v1/analytics/seed-demo-cohort?num_patients=2", headers={"X-Vigil-Role": "admin"}
    )
    assert r_prod.status_code in (401, 403)
