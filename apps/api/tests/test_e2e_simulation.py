"""End-to-End Clinical Verification Simulation Test for Vigil Surveillance.

Converts the prototype's demonstration script into a formal automated pytest test
suite per MASTER_PLAN.md §15 Defect A9 and §14 WP0.7.
Removes machine-specific paths (Defect A16).
"""

import os

os.environ["OMP_NUM_THREADS"] = "1"

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from vigil_api.database import Base, engine
from vigil_api.main import app


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_e2e_surveillance_simulation(client):
    """Executes a 5-stage patient surveillance progression:

    1. Enrolls patient
    2. Stores baseline pathology without the retracted M1 prior
    3. Submits 5 sequential lab draws through the separate M3/K2 workflow
    4. Verifies recurrence-risk estimates remain unavailable
    5. Verifies the patient remains visible in the task-oriented Triage Queue
    """
    # Step 1: Enroll Patient
    p_resp = client.post(
        "/api/v1/patients/", json={"age": 54, "status": "active", "synthetic": True}
    )
    assert p_resp.status_code == 201, f"Failed to create patient: {p_resp.text}"
    patient = p_resp.json()
    patient_id = patient["id"]
    client.post(f"/api/v1/patients/{patient_id}/consent", json={"scope": "full", "granted": True})

    # Step 2: Submit Baseline Pathology: Stage IIb, ER+, PR-, HER2+
    b_resp = client.post(
        f"/api/v1/patients/{patient_id}/baseline",
        json={
            "tumor_stage": 2,
            "er_status": True,
            "pr_status": False,
            "her2_status": True,
            "has_hypertension": True,
            "renal_history": False,
        },
    )
    assert b_resp.status_code == 200, f"Failed baseline: {b_resp.text}"
    baseline = b_resp.json()
    assert baseline["target_organ_susceptibility_vector"] is None

    # Step 3: Ingest 5 Sequential Lab Draws (Normal -> Accelerated Spike)
    base_date = datetime(2025, 1, 15, 9, 0, 0)
    simulated_draws = [
        # Visit 1: Post-treatment nadir (Normal)
        {
            "date_drawn": (base_date).isoformat(),
            "alt_level": 22.0,
            "ast_level": 19.0,
            "creatinine": 0.85,
            "ca_15_3": 16.5,
            "wbc_count": 6.1,
        },
        # Visit 2: 3-Month Routine (Normal)
        {
            "date_drawn": (base_date + timedelta(days=90)).isoformat(),
            "alt_level": 24.0,
            "ast_level": 21.0,
            "creatinine": 0.88,
            "ca_15_3": 18.0,
            "wbc_count": 6.4,
        },
        # Visit 3: 6-Month Routine (Borderline velocity inflection)
        {
            "date_drawn": (base_date + timedelta(days=180)).isoformat(),
            "alt_level": 35.0,
            "ast_level": 30.0,
            "creatinine": 0.90,
            "ca_15_3": 25.5,
            "wbc_count": 7.2,
        },
        # Visit 4: 9-Month Follow-up (Sub-threshold divergence)
        {
            "date_drawn": (base_date + timedelta(days=270)).isoformat(),
            "alt_level": 58.0,
            "ast_level": 52.0,
            "creatinine": 0.92,
            "ca_15_3": 38.0,
            "wbc_count": 8.9,
        },
        # Visit 5: 12-Month Follow-up (Full Metastatic Biomarker Spike)
        {
            "date_drawn": (base_date + timedelta(days=360)).isoformat(),
            "alt_level": 115.0,
            "ast_level": 105.0,
            "creatinine": 0.98,
            "ca_15_3": 78.0,
            "wbc_count": 11.8,
        },
    ]

    last_risk_response = None
    for draw in simulated_draws:
        resp = client.post(f"/api/v1/patients/{patient_id}/labs", json=draw)
        assert resp.status_code == 200, f"Lab submission failed: {resp.text}"
        last_risk_response = resp.json()

    # Step 4: Lab data is saved while the unsupported recurrence-risk output abstains.
    assert last_risk_response is not None
    assert last_risk_response["status"] == "unavailable"
    assert last_risk_response["calculated_metastasis_risk"] is None
    assert last_risk_response["triage_flag"] is None

    # Step 5: Verify Full Trajectory
    traj_resp = client.get(f"/api/v1/patients/{patient_id}/trajectory")
    assert traj_resp.status_code == 200
    traj_data = traj_resp.json()
    assert len(traj_data) == 5

    # Step 6: Verify Triage Queue
    queue_resp = client.get("/api/v1/patients/triage")
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    assert len(queue) >= 1
    # The patient remains in the queue without a fabricated recurrence-risk score.
    matching = [q for q in queue if q["patient_id"] == patient_id]
    assert len(matching) == 1
    assert matching[0]["triage_flag"] is None
    assert matching[0]["latest_risk"] is None
