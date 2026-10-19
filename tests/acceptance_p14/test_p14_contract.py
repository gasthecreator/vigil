"""Overseer-authored acceptance test for Phase 14 remediation. DO NOT EDIT.

Run with VIGIL_ACCEPT_P14=1. Enumerates EVERY route in the live OpenAPI schema; with auth required, an
unauthenticated caller must be rejected (401/403) everywhere except an explicit public allowlist. A new route
without authentication therefore fails this test automatically (docs/progress/VERDICT-P8A.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P14") != "1":
    pytest.skip("set VIGIL_ACCEPT_P14=1 to run Phase 14 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

# Public by design: liveness/landing, and bearer-token (share link) routes that authenticate themselves.
PUBLIC_EXACT = {"/", "/health", "/live", "/ready"}  # /metrics is token-gated, so it must reject unauthenticated calls
PUBLIC_PREFIXES = ("/api/v1/companion/share/",)

CODE = """
import json, re
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
bad, total = [], 0
for path, ops in app.openapi()["paths"].items():
    for m in ops:
        if m not in ("get", "post", "put", "patch", "delete"):
            continue
        total += 1
        url = re.sub(r"\\{[^}]+\\}", "dummy-id", path)
        r = c.request(m.upper(), url, json={} if m != "get" else None)
        bad.append([m.upper(), path, r.status_code]) if r.status_code not in (401, 403) else None
print(json.dumps({"total": total, "not_rejected": bad}))
"""


def test_every_route_rejects_unauthenticated_callers_unless_explicitly_public(tmp_path):
    e = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'api.db'}",
        "REQUIRE_AUTH": "true",
        "JWT_SECRET_KEY": "x-test-secret-key-for-enumeration-only-32b",
    }
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
    assert r["total"] >= 40, f"suspiciously few routes enumerated: {r['total']}"
    leaked = [
        (m, path, code)
        for m, path, code in r["not_rejected"]
        if path not in PUBLIC_EXACT and not path.startswith(PUBLIC_PREFIXES)
    ]
    assert not leaked, f"routes reachable without authentication: {leaked}"
