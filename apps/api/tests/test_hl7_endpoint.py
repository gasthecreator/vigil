"""Integration tests for HL7 v2 ORU^R01 ingestion endpoint."""

import pytest
from fastapi.testclient import TestClient
from vigil_api.database import Base, engine
from vigil_api.main import app
from vigil_core.hl7 import generate_oru_r01


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_hl7_oru_r01_successful_ingestion(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # 1. Create Patient & Grant Consent
    p_resp = client.post("/api/v1/patients/", json={"age": 52, "status": "active"}, headers=headers)
    assert p_resp.status_code == 201
    pid = p_resp.json()["id"]

    c_resp = client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"scope": "clinical_care", "granted": True},
        headers=headers,
    )
    assert c_resp.status_code == 201

    # 2. Build HL7 v2 ORU^R01 message
    hl7_text = (
        f"MSH|^~\\&|LIS_CENTRAL|HOSP_A|VIGIL|ONCOLOGY|20261017083000||ORU^R01|MSG-HL7-001|P|2.5\r\n"
        f"PID|1||{pid}^^^HOSP^MR||Doe^Jane\r\n"
        f"OBR|1|||LAB^SURVEILLANCE|||20261017081500\r\n"
        f"OBX|1|NM|83082-8^CA 15-3^LN||22.4|U/mL|< 30.0|N|||F|||20261017081500|LAB-01\r\n"
        f"OBX|2|NM|1742-6^ALT^LN||29.0|U/L|7-35|N|||F|||20261017081500|LAB-01\r\n"
    )

    # 3. Post raw text HL7
    r = client.post(
        "/api/v1/hl7/oru-r01",
        content=hl7_text.encode("utf-8"),
        headers={**headers, "content-type": "text/plain"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["message_control_id"] == "MSG-HL7-001"
    assert data["patient_id"] == pid
    assert data["total_observations"] == 2
    assert data["imported_count"] == 2
    assert data["rejected_count"] == 0

    # Verify audit event was logged
    audit_resp = client.get("/api/v1/audit/verify", headers={"X-Vigil-Role": "admin"})
    assert audit_resp.status_code == 200
    assert audit_resp.json()["valid"] is True


def test_hl7_oru_r01_json_wrapper(client):
    headers = {"X-Vigil-Role": "nurse_clerk", "X-Vigil-User-Id": "nurse-1"}

    # 1. Create Patient & Grant Consent
    p_resp = client.post("/api/v1/patients/", json={"age": 48, "status": "active"}, headers=headers)
    pid = p_resp.json()["id"]

    client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"scope": "clinical_care", "granted": True},
        headers=headers,
    )

    # 2. Build message via generate_oru_r01
    msg_raw = generate_oru_r01(
        message_control_id="MSG-JSON-002",
        patient_id=pid,
        observations=[{"analyte_code": "ca_15_3", "value": 19.5, "unit": "U/mL"}],
        patient_name="Smith Mary",
    )

    # 3. Post as JSON payload
    r = client.post(
        "/api/v1/hl7/oru-r01",
        json={"hl7_message": msg_raw},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported_count"] == 1
    assert data["observation_reports"][0]["analyte_code"] == "ca_15_3"


def test_hl7_oru_r01_consent_rejection(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # Patient created with NO consent
    p_resp = client.post("/api/v1/patients/", json={"age": 60, "status": "active"}, headers=headers)
    pid = p_resp.json()["id"]

    hl7_text = (
        f"MSH|^~\\&|LIS|HOSP|VIGIL|ONCOLOGY|20261017083000||ORU^R01|MSG-NOCONSENT|P|2.5\r\n"
        f"PID|1||{pid}\r\n"
        f"OBX|1|NM|83082-8^CA 15-3^LN||22.4|U/mL\r\n"
    )

    r = client.post(
        "/api/v1/hl7/oru-r01",
        content=hl7_text.encode("utf-8"),
        headers={**headers, "content-type": "text/plain"},
    )
    assert r.status_code == 403


def test_hl7_oru_r01_malformed_rejection(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    # Malformed HL7
    r = client.post(
        "/api/v1/hl7/oru-r01",
        content=b"NOT A VALID HL7 MESSAGE",
        headers={**headers, "content-type": "text/plain"},
    )
    assert r.status_code == 422


def test_hl7_oru_r01_unknown_patient_404(client):
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-1"}

    hl7_text = (
        "MSH|^~\\&|LIS|HOSP|VIGIL|ONCOLOGY|20261017083000||ORU^R01|MSG-UNKNOWN|P|2.5\r\n"
        "PID|1||NONEXISTENT-PT-9999\r\n"
        "OBX|1|NM|83082-8^CA 15-3^LN||22.4|U/mL\r\n"
    )

    r = client.post(
        "/api/v1/hl7/oru-r01",
        content=hl7_text.encode("utf-8"),
        headers={**headers, "content-type": "text/plain"},
    )
    assert r.status_code == 404
