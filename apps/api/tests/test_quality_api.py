"""Unit and Integration tests for Missed-Signal Quality Audit API (M10).

Verifies:
- RBAC enforcement: Only quality_lead and admin can access /api/v1/quality/audit
- Forbidden roles: clinician, nurse_clerk, patient, caregiver are rejected with 403 Forbidden
- Unauthenticated requests are rejected with 401 Unauthorized
- Small-cell suppression: Strata with 1 <= n < 5 are masked with "<5" and rates are suppressed
- Strictly neutral register: Narrative summaries contain zero punitive terms
- Cryptographic AuditEvent recording on every audit run
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vigil_ml.quality import FORBIDDEN_PUNITIVE_TERMS, verify_neutral_register

# Setup test environment
os.environ["ENVIRONMENT"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import Facility, User, UserRole


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_quality.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with Session(engine) as session:
        # Facility
        fac = Facility(
            id="FAC-01", name="UCH Ibadan Oncology Center", code="UCH-ONC", tier="tertiary"
        )
        session.add(fac)

        # Users
        quality_lead = User(
            id="USR-QL-01",
            username="quality_lead_chioma",
            email="ql@uch.edu.ng",
            role=UserRole.QUALITY_LEAD.value,
            full_name="Chioma Okeke, MSc Quality Lead",
            facility_id="FAC-01",
            hashed_password="mock",
        )
        admin = User(
            id="USR-ADMIN-01",
            username="admin_sys",
            email="admin@uch.edu.ng",
            role=UserRole.ADMIN.value,
            full_name="Systems Administrator",
            facility_id="FAC-01",
            hashed_password="mock",
        )
        clinician = User(
            id="USR-DR-01",
            username="dr_folashade",
            email="dr@uch.edu.ng",
            role=UserRole.CLINICIAN.value,
            full_name="Dr. Folashade Adebayo",
            facility_id="FAC-01",
            hashed_password="mock",
        )
        nurse = User(
            id="USR-NURSE-01",
            username="nurse_amara",
            email="nurse@uch.edu.ng",
            role=UserRole.NURSE_CLERK.value,
            full_name="Amara Eze, RN",
            facility_id="FAC-01",
            hashed_password="mock",
        )
        patient_user = User(
            id="USR-PAT-01",
            username="patient_ada",
            email="ada@example.com",
            role=UserRole.PATIENT.value,
            full_name="Adaeze Obi",
            hashed_password="mock",
        )
        caregiver_user = User(
            id="USR-CG-01",
            username="caregiver_chidi",
            email="chidi@example.com",
            role=UserRole.CAREGIVER.value,
            full_name="Chidi Obi",
            hashed_password="mock",
        )
        session.add_all([quality_lead, admin, clinician, nurse, patient_user, caregiver_user])
        session.commit()

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_quality_audit_rbac_quality_lead(client):
    """Quality lead can successfully run quality audit and receive 200 OK."""
    headers = {"X-Vigil-Role": "quality_lead", "X-Vigil-User-Id": "USR-QL-01"}
    payload = {
        "facility_id": "FAC-01",
        "lookback_days": 365,
        "n_bootstrap": 200,
        "include_synthetic_benchmark": True,
    }
    response = client.post("/api/v1/quality/audit", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_patients_audited"] >= 1000
    assert data["total_signals_detected"] > 0
    assert data["register_audit_verified"] is True
    assert "narrative_summary" in data


def test_quality_audit_rbac_admin(client):
    """Administrator can successfully run quality audit and receive 200 OK."""
    headers = {"X-Vigil-Role": "admin", "X-Vigil-User-Id": "USR-ADMIN-01"}
    payload = {
        "facility_id": "FAC-01",
        "lookback_days": 180,
        "n_bootstrap": 200,
        "include_synthetic_benchmark": True,
    }
    response = client.post("/api/v1/quality/audit", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_signals_detected"] > 0


@pytest.mark.parametrize(
    "role,user_id",
    [
        ("clinician", "USR-DR-01"),
        ("nurse_clerk", "USR-NURSE-01"),
        ("patient", "USR-PAT-01"),
        ("caregiver", "USR-CG-01"),
    ],
)
def test_quality_audit_rbac_forbidden_roles(client, role, user_id):
    """Non-quality/non-admin roles are rejected with 403 Forbidden."""
    headers = {"X-Vigil-Role": role, "X-Vigil-User-Id": user_id}
    payload = {"facility_id": "FAC-01"}
    response = client.post("/api/v1/quality/audit", json=payload, headers=headers)
    assert response.status_code == 403
    assert "detail" in response.json()


def test_quality_audit_unauthenticated(client, monkeypatch):
    """Unauthenticated request without headers is rejected with 401 when auth is required, or 403 in local default."""
    from vigil_api.config import settings

    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
    response = client.post("/api/v1/quality/audit", json={"facility_id": "FAC-01"})
    assert response.status_code == 401

    monkeypatch.setattr(settings, "REQUIRE_AUTH", False)
    response_fallback = client.post("/api/v1/quality/audit", json={"facility_id": "FAC-01"})
    assert response_fallback.status_code == 403


def test_quality_audit_small_cell_suppression(client):
    """Verifies that small cells (1 <= n < 5) are masked as '<5' with rate=null."""
    headers = {"X-Vigil-Role": "quality_lead", "X-Vigil-User-Id": "USR-QL-01"}
    payload = {
        "facility_id": "FAC-01",
        "lookback_days": 365,
        "n_bootstrap": 100,
        "include_synthetic_benchmark": True,
    }
    response = client.post("/api/v1/quality/audit", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Small cell suppression must be present in the benchmark
    assert data["suppressed_strata_count"] > 0

    all_breakdowns = [
        data["subgroup_breakdown"],
        data["subtype_breakdown"],
        data["stage_breakdown"],
    ]

    found_suppressed = False
    for bd in all_breakdowns:
        for stratum, metric in bd.items():
            if metric["is_suppressed"]:
                found_suppressed = True
                assert metric["total_signals"] == "<5"
                assert metric["action_not_recorded_count"] == "<5"
                assert metric["action_not_recorded_rate"] is None
            else:
                assert isinstance(metric["total_signals"], int)
                assert isinstance(metric["action_not_recorded_count"], int)
                assert isinstance(metric["action_not_recorded_rate"], (int, float))

    assert found_suppressed, "Expected at least one suppressed small cell in benchmark results"


def test_quality_audit_neutral_register(client):
    """Verifies strictly neutral descriptive register and zero punitive terms."""
    headers = {"X-Vigil-Role": "quality_lead", "X-Vigil-User-Id": "USR-QL-01"}
    payload = {"n_bootstrap": 100, "include_synthetic_benchmark": True}
    response = client.post("/api/v1/quality/audit", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    narrative = data["narrative_summary"]
    assert verify_neutral_register(narrative) is True

    # Raw scan for forbidden terms
    narrative_lower = narrative.lower()
    for term in FORBIDDEN_PUNITIVE_TERMS:
        import re

        assert not re.search(
            term, narrative_lower
        ), f"Forbidden punitive term {term} found in narrative: {narrative}"


def test_quality_audit_audit_chain_recording(client):
    """Verifies that executing a quality audit persists a chained AuditEvent."""
    headers = {"X-Vigil-Role": "quality_lead", "X-Vigil-User-Id": "USR-QL-01"}
    payload = {"n_bootstrap": 100, "include_synthetic_benchmark": True}

    response = client.post("/api/v1/quality/audit", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    audit_id = data["audit_id"]

    # Verify audit chain endpoint
    audit_resp = client.get("/api/v1/audit/events", headers=headers)
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    quality_events = [
        e
        for e in events
        if e["action"] == "quality.audit.execute" and e["resource_id"] == audit_id
    ]
    assert len(quality_events) >= 1
    ev = quality_events[0]
    assert ev["actor_id"] == "USR-QL-01"
    assert ev["actor_role"] == "quality_lead"
    assert ev["resource_type"] == "facility_audit"


def test_quality_audit_latest_endpoint(client):
    """Verifies GET /api/v1/quality/audit/latest retrieves audit data for quality_lead."""
    headers = {"X-Vigil-Role": "quality_lead", "X-Vigil-User-Id": "USR-QL-01"}
    response = client.get("/api/v1/quality/audit/latest", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "audit_id" in data
    assert data["total_patients_audited"] > 0

    # Clinician is forbidden
    bad_resp = client.get(
        "/api/v1/quality/audit/latest",
        headers={"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"},
    )
    assert bad_resp.status_code == 403
