"""Shared HTTP fixtures for the silent-mode and route-policy suites.

Everything that matters for security is exercised over HTTP with signed bearer tokens. Seed data (a facility)
is written once; patients and consents are created through the API like any client would.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vigil_api import shadow_store
from vigil_api.auth import create_access_token
from vigil_api.config import settings
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import Facility, UserRole

ALL_ROLES = [r.value for r in UserRole]
CLINICAL_WRITERS = ["clinician", "nurse_clerk", "admin"]


@dataclass
class ApiEnv:
    client: TestClient
    engine: object
    shadow_url: str

    def headers(self, role: str, subject: Optional[str] = None, patient_id: Optional[str] = None) -> Dict[str, str]:
        token = create_access_token(subject=subject or f"usr-{role}", role=role, patient_id=patient_id)
        return {"Authorization": f"Bearer {token}"}

    def create_patient(self, mrn: str, consent: bool = True) -> str:
        res = self.client.post(
            "/api/v1/patients/", json={"age": 52, "mrn": mrn}, headers=self.headers("admin")
        )
        assert res.status_code == 201, res.text
        pid = res.json()["id"]
        if consent:
            c = self.client.post(
                f"/api/v1/patients/{pid}/consent",
                json={"consent_type": "surveillance_monitoring", "granted": True, "scope": "full"},
                headers=self.headers("admin"),
            )
            assert c.status_code == 201, c.text
        return pid


@pytest.fixture
def api_env(tmp_path, monkeypatch):
    """Isolated clinical database, a separate shadow database, strict authentication."""
    db_url = f"sqlite:///{tmp_path / 'clinical.db'}"
    shadow_url = f"sqlite:///{tmp_path / 'shadow.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
    monkeypatch.setattr(settings, "DATABASE_URL", db_url)
    monkeypatch.setattr(settings, "SILENT_MODE", False)
    monkeypatch.setattr(settings, "SILENT_SHADOW_DATABASE_URL", shadow_url)
    with Session(engine) as session:
        session.add(
            Facility(
                id="fac-01", name="Oncology Center", code="ONC-01", country="NG", tier="tertiary",
                active=True, created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    with TestClient(app) as client:
        yield ApiEnv(client=client, engine=engine, shadow_url=shadow_url)
    app.dependency_overrides.clear()
    shadow_store.reset_stores()
    engine.dispose()
