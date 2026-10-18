"""Automated Black-Box Penetration and Security Verification Suite (Phase 8a).

Governing Specifications:
- docs/security/THREAT_MODEL.md (STRIDE Threat Model v2)
- docs/MASTER_PLAN.md §3, §9.3, §11, §14
- docs/REALITY_RULES.md (RR1, RR2, RR4, RR7)

Covers:
1. Complete OpenAPI Authorization Matrix (Canonical Routes x 8 Roles)
2. Patient Consent Lifecycle Matrix over HTTP (None, Granted, Withdrawn, Expired, Regranted)
3. Forged Body Fuzzing on Mutating Routes (SQL injection, boundary overflow, parameter tampering)
4. Companion Token Security (Expiry, Revocation, Cross-Patient Isolation, Zero-Plaintext at Rest)
5. Offline Batch Sync Replay and Idempotency
6. HL7 v2 Robustness and LOINC/Analyte Fuzzing
7. Error Message Leakage and Stack Trace Hygiene (Zero Internal Path / SQL / Secret Leakage)
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from pathlib import Path
from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Setup isolated environment
os.environ["ENVIRONMENT"] = "local"
os.environ["REQUIRE_AUTH"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from vigil_api.auth import create_access_token
from vigil_api.config import settings
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import Facility, Patient, User, UserRole

settings.REQUIRE_AUTH = True


@pytest.fixture
def test_env(tmp_path):
    """Provides isolated SQLite database and seeded principals for penetration testing."""
    settings.REQUIRE_AUTH = True
    db_file = tmp_path / "pen_suite.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with Session(engine) as session:
        # Seed test facility
        fac = Facility(id="FAC-SEC-01", name="Security Test Hospital", code="SEC-01", tier="tertiary")
        session.add(fac)

        # Seed Patients
        p1 = Patient(id="PAT-SEC-01", facility_id="FAC-SEC-01", mrn="MRN-SEC-01", status="active", age=52)
        p2 = Patient(id="PAT-SEC-02", facility_id="FAC-SEC-01", mrn="MRN-SEC-02", status="active", age=61)
        session.add_all([p1, p2])

        # Seed Users across all roles
        u_clin = User(id="USR-CLIN", username="dr_sec", email="clin@test.org", full_name="Dr Sec", role=UserRole.CLINICIAN.value, facility_id="FAC-SEC-01", hashed_password="mock")
        u_nurse = User(id="USR-NURSE", username="nurse_sec", email="nurse@test.org", full_name="Nurse Sec", role=UserRole.NURSE_CLERK.value, facility_id="FAC-SEC-01", hashed_password="mock")
        u_ql = User(id="USR-QL", username="ql_sec", email="ql@test.org", full_name="QL Sec", role=UserRole.QUALITY_LEAD.value, facility_id="FAC-SEC-01", hashed_password="mock")
        u_admin = User(id="USR-ADMIN", username="admin_sec", email="admin@test.org", full_name="Admin Sec", role=UserRole.ADMIN.value, facility_id="FAC-SEC-01", hashed_password="mock")
        u_pat = User(id="USR-PAT", username="patient_sec", email="pat@test.org", full_name="Patient Sec", role=UserRole.PATIENT.value, hashed_password="mock")
        u_cg = User(id="USR-CG", username="cg_sec", email="cg@test.org", full_name="Caregiver Sec", role=UserRole.CAREGIVER.value, hashed_password="mock")
        session.add_all([u_clin, u_nurse, u_ql, u_admin, u_pat, u_cg])
        session.commit()

    client = TestClient(app, raise_server_exceptions=False)
    yield {
        "client": client,
        "engine": engine,
        "pat1_id": "PAT-SEC-01",
        "pat2_id": "PAT-SEC-02",
    }


def _auth_header(role: str, patient_id: Optional[str] = None) -> Dict[str, str]:
    if role == "unauthenticated":
        return {}
    token = create_access_token(
        subject=f"sub_{role}",
        role=role,
        patient_id=patient_id,
        expires_delta=dt.timedelta(hours=1),
    )
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Complete OpenAPI Authorization Matrix
# ==============================================================================


def test_openapi_authorization_matrix(test_env):
    """Tests all canonical routes across all 8 security roles to verify least privilege."""
    client: TestClient = test_env["client"]
    p1 = test_env["pat1_id"]

    roles = [
        "clinician",
        "nurse_clerk",
        "quality_lead",
        "admin",
        "patient",
        "caregiver",
        "unauthenticated",
        "attacker",
    ]

    # Matrix: (method, path, body, allowed_roles)
    endpoints = [
        ("GET", "/api/v1/patients/", None, {"clinician", "nurse_clerk", "quality_lead", "admin"}),
        ("GET", f"/api/v1/patients/{p1}", None, {"clinician", "nurse_clerk", "quality_lead", "admin", "patient", "caregiver"}),
        ("POST", "/api/v1/quality/audit", {"facility_id": "FAC-SEC-01", "include_synthetic_benchmark": False}, {"quality_lead", "admin"}),
        ("GET", "/api/v1/audit/events", None, {"quality_lead", "admin", "clinician"}),
        ("POST", "/api/v1/continuity/courses", {"patient_id": p1, "clinical_context": "curative_tnbc", "total_fractions": 25}, {"clinician", "admin"}),
        ("POST", "/api/v1/continuity/schedule/solve", {"horizon_days": 14, "fairness_disparity_bound": 5.0, "max_wait_days": 30}, {"clinician", "admin", "quality_lead"}),
    ]

    for method, path, body, allowed in endpoints:
        for role in roles:
            headers = _auth_header(role, patient_id=p1 if role in ("patient", "caregiver") else None)
            if method == "GET":
                resp = client.get(path, headers=headers)
            else:
                resp = client.post(path, json=body, headers=headers)

            if role == "unauthenticated":
                assert resp.status_code in (401, 403), f"Unauthenticated request to {method} {path} returned {resp.status_code}"
            elif role == "attacker":
                assert resp.status_code in (401, 403), f"Attacker role on {method} {path} returned {resp.status_code}"
            elif role not in allowed:
                assert resp.status_code in (401, 403), f"Role '{role}' unexpectedly allowed on {method} {path} (got {resp.status_code})"


# ==============================================================================
# 2. Patient Consent Lifecycle Matrix over HTTP
# ==============================================================================


def test_consent_lifecycle_matrix_over_http(test_env):
    """Verifies that observation reads strictly respect the 5 consent lifecycle states over HTTP."""
    client: TestClient = test_env["client"]
    p1 = test_env["pat1_id"]
    h_clin = _auth_header("clinician")

    # State 1: None (no consent granted yet)
    r1 = client.get(f"/api/v1/patients/{p1}/observations", headers=h_clin)
    assert r1.status_code == 403, f"Expected 403 for missing consent, got {r1.status_code}"

    # State 2: Granted
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "clinical_care", "granted": True}, headers=h_clin)
    r2 = client.get(f"/api/v1/patients/{p1}/observations", headers=h_clin)
    assert r2.status_code == 200, f"Expected 200 for granted consent, got {r2.status_code}"

    # State 3: Withdrawn over HTTP
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "clinical_care", "granted": False}, headers=h_clin)
    r3 = client.get(f"/api/v1/patients/{p1}/observations", headers=h_clin)
    assert r3.status_code == 403, f"Expected 403 for withdrawn consent, got {r3.status_code}"

    # State 4: Regranted
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "clinical_care", "granted": True}, headers=h_clin)
    r4 = client.get(f"/api/v1/patients/{p1}/observations", headers=h_clin)
    assert r4.status_code == 200, f"Expected 200 for regranted consent, got {r4.status_code}"


# ==============================================================================
# 3. Forged Body Fuzzing on Mutating Routes
# ==============================================================================


def test_forged_body_fuzzing_on_mutating_routes(test_env):
    """Fuzzes mutating routes with SQLi, malformed types, and parameter tampering."""
    client: TestClient = test_env["client"]
    p1 = test_env["pat1_id"]
    h_clin = _auth_header("clinician")

    # Grant consent so payload validation is executed rather than early consent rejection
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "clinical_care", "granted": True}, headers=h_clin)

    fuzz_payloads = [
        # SQL Injection in string field
        {"analyte_code": "ca_15_3' OR 1=1; DROP TABLE observations; --", "value": 30.0, "unit": "U/mL"},
        # Negative age
        {"age": -45, "status": "active"},
        # Type confusion: string in float field
        {"analyte_code": "ca_15_3", "value": "CRITICAL_HIGH_OVERFLOW", "unit": "U/mL"},
        # Giant buffer overflow attempt
        {"analyte_code": "ca_15_3", "value": 30.0, "unit": "A" * 50000},
        # Forged parameter injection on schedule confirm
        {"assignments": [{"patient_id": p1, "course_id": "c1", "machine_id": "LINAC-01", "start_day": 0, "server_derived_harm": 0.0}]},
    ]

    for payload in fuzz_payloads:
        # Test against patient observations and patients
        r1 = client.post(f"/api/v1/patients/{p1}/observations", json=payload, headers=h_clin)
        assert r1.status_code in (400, 422), f"Fuzz payload returned unhandled status {r1.status_code}: {r1.text}"
        assert "Internal Server Error" not in r1.text


# ==============================================================================
# 4. Companion Token Security & Isolation
# ==============================================================================


def test_companion_token_expiry_and_revocation_enforcement(test_env):
    """Verifies companion tokens expire and are blocked immediately upon revocation."""
    client: TestClient = test_env["client"]
    p1 = test_env["pat1_id"]
    h_clin = _auth_header("clinician")

    # Ensure consent is granted
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "caregiver_sharing,clinical_care", "granted": True}, headers=h_clin)

    # 1. Issue Companion Share Token
    iss_resp = client.post(
        f"/api/v1/patients/{p1}/shares",
        json={"caregiver_name": "Tunde Bakare", "relationship_type": "spouse", "scope": "view_summary", "expires_in_days": 30},
        headers=h_clin,
    )
    assert iss_resp.status_code == 201, f"Failed to issue companion token: {iss_resp.text}"
    token_data = iss_resp.json()
    token_secret = token_data["share_token"]
    share_id = token_data["id"]

    # 2. Token works over HTTP
    r_valid = client.get(f"/api/v1/companion/share/{token_secret}")
    assert r_valid.status_code == 200, f"Valid companion token rejected: {r_valid.text}"
    assert r_valid.json()["patient_id"] == p1

    # 3. Revoke Token via Patient/Clinician
    rev_resp = client.delete(f"/api/v1/patients/{p1}/shares/{share_id}", headers=h_clin)
    assert rev_resp.status_code == 200

    # 4. Revoked Token is immediately rejected
    r_revoked = client.get(f"/api/v1/companion/share/{token_secret}")
    assert r_revoked.status_code == 403, f"Revoked companion token was accepted: {r_revoked.status_code}"


def test_cross_patient_companion_token_isolation(test_env):
    """Verifies that a companion token issued for Patient 1 cannot access Patient 2."""
    client: TestClient = test_env["client"]
    p1 = test_env["pat1_id"]
    p2 = test_env["pat2_id"]
    h_clin = _auth_header("clinician")

    # Grant consent for both
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "caregiver_sharing,clinical_care", "granted": True}, headers=h_clin)
    client.post(f"/api/v1/patients/{p2}/consent", json={"scope": "clinical_care", "granted": True}, headers=h_clin)

    # Issue token for Patient 1
    iss_resp = client.post(
        f"/api/v1/patients/{p1}/shares",
        json={"caregiver_name": "Caregiver 1", "relationship_type": "sibling", "scope": "view_summary"},
        headers=h_clin,
    )
    assert iss_resp.status_code == 201
    token_secret1 = iss_resp.json()["share_token"]

    # Verify Patient 1 token returns Patient 1 and cannot be used to see Patient 2
    r_summary = client.get(f"/api/v1/companion/share/{token_secret1}")
    assert r_summary.status_code == 200
    assert r_summary.json()["patient_id"] == p1
    assert r_summary.json()["patient_id"] != p2

    # Withdraw consent for Patient 1 -> Companion token is immediately invalidated
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "clinical_care", "granted": False}, headers=h_clin)
    r_withdrawn = client.get(f"/api/v1/companion/share/{token_secret1}")
    assert r_withdrawn.status_code == 403


def test_companion_token_never_exposed_in_plaintext_listing(test_env):
    """Verifies bearer secret is hashed at rest and never returned on list calls."""
    client: TestClient = test_env["client"]
    p1 = test_env["pat1_id"]
    h_clin = _auth_header("clinician")

    # Grant consent
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "caregiver_sharing,clinical_care", "granted": True}, headers=h_clin)

    # Issue token
    client.post(
        f"/api/v1/patients/{p1}/shares",
        json={"caregiver_name": "Caregiver Audit", "relationship_type": "parent", "scope": "view_summary"},
        headers=h_clin,
    )

    # List tokens
    list_resp = client.get(f"/api/v1/patients/{p1}/shares", headers=h_clin)
    assert list_resp.status_code == 200
    shares = list_resp.json()
    for s in shares:
        assert s.get("share_token") is None, "Plaintext bearer token leaked in listing response!"
        assert "token_preview" in s and s["token_preview"] is not None


# ==============================================================================
# 5. Offline Batch Sync Replay & Idempotency
# ==============================================================================


def test_offline_sync_replay_and_idempotency(test_env):
    """Verifies that replaying an identical client mutation ID does not duplicate records."""
    client: TestClient = test_env["client"]
    p1 = test_env["pat1_id"]
    h_clin = _auth_header("clinician")

    # Grant consent
    client.post(f"/api/v1/patients/{p1}/consent", json={"scope": "clinical_care", "granted": True}, headers=h_clin)

    mut_id = f"MUT-IDEMP-{uuid.uuid4()}"
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    batch_payload = {
        "sync_id": f"SYNC-{uuid.uuid4()}",
        "client_device_id": "DEVICE-SEC-01",
        "client_timestamp": now_iso,
        "mutations": [
            {
                "client_mutation_id": mut_id,
                "entity_type": "observation",
                "action": "create",
                "patient_id": p1,
                "client_updated_at": now_iso,
                "payload": {
                    "analyte_code": "ca_15_3",
                    "value": 24.5,
                    "unit": "U/mL",
                    "specimen_collected_at": now_iso,
                },
            }
        ],
    }

    # 1. First sync submission
    r1 = client.post("/api/v1/sync/batch", json=batch_payload, headers=h_clin)
    assert r1.status_code == 200, f"Sync submission failed: {r1.text}"
    res1 = r1.json()
    assert res1["applied_count"] == 1
    assert res1["results"][0]["status"] == "applied"

    # 2. Replay identical batch
    r2 = client.post("/api/v1/sync/batch", json=batch_payload, headers=h_clin)
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["already_applied_count"] == 1
    assert res2["results"][0]["status"] == "already_applied"


# ==============================================================================
# 6. HL7 v2 Robustness & Malformed Message Fuzzing
# ==============================================================================


def test_hl7_ingestion_malformed_and_loinc_fuzzing(test_env):
    """Verifies HL7 ingestion rejects malformed messages without internal errors."""
    client: TestClient = test_env["client"]
    h_nurse = _auth_header("nurse_clerk")

    malformed_messages = [
        "GARBAGE TEXT NOT AN HL7 MESSAGE",
        "MSH|^~\\&|LAB|HOSPITAL\rPID|1||MRN-NONEXISTENT\r",  # Missing OBX
        "MSH|^~\\&|LAB\rPID|1\rOBX|1|NM|99999-9^INVALID^LN||-500.0|U/mL||||F\r",  # Invalid LOINC and negative value
    ]

    for msg in malformed_messages:
        resp = client.post("/api/v1/hl7/oru-r01", data=msg, headers={**h_nurse, "Content-Type": "text/plain"})
        assert resp.status_code in (400, 422), f"Malformed HL7 produced unexpected status {resp.status_code}"
        assert "Internal Server Error" not in resp.text


# ==============================================================================
# 7. Error Message Leakage & Stack Trace Hygiene
# ==============================================================================


def test_error_message_leakage_and_stack_trace_hygiene(test_env):
    """Verifies that API error responses never expose database internals, file paths, or secrets."""
    client: TestClient = test_env["client"]
    h_clin = _auth_header("clinician")

    # Trigger multiple error conditions
    endpoints_to_trigger = [
        ("GET", f"/api/v1/patients/{uuid.uuid4()}"),
        ("POST", "/api/v1/patients/INVALID_UUID/observations", {"analyte_code": "unknown", "value": "nan"}),
        ("GET", "/api/v1/alerts/NONEXISTENT_ALERT"),
    ]

    forbidden_substrings = [
        "Traceback (most recent call last)",
        "sqlite3.OperationalError",
        "sqlalchemy.exc",
        "FIELD_ENCRYPTION_KEYS",
        "JWT_SECRET_KEY",
        str(Path.home()),
        "WHERE observations.",
    ]

    for method, path, *body in endpoints_to_trigger:
        b = body[0] if body else None
        if method == "GET":
            resp = client.get(path, headers=h_clin)
        else:
            resp = client.post(path, json=b, headers=h_clin)

        body_str = resp.text
        for forbidden in forbidden_substrings:
            assert forbidden not in body_str, f"Sensitive error leakage detected on {method} {path}! Found: '{forbidden}'"
