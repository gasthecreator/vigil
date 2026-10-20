"""Overseer-authored acceptance tests for Phase 11 remediation. DO NOT EDIT.

Run with VIGIL_ACCEPT_P11=1. Encodes the bad-news-mode defect reproduced against the Phase 6b PR
(docs/progress/VERDICT-P6B.md): the gate must be enforced by the server, not the browser.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P11") != "1":
    pytest.skip("set VIGIL_ACCEPT_P11=1 to run Phase 11 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

PRELUDE = """
import json, itertools
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
H = {"X-Vigil-Role": "clinician"}; N = {"X-Vigil-Role": "nurse_clerk"}
created = c.post("/api/v1/patients/", json={"age": 55, "status": "active", "mrn": "M1", "synthetic": True}, headers=H).json()
assert created["synthetic"] is True
p = created["id"]
c.post(f"/api/v1/patients/{p}/consent", json={"scope": "full", "granted": True}, headers=H)
def obs(m, v):
    return c.post(f"/api/v1/patients/{p}/observations", json={"analyte_code": "ca_15_3", "value": v, "unit": "U/mL",
                  "specimen_collected_at": f"2026-0{m}-01T00:00:00+00:00"}, headers=H).json()
for m, v in ((1, 18.0), (2, 19.0), (3, 17.5)): obs(m, v)
esc = obs(4, 45.0)["observation_id"]
tok = c.post(f"/api/v1/patients/{p}/shares", json={"caregiver_name": "Aunt", "scope": "view_summary", "expires_in_days": 7}, headers=H).json()["share_token"]
def leaks(r):
    return r.status_code == 200 and "escalate" in r.text.lower()
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


def test_bad_news_is_withheld_by_the_server_until_a_clinician_releases_it(tmp_path):
    """Before release, neither the patient route nor a caregiver token may return an escalate-level explainer.
    Release must be clinician-only, persisted, and applied to both routes afterwards."""
    body = """
    pat_url = f"/api/v1/patients/{p}/observations/{esc}/explainer"
    cg_url = f"/api/v1/companion/share/{tok}/observations/{esc}/explainer"
    before = {"patient": leaks(c.get(pat_url, headers=H)), "caregiver": leaks(c.get(cg_url))}
    nurse = c.post(f"/api/v1/patients/{p}/disclosure/unlock", json={"reason": "nurse attempt"}, headers=N).status_code
    after_nurse = {"patient": leaks(c.get(pat_url, headers=H)), "caregiver": leaks(c.get(cg_url))}
    clin = c.post(f"/api/v1/patients/{p}/disclosure/unlock", json={"reason": "clinician release"}, headers=H).status_code
    after = {"patient": leaks(c.get(pat_url, headers=H)), "caregiver": leaks(c.get(cg_url))}
    print(json.dumps({"before": before, "nurse": nurse, "after_nurse": after_nurse, "clin": clin, "after": after}))
    """
    r = run(body, tmp_path)
    assert not r["before"]["patient"], (
        "escalate explainer returned to the patient route before release"
    )
    assert not r["before"]["caregiver"], (
        "escalate explainer returned to a caregiver token before release"
    )
    assert r["nurse"] in (401, 403), f"non-clinician released bad news: {r['nurse']}"
    assert not any(r["after_nurse"].values()), "nurse 'release' unlocked content"
    assert r["clin"] == 200
    assert r["after"]["patient"] and r["after"]["caregiver"], (
        "release did not persist for both routes"
    )
