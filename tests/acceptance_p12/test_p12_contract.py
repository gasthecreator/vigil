"""Overseer-authored acceptance tests for Phase 12 remediation. DO NOT EDIT.

Run with VIGIL_ACCEPT_P12=1. Encodes defects reproduced against the Phase 7a PR (docs/progress/VERDICT-P7A.md):
continuity listings ignore consent, and /schedule/confirm trusts client-supplied ledger values.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P12") != "1":
    pytest.skip("set VIGIL_ACCEPT_P12=1 to run Phase 12 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

PRELUDE = """
import json
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
H = {"X-Vigil-Role": "clinician"}; N = {"X-Vigil-Role": "nurse_clerk"}; Q = {"X-Vigil-Role": "quality_lead"}
def patient(mrn, consent):
    p = c.post("/api/v1/patients/", json={"age": 55, "status": "active", "mrn": mrn}, headers=H).json()["id"]
    if consent:
        c.post(f"/api/v1/patients/{p}/consent", json={"scope": "full", "granted": True}, headers=H)
    return p
def course(p):
    return c.post("/api/v1/continuity/courses", json={"patient_id": p, "clinical_context": "curative_tnbc",
        "total_fractions": 15, "prescribed_start_date": "2026-10-01T00:00:00+00:00"}, headers=H).json()["id"]
def machine_id():
    ms = c.get("/api/v1/continuity/machines", headers=H).json()
    return ms[0]["id"]
def asg(cid, pid, machine, harm=0.0, delay=0):
    return {"course_id": cid, "patient_id": pid, "machine_id": machine, "start_day": 0,
            "scheduled_date": "2026-10-20T00:00:00+00:00", "fractions": 15, "context": "curative_tnbc",
            "delay_days": delay, "marginal_harm": harm, "explanation": "x", "is_moved": True}
"""


def run(body: str, tmp_path: Path) -> dict:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    code = PRELUDE + textwrap.dedent(body) + "\n"
    e = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'api.db'}",
        "VIGIL_FIELD_ENCRYPTION_KEYS": key,
        "FIELD_ENCRYPTION_KEYS": key,
        "ENCRYPTION_KEY": key,
    }
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=ROOT, timeout=300
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_course_and_ledger_listings_respect_consent(tmp_path):
    body = """
    A = patient("A", True); cid = course(A)
    c.post("/api/v1/continuity/schedule/solve", json={}, headers=H)  # may be a no-op; ensures machines exist
    m = machine_id()
    c.post("/api/v1/continuity/schedule/confirm", json={"assignments": [asg(cid, A, m)], "reason": "ok"}, headers=H)
    before = {"courses": len(c.get("/api/v1/continuity/courses", headers=N).json()),
              "ledger": len(c.get("/api/v1/continuity/ledger", headers=Q).json())}
    c.post(f"/api/v1/patients/{A}/consent", json={"scope": "full", "granted": False}, headers=H)
    after = {"courses": len(c.get("/api/v1/continuity/courses", headers=N).json()),
             "ledger": len(c.get("/api/v1/continuity/ledger", headers=Q).json())}
    print(json.dumps({"before": before, "after": after}))
    """
    r = run(body, tmp_path)
    assert r["before"]["courses"] >= 1 and r["before"]["ledger"] >= 1, r
    assert r["after"] == {"courses": 0, "ledger": 0}, f"data listed after consent withdrawn: {r}"


def test_schedule_confirm_derives_ledger_values_on_the_server(tmp_path):
    body = """
    A = patient("A", True); B = patient("B", False); cid = course(A)
    c.post("/api/v1/continuity/schedule/solve", json={}, headers=H)
    m = machine_id()
    wrong_patient = c.post("/api/v1/continuity/schedule/confirm", json={"assignments": [asg(cid, B, m, 999.0, -5)], "reason": "x"}, headers=H).status_code
    bad_machine = c.post("/api/v1/continuity/schedule/confirm", json={"assignments": [asg(cid, A, "NOPE")], "reason": "x"}, headers=H).status_code
    unknown = c.post("/api/v1/continuity/schedule/confirm", json={"assignments": [asg("nonexistent", A, m)], "reason": "x"}, headers=H).status_code
    dup = c.post("/api/v1/continuity/schedule/confirm", json={"assignments": [asg(cid, A, m), asg(cid, A, m)], "reason": "x"}, headers=H).status_code
    ledger_after_bad = len(c.get("/api/v1/continuity/ledger", headers=Q).json())
    ok = c.post("/api/v1/continuity/schedule/confirm", json={"assignments": [asg(cid, A, m, 999.0, -5)], "reason": "x"}, headers=H).status_code
    led = c.get("/api/v1/continuity/ledger", headers=Q).json()
    print(json.dumps({"wrong_patient": wrong_patient, "bad_machine": bad_machine, "unknown": unknown, "dup": dup,
                      "ledger_after_bad": ledger_after_bad, "ok": ok,
                      "entry": [(e["delay_days"], e["marginal_harm"]) for e in led]}))
    """
    r = run(body, tmp_path)
    for k in ("wrong_patient", "bad_machine", "unknown", "dup"):
        assert 400 <= r[k] < 500, f"{k} accepted: {r}"
    assert r["ledger_after_bad"] == 0, "rejected requests still wrote ledger entries (not atomic)"
    assert r["ok"] == 200
    (delay, harm) = r["entry"][0]
    assert delay == 19 and harm < 100, f"ledger kept client-supplied values: {r['entry']}"


def test_consent_withdrawal_over_http_revokes_access_and_regrant_restores_it(tmp_path):
    """Withdrawing consent through the API (granted=false, or a record with withdrawn_at) must end access;
    a later grant must restore it. Earlier 'withdrawn' tests edited the database directly."""
    body = """
    p = patient("A", False)
    read = lambda: c.get(f"/api/v1/patients/{p}/observations", headers=H).status_code
    seq = {"none": read()}
    c.post(f"/api/v1/patients/{p}/consent", json={"scope": "full", "granted": True}, headers=H); seq["granted"] = read()
    c.post(f"/api/v1/patients/{p}/consent", json={"scope": "full", "granted": False}, headers=H); seq["withdrawn"] = read()
    c.post(f"/api/v1/patients/{p}/consent", json={"scope": "full", "granted": True}, headers=H); seq["regranted"] = read()
    c.post(f"/api/v1/patients/{p}/consent", json={"scope": "full", "granted": True, "withdrawn_at": "2026-10-17T00:00:00+00:00"}, headers=H); seq["withdrawn_at"] = read()
    print(json.dumps(seq))
    """
    r = run(body, tmp_path)
    assert r == {
        "none": 403,
        "granted": 200,
        "withdrawn": 403,
        "regranted": 200,
        "withdrawn_at": 403,
    }, r
