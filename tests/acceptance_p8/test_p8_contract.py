"""Overseer-authored acceptance tests for Phase 8 remediation. DO NOT EDIT.

Run with VIGIL_ACCEPT_P8=1. They encode defects reproduced against the Phase 5c PR (docs/progress/VERDICT-P5C.md).
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P8") != "1":
    pytest.skip("set VIGIL_ACCEPT_P8=1 to run Phase 8 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

PRELUDE = """
import json, os
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
H = {"X-Vigil-Role": "clinician"}
"""


def run(body: str, tmp_path: Path, **env) -> dict:
    code = PRELUDE + textwrap.dedent(body) + "\n"
    e = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'api.db'}", **env}
    p = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=ROOT, timeout=300
    )
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_sync_replay_does_not_bypass_consent_or_leak_other_patients(tmp_path):
    """Replaying a known client_mutation_id for a patient WITHOUT consent must not return another patient's
    entity id or adjudication. Idempotency keys must be scoped to (patient, key) and checked after consent."""
    body = """
    def mk():
        return c.post("/api/v1/patients/", json={"age": 55, "status": "active"}, headers=H).json()["id"]
    A, B = mk(), mk()
    c.post(f"/api/v1/patients/{A}/consent", json={"scope": "clinical_care", "granted": True}, headers=H)
    def batch(pid, mid):
        return {"sync_id": "s" + mid, "client_timestamp": "2026-06-01T00:00:00+00:00", "mutations": [{
            "client_mutation_id": mid, "entity_type": "observation", "action": "create", "patient_id": pid,
            "client_updated_at": "2026-06-01T00:00:00+00:00",
            "payload": {"analyte_code": "ca_15_3", "value": 20.0, "unit": "U/mL",
                        "specimen_collected_at": "2026-06-01T00:00:00+00:00"}}]}
    first = c.post("/api/v1/sync/batch", json=batch(A, "m1"), headers=H).json()["results"][0]
    x = c.post("/api/v1/sync/batch", json=batch(B, "m1"), headers=H).json()["results"][0]
    print(json.dumps({"first": first["status"], "other": x["status"], "leaked": x.get("entity_id") == first.get("entity_id")}))
    """
    r = run(body, tmp_path)
    assert r["first"] == "applied"
    assert not r["leaked"], "idempotency replay leaked another patient's entity id without consent"
    assert r["other"] == "rejected", f"no-consent patient got status {r['other']}"


def test_mrn_sent_through_the_api_is_stored_encrypted(tmp_path):
    """A patient identifier submitted via the API must be persisted, readable by an authorised caller,
    and ciphertext in the raw database file."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    body = """
    r = c.post("/api/v1/patients/", json={"age": 55, "status": "active", "mrn": "MRN-SECRET-123"}, headers=H)
    pid = r.json()["id"]
    c.post(f"/api/v1/patients/{pid}/consent", json={"scope": "clinical_care", "granted": True}, headers=H)
    g = c.get(f"/api/v1/patients/{pid}", headers=H)
    print(json.dumps({"pid": pid, "read_back": g.json().get("mrn") if g.status_code == 200 else None}))
    """
    envs = {"VIGIL_FIELD_ENCRYPTION_KEYS": key, "FIELD_ENCRYPTION_KEYS": key, "ENCRYPTION_KEY": key}
    r = run(body, tmp_path, **envs)
    raw = (
        sqlite3.connect(tmp_path / "api.db")
        .execute("select mrn from patients where id=?", (r["pid"],))
        .fetchone()[0]
    )
    assert raw, "MRN submitted through the API was not persisted"
    assert "MRN-SECRET-123" not in str(raw), "MRN stored in plaintext"
    assert r["read_back"] == "MRN-SECRET-123", "authorised read does not return the decrypted MRN"
