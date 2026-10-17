"""Role × Endpoint × Consent State Matrix Test Suite.

Implements Master Plan §9.2, §11, and Phase 5a Auth/RBAC/Consent verification:
- 6 roles: clinician, nurse_clerk, quality_lead, admin, patient, caregiver (plus unauthenticated).
- 3 consent states: active, revoked, expired.
- Systematic Cartesian product test verifying exact expected status codes on all matrix cells.
- Rejection of unauthenticated data-mutating operations when REQUIRE_AUTH is true.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vigil_api.auth import create_access_token
from vigil_api.config import settings
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import (
    Alert,
    AlertSeverity,
    AlertStatus,
    ConsentRecord,
    Facility,
    Patient,
    RiskAssessment,
    UserRole,
)


@pytest.fixture
def test_env(tmp_path):
    """Set up an isolated database for auth/RBAC matrix tests."""
    db_file = tmp_path / "test_auth.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Create baseline facility and patients
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        fac = Facility(id="fac-01", name="Oncology Center", code="ONC-01", country="NG", tier="tertiary", active=True, created_at=now)
        session.add(fac)

        # Patient 1: Target for consent variations
        p1 = Patient(id="pat-target", facility_id="fac-01", mrn="MRN-TARGET", biological_sex="female", primary_cancer_type="breast", synthetic=True, status="active", created_at=now, updated_at=now)
        # Patient 2: Foreign patient for patient role boundary checks
        p2 = Patient(id="pat-foreign", facility_id="fac-01", mrn="MRN-FOREIGN", biological_sex="female", primary_cancer_type="breast", synthetic=True, status="active", created_at=now, updated_at=now)
        session.add_all([p1, p2])

        # Active consent for foreign patient
        session.add(ConsentRecord(patient_id="pat-foreign", consent_type="surveillance_monitoring", granted=True, granted_at=now, scope="full"))

        # Risk assessment & alert for alert acknowledge tests
        risk = RiskAssessment(
            id="risk-test",
            patient_id="pat-target",
            assessment_date=now,
            model_versions={"M3": "1.0"},
            input_hash="0" * 64,
            score=0.8,
            risk_tier="high",
            abstention=False,
            adjudicated_action="needs_repeat",
            created_at=now,
        )
        session.add(risk)

        alert = Alert(
            id="alert-test",
            patient_id="pat-target",
            risk_assessment_id="risk-test",
            alert_type="lab_error_repeat",
            severity=AlertSeverity.WARNING.value,
            trigger_reason="Needs repeat",
            status=AlertStatus.OPEN.value,
            created_at=now,
        )
        session.add(alert)
        session.commit()

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


def set_patient_consent_state(engine, patient_id: str, state: str):
    """Update consent state for a patient: 'active', 'revoked', or 'expired'."""
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        # Clear existing consent records
        session.query(ConsentRecord).filter(ConsentRecord.patient_id == patient_id).delete()
        if state == "active":
            session.add(ConsentRecord(
                patient_id=patient_id,
                consent_type="surveillance_monitoring",
                granted=True,
                granted_at=now,
                scope="full",
            ))
        elif state == "revoked":
            session.add(ConsentRecord(
                patient_id=patient_id,
                consent_type="surveillance_monitoring",
                granted=True,
                granted_at=now - timedelta(days=5),
                withdrawn_at=now - timedelta(days=1),
                scope="full",
            ))
        elif state == "expired":
            session.add(ConsentRecord(
                patient_id=patient_id,
                consent_type="surveillance_monitoring",
                granted=True,
                granted_at=now - timedelta(days=365),
                expires_at=now - timedelta(days=1),
                scope="full",
            ))
        session.commit()


ROLES = [
    UserRole.CLINICIAN.value,
    UserRole.NURSE_CLERK.value,
    UserRole.QUALITY_LEAD.value,
    UserRole.ADMIN.value,
    UserRole.PATIENT.value,
    UserRole.CAREGIVER.value,
]

CONSENT_STATES = ["active", "revoked", "expired"]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("consent_state", CONSENT_STATES)
def test_role_x_endpoint_x_consent_matrix(test_env, role: str, consent_state: str, monkeypatch):
    """Cartesian product test: Role × Consent State across key API endpoints."""
    client, engine = test_env
    # Enforce strict auth in test
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)

    set_patient_consent_state(engine, "pat-target", consent_state)

    token = create_access_token(
        subject=f"usr-{role}",
        role=role,
        patient_id="pat-target" if role == UserRole.PATIENT.value else None,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. READ PATIENT: GET /api/v1/patients/pat-target
    r_read = client.get("/api/v1/patients/pat-target", headers=headers)
    if consent_state in ("revoked", "expired"):
        # Any patient read must fail with 403 if consent is not active
        assert r_read.status_code == 403, f"Expected 403 on {role} read with {consent_state} consent, got {r_read.status_code}"
    else:
        # Active consent
        assert r_read.status_code == 200, f"Expected 200 on {role} read with active consent, got {r_read.status_code}"

    # 2. INGEST OBSERVATION: POST /api/v1/patients/pat-target/observations
    obs_payload = {
        "analyte_code": "ca_15_3",
        "value": 24.5,
        "unit": "U/mL",
    }
    r_obs = client.post("/api/v1/patients/pat-target/observations", json=obs_payload, headers=headers)
    if consent_state in ("revoked", "expired"):
        assert r_obs.status_code == 403, f"Expected 403 on observation ingest with {consent_state} consent"
    else:
        # Active consent: clinician, nurse_clerk, admin allowed
        if role in (UserRole.CLINICIAN.value, UserRole.NURSE_CLERK.value, UserRole.ADMIN.value):
            assert r_obs.status_code == 201, f"Expected 201 for {role} ingest, got {r_obs.status_code}"
        else:
            assert r_obs.status_code == 403, f"Expected 403 for {role} ingest, got {r_obs.status_code}"

    # 3. ACKNOWLEDGE ALERT: POST /api/v1/alerts/alert-test/acknowledge
    ack_payload = {
        "disposition": "sample_redraw_ordered",
        "rationale_text": "Sample redraw ordered to evaluate pre-analytical spike.",
    }
    r_ack = client.post("/api/v1/alerts/alert-test/acknowledge", json=ack_payload, headers=headers)
    if role in (UserRole.CLINICIAN.value, UserRole.QUALITY_LEAD.value):
        assert r_ack.status_code == 200, f"Expected 200 for {role} alert acknowledge, got {r_ack.status_code}"
    else:
        assert r_ack.status_code == 403, f"Expected 403 for {role} alert acknowledge, got {r_ack.status_code}"

    # 4. VERIFY AUDIT CHAIN: GET /api/v1/audit/verify
    r_audit = client.get("/api/v1/audit/verify", headers=headers)
    if role in (UserRole.QUALITY_LEAD.value, UserRole.ADMIN.value, UserRole.CLINICIAN.value):
        assert r_audit.status_code == 200, f"Expected 200 for {role} audit verify, got {r_audit.status_code}"
    else:
        assert r_audit.status_code == 403, f"Expected 403 for {role} audit verify, got {r_audit.status_code}"


def test_unauthenticated_mutating_endpoints_rejected(test_env, monkeypatch):
    """Verify that unauthenticated data-mutating requests are strictly rejected with 401."""
    client, engine = test_env
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)

    # Observation ingest without auth
    r1 = client.post("/api/v1/patients/pat-target/observations", json={"analyte_code": "ca_15_3", "value": 20.0, "unit": "U/mL"})
    assert r1.status_code == 401

    # Alert acknowledge without auth
    r2 = client.post("/api/v1/alerts/alert-test/acknowledge", json={"disposition": "false_alarm", "rationale_text": "Not verified"})
    assert r2.status_code == 401


def test_patient_role_cannot_read_foreign_records(test_env, monkeypatch):
    """Verify that a patient cannot access another patient's clinical records."""
    client, engine = test_env
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)

    set_patient_consent_state(engine, "pat-target", "active")

    token_pat_target = create_access_token(subject="pat-target", role=UserRole.PATIENT.value)
    headers = {"Authorization": f"Bearer {token_pat_target}"}

    # Reading own record succeeds
    r_own = client.get("/api/v1/patients/pat-target", headers=headers)
    assert r_own.status_code == 200

    # Reading another patient's record is strictly forbidden (HTTP 403)
    r_foreign = client.get("/api/v1/patients/pat-foreign", headers=headers)
    assert r_foreign.status_code == 403
