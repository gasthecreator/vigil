"""Overseer-authored acceptance tests for Phase 9 remediation. DO NOT EDIT.

Run with VIGIL_ACCEPT_P9=1. They encode defects reproduced against the Phase 6a PR (docs/progress/VERDICT-P6A.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P9") != "1":
    pytest.skip("set VIGIL_ACCEPT_P9=1 to run Phase 9 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

PRELUDE = """
import json
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
H = {"X-Vigil-Role": "clinician"}; A = {"X-Vigil-Role": "admin"}
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
    p = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=ROOT, timeout=300
    )
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_identifiers_are_not_returned_without_consent(tmp_path):
    """MRN / external_id are identifiers: listing or searching patients must not expose them (or let a caller
    confirm that an MRN exists) for patients without active consent."""
    body = """
    c.post("/api/v1/patients/", json={"age": 55, "status": "active", "mrn": "MRN-SECRET-777", "external_id": "EXT-555"}, headers=H)
    lst = c.get("/api/v1/patients/", headers=H)
    srch = c.get("/api/v1/patients/", params={"mrn": "MRN-SECRET-777"}, headers=H)
    print(json.dumps({"list": lst.text, "search": srch.text}))
    """
    r = run(body, tmp_path)
    for name in ("list", "search"):
        assert "MRN-SECRET-777" not in r[name] and "EXT-555" not in r[name], (
            f"identifier exposed without consent via {name}"
        )


def test_key_rotation_is_admin_only(tmp_path):
    """Re-encrypting every patient identifier is a global operation: admin only."""
    body = """
    c.post("/api/v1/patients/", json={"age": 55, "status": "active", "mrn": "M1"}, headers=H)
    print(json.dumps({"clinician": c.post("/api/v1/patients/rotate-keys", headers=H).status_code,
                      "admin": c.post("/api/v1/patients/rotate-keys", headers=A).status_code}))
    """
    r = run(body, tmp_path)
    assert r["clinician"] in (401, 403), f"clinician rotated keys: {r['clinician']}"
    assert r["admin"] == 200
