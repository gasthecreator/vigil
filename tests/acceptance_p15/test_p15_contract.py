"""Overseer-authored acceptance test for the triage consent defect. DO NOT EDIT.

Run with VIGIL_ACCEPT_P15=1. The triage queue is a patient-data read: patients without active consent
(never granted, withdrawn, or expired) must not appear in it for any role.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P15") != "1":
    pytest.skip("set VIGIL_ACCEPT_P15=1 to run the triage consent test", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

CODE = """
import json
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
H = {"X-Vigil-Role": "clinician"}
roles = {"clinician": H, "nurse_clerk": {"X-Vigil-Role": "nurse_clerk"}, "quality_lead": {"X-Vigil-Role": "quality_lead"}, "admin": {"X-Vigil-Role": "admin"}}
def mk(mrn, consent):
    p = c.post("/api/v1/patients/", json={"age": 55, "status": "active", "mrn": mrn}, headers=H).json()["id"]
    if consent:
        c.post(f"/api/v1/patients/{p}/consent", json={"scope": "full", "granted": True}, headers=H)
    return p
A, B = mk("A", True), mk("B", False)
ids = lambda role: sorted(x["patient_id"] for x in c.get("/api/v1/patients/triage", headers=roles[role]).json())
before = {r: ids(r) for r in roles}
c.post(f"/api/v1/patients/{A}/consent", json={"scope": "full", "granted": False}, headers=H)
after = {r: ids(r) for r in roles}
c.post(f"/api/v1/patients/{A}/consent", json={"scope": "full", "granted": True}, headers=H)
regranted = {r: ids(r) for r in roles}
print(json.dumps({"A": A, "B": B, "before": before, "after": after, "regranted": regranted}))
"""


def test_triage_queue_respects_consent_for_every_role(tmp_path):
    e = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'api.db'}"}
    p = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(CODE)],
        capture_output=True,
        text=True,
        env=e,
        cwd=ROOT,
        timeout=300,
    )
    assert p.returncode == 0, p.stderr[-800:]
    r = json.loads(p.stdout.strip().splitlines()[-1])
    for role in ("clinician", "nurse_clerk", "quality_lead", "admin"):
        assert r["B"] not in r["before"][role], f"{role}: unconsented patient listed in triage"
        assert r["A"] in r["before"][role], f"{role}: consented patient missing from triage"
        assert r["A"] not in r["after"][role], f"{role}: withdrawn patient still in triage"
        assert r["A"] in r["regranted"][role], f"{role}: re-granted patient missing from triage"
