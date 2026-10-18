"""Overseer-authored acceptance tests for Phase 13 remediation. DO NOT EDIT.

Run with VIGIL_ACCEPT_P13=1. Encodes defects reproduced against the Phase 7b PR (docs/progress/VERDICT-P7B.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

if os.environ.get("VIGIL_ACCEPT_P13") != "1":
    pytest.skip("set VIGIL_ACCEPT_P13=1 to run Phase 13 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

PRELUDE = """
import json
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
Q = {"X-Vigil-Role": "quality_lead"}
"""


def run(body: str, tmp_path: Path) -> dict:
    code = PRELUDE + textwrap.dedent(body) + "\n"
    e = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'api.db'}"}
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=ROOT, timeout=300
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_quality_audit_never_mixes_synthetic_trajectories_into_facility_data(tmp_path):
    """An audit of an empty facility must report an empty audit, not statistics from fabricated patients."""
    body = """
    default = c.post("/api/v1/quality/audit", json={}, headers=Q).json()
    bench = c.post("/api/v1/quality/audit", json={"include_synthetic_benchmark": True}, headers=Q).json()
    print(json.dumps({"default_patients": default["total_patients_audited"],
                      "bench_patients": bench["total_patients_audited"],
                      "bench_labelled": "synthetic" in bench["narrative_summary"].lower()}))
    """
    r = run(body, tmp_path)
    assert r["default_patients"] == 0, f"empty facility audited {r['default_patients']} patients"
    assert r["bench_patients"] > 0 and r["bench_labelled"], (
        "benchmark must be explicit and labelled synthetic"
    )
