"""Shared HTTP fixtures for the silent-mode and route-policy suites.

Everything that matters for security is exercised over HTTP with signed bearer tokens. Seed data (a facility)
is written once; patients and consents are created through the API like any client would.
"""

from __future__ import annotations

import os
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


def _test_db_urls(tmp_path) -> tuple[str, str, dict]:
    """Prefer Postgres when VIGIL_POSTGRES_TEST_URL is set (G-02); else isolated SQLite files."""
    pg = os.environ.get("VIGIL_POSTGRES_TEST_URL", "")
    if pg.startswith("postgresql"):
        suffix = tmp_path.name.replace("-", "")[:8]
        clinical = f"{pg}{_url_sep(pg)}options=-csearch_path%3Dvigil_t_{suffix}"
        shadow = f"{pg}{_url_sep(pg)}options=-csearch_path%3Dvigil_s_{suffix}"
        return clinical, shadow, {}
    return (
        f"sqlite:///{tmp_path / 'clinical.db'}",
        f"sqlite:///{tmp_path / 'shadow.db'}",
        {"check_same_thread": False},
    )


def _url_sep(url: str) -> str:
    return "&" if "?" in url else "?"


@pytest.fixture
def api_env(tmp_path, monkeypatch):
    """Isolated clinical database, a separate shadow database, strict authentication."""
    db_url, shadow_url, connect_args = _test_db_urls(tmp_path)
    if db_url.startswith("postgresql"):
        from sqlalchemy import text as sa_text

        admin = create_engine(os.environ["VIGIL_POSTGRES_TEST_URL"])
        schema_c = f"vigil_t_{tmp_path.name.replace('-', '')[:8]}"
        schema_s = f"vigil_s_{tmp_path.name.replace('-', '')[:8]}"
        with admin.begin() as conn:
            conn.execute(sa_text(f"DROP SCHEMA IF EXISTS {schema_c} CASCADE"))
            conn.execute(sa_text(f"DROP SCHEMA IF EXISTS {schema_s} CASCADE"))
            conn.execute(sa_text(f"CREATE SCHEMA {schema_c}"))
            conn.execute(sa_text(f"CREATE SCHEMA {schema_s}"))
        admin.dispose()

    engine = create_engine(db_url, connect_args=connect_args)
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
