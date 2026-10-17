"""Overseer-authored black-box API acceptance tests for Phase 5a. DO NOT EDIT.

Run with VIGIL_ACCEPT_P5=1. Each test starts the API in a fresh subprocess with a fresh database and
environment, because auth/profile settings are read at import time. These encode defects the overseer
reproduced against the Phase 5a PR; see docs/progress/VERDICT-P5A.md.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P5") != "1":
    pytest.skip(
        "set VIGIL_ACCEPT_P5=1 to run Phase 5a API acceptance tests", allow_module_level=True
    )

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRET = "vigil-precision-oncology-secret-key-32bytes-min"

PRELUDE = """
import json, os, sqlite3, datetime as dt, sys
import jwt
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
DB = os.environ["DATABASE_URL"].replace("sqlite:///", "")
def count(t):
    con = sqlite3.connect(DB); n = con.execute(f"select count(*) from {t}").fetchone()[0]; con.close(); return n
"""


def run(body: str, tmp_path: Path, **env) -> dict:
    code = PRELUDE + textwrap.dedent(body) + "\n"
    e = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'api.db'}", **env}
    for k in ("JWT_SECRET_KEY", "REQUIRE_AUTH", "ENVIRONMENT"):
        if k not in env:
            e.pop(k, None)
    p = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=ROOT, timeout=300
    )
    return {
        "rc": p.returncode,
        "out": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "",
        "err": p.stderr[-600:],
    }


def test_production_rejects_header_claimed_roles(tmp_path):
    """In production a caller must not be able to claim a role with a header and no token."""
    r = run(
        'print(json.dumps(c.get("/api/v1/patients/", headers={"X-Vigil-Role": "admin"}).status_code))',
        tmp_path,
        ENVIRONMENT="production",
    )
    if r["rc"] != 0:  # refusing to boot unsafely is acceptable
        return
    assert json.loads(r["out"]) in (401, 403), (
        f"production accepted a header-claimed admin: {r['out']}"
    )


def test_default_jwt_secret_is_not_accepted_in_production(tmp_path):
    """A token signed with the committed default secret must not authenticate in production."""
    body = f'''
    now = dt.datetime.now(dt.timezone.utc)
    t = jwt.encode({{"sub": "attacker", "role": "admin", "iat": now, "exp": now + dt.timedelta(hours=1)}}, "{DEFAULT_SECRET}", algorithm="HS256")
    print(json.dumps(c.get("/api/v1/audit/events", headers={{"Authorization": "Bearer " + t}}).status_code))
    '''
    r = run(body, tmp_path, ENVIRONMENT="production")
    if r["rc"] != 0:  # refusing to boot with a default secret is the preferred behaviour
        return
    assert json.loads(r["out"]) in (401, 403), f"forged token accepted in production: {r['out']}"


def test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline(tmp_path):
    """A surprising result posted through ANY write path must produce an observation, an alert/follow-up and an audit event
    — or the endpoint must be gone. Posting CA 15-3 = 500 through the legacy /labs route must not be silently accepted."""
    body = """
    H = {"X-Vigil-Role": "clinician"}
    pid = c.post("/api/v1/patients/", json={"age": 55, "status": "active"}, headers=H).json()["id"]
    r = c.post(f"/api/v1/patients/{pid}/labs", json={"date_drawn": "2026-01-01T00:00:00", "alt_level": 30, "ast_level": 30,
               "creatinine": 1.0, "ca_15_3": 500.0, "wbc_count": 6}, headers={"X-Vigil-Role": "nurse_clerk"})
    print(json.dumps({"status": r.status_code, "obs": count("observations"), "alerts": count("alerts"), "tasks": count("follow_up_tasks"), "audit": count("audit_events")}))
    """
    out = json.loads(run(body, tmp_path)["out"])
    removed = out["status"] in (404, 405, 410)
    handled = out["obs"] >= 1 and (out["alerts"] >= 1 or out["tasks"] >= 1) and out["audit"] >= 1
    assert removed or handled, f"legacy /labs accepted a CA 15-3 of 500 and created nothing: {out}"


def test_writes_are_audited(tmp_path):
    """Creating a patient, granting consent, acknowledging an alert and transitioning a follow-up task must each add an audit event."""
    body = """
    H = {"X-Vigil-Role": "clinician"}
    res = {}
    pid = c.post("/api/v1/patients/", json={"age": 55, "status": "active"}, headers=H).json()["id"]
    res["after_create"] = count("audit_events")
    c.post(f"/api/v1/patients/{pid}/consent", json={"scope": "clinical_care", "granted": True}, headers=H)
    res["after_consent"] = count("audit_events")
    t0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    for i, v in enumerate([18.0, 19.0, 17.5, 18.5, 32.0]):
        c.post(f"/api/v1/patients/{pid}/observations", json={"analyte_code": "ca_15_3", "value": v, "unit": "U/mL",
               "specimen_collected_at": (t0 + dt.timedelta(days=30 * i)).isoformat()}, headers=H)
    res["after_obs"] = count("audit_events")
    alerts = c.get("/api/v1/alerts/", headers=H).json()
    if alerts:
        aid = alerts[0]["id"] if isinstance(alerts[0], dict) and "id" in alerts[0] else alerts[0].get("alert_id")
        c.post(f"/api/v1/alerts/{aid}/acknowledge", json={"disposition": "repeat_ordered", "note": "test"}, headers=H)
    res["after_ack"] = count("audit_events")
    print(json.dumps(res))
    """
    r = json.loads(run(body, tmp_path)["out"])
    assert r["after_create"] >= 1, f"patient creation not audited: {r}"
    assert r["after_consent"] > r["after_create"], f"consent grant not audited: {r}"
    assert r["after_ack"] > r["after_obs"], f"alert acknowledgement not audited: {r}"


def test_reads_require_consent_for_every_role(tmp_path):
    """MASTER_PLAN §6.0: every read of patient data is checked against role AND consent, including clinicians."""
    body = """
    H = {"X-Vigil-Role": "clinician"}
    pid = c.post("/api/v1/patients/", json={"age": 55, "status": "active"}, headers=H).json()["id"]
    print(json.dumps(c.get(f"/api/v1/patients/{pid}/observations", headers=H).status_code))
    """
    status = json.loads(run(body, tmp_path)["out"])
    assert status == 403, (
        f"clinician read a patient's observations with no consent on record (status {status})"
    )


def test_passwords_are_hashed_with_a_slow_salted_kdf():
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    from vigil_api.auth import hash_password, verify_password

    a, b = (
        hash_password("correct horse battery staple"),
        hash_password("correct horse battery staple"),
    )
    assert a != b, "same password produced identical hashes (no per-user random salt)"
    assert verify_password("correct horse battery staple", a) and not verify_password("wrong", a)
    assert any(tag in a.lower() for tag in ("argon2", "bcrypt", "scrypt", "pbkdf2")), (
        "hash does not identify a slow KDF"
    )
