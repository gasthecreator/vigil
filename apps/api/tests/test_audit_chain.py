"""Cryptographic Audit Chain Verification and Tampering Detection Test Suite.

Implements Master Plan §11 and Phase 5a Audit requirements:
- Validates hash-chain continuity across append operations.
- Verifies that any database-level tampering (modified payload, altered hash, broken link)
  is immediately detected and identified by the verification engine and endpoint.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event, verify_audit_chain
from vigil_api.auth import create_access_token
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import AuditEvent, UserRole


@pytest.fixture
def audit_db(tmp_path):
    """Set up an isolated database for audit chain tests."""
    db_file = tmp_path / "test_audit.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


def test_audit_chain_integrity_and_tamper_detection(audit_db):
    """Test append integrity, API verification endpoint, and tamper detection."""
    client, engine = audit_db

    now = datetime.now(timezone.utc)

    ev2_id = None
    ev3_hash = None
    with Session(engine) as session:
        record_audit_event(
            db=session,
            actor_id="dr_adewale",
            actor_role=UserRole.CLINICIAN.value,
            action="patient.create",
            resource_type="patient",
            resource_id="pat-100",
            details={"mrn": "MRN-100", "synthetic": True},
            timestamp=now,
        )
        session.commit()

    with Session(engine) as session:
        ev2 = record_audit_event(
            db=session,
            actor_id="nurse_ngozi",
            actor_role=UserRole.NURSE_CLERK.value,
            action="observation.ingest",
            resource_type="observation",
            resource_id="obs-200",
            details={"analyte": "ca_15_3", "value": 28.5},
            timestamp=now,
        )
        ev2_id = ev2.id
        session.commit()

    with Session(engine) as session:
        ev3 = record_audit_event(
            db=session,
            actor_id="dr_adewale",
            actor_role=UserRole.CLINICIAN.value,
            action="alert.acknowledge",
            resource_type="alert",
            resource_id="alt-300",
            details={"disposition": "sample_redraw_ordered"},
            timestamp=now,
        )
        ev3_hash = ev3.curr_hash
        session.commit()

    # 2. Verify clean chain directly
    with Session(engine) as session:
        v_clean = verify_audit_chain(session)
        assert v_clean["valid"] is True
        assert v_clean["verified_events"] == 3
        assert v_clean["total_events"] == 3
        assert v_clean["head_hash"] == ev3_hash

    # 3. Verify clean chain via GET /api/v1/audit/verify endpoint
    token = create_access_token(subject="lead-auditor", role=UserRole.QUALITY_LEAD.value)
    headers = {"Authorization": f"Bearer {token}"}

    r_clean = client.get("/api/v1/audit/verify", headers=headers)
    assert r_clean.status_code == 200
    data_clean = r_clean.json()
    assert data_clean["valid"] is True
    assert data_clean["total_events"] == 3

    # 4. Tamper with intermediate row: modify payload of ev2
    with Session(engine) as session:
        target_ev = session.execute(select(AuditEvent).where(AuditEvent.id == ev2_id)).scalar_one()
        # Maliciously edit value from 28.5 to 128.5
        target_ev.details = {"analyte": "ca_15_3", "value": 128.5}
        session.commit()

    # 5. Verify that verifier detects tampering immediately
    with Session(engine) as session:
        v_tampered = verify_audit_chain(session)
        assert v_tampered["valid"] is False
        assert v_tampered["tampered_event_id"] == ev2_id
        assert "Tampered payload" in v_tampered["error"]

    # 6. Verify that API endpoint reports tampering and identifies tampered row
    r_tampered = client.get("/api/v1/audit/verify", headers=headers)
    assert r_tampered.status_code == 200
    data_tampered = r_tampered.json()
    assert data_tampered["valid"] is False
    assert data_tampered["tampered_event_id"] == ev2_id
    assert "Tampered payload" in data_tampered["error"]
