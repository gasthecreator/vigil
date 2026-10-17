"""Overseer-authored acceptance tests for Phase 7 remediation. DO NOT EDIT.

Run with VIGIL_ACCEPT_P7=1. They encode defects the overseer reproduced against the Phase 5b PR
(see docs/progress/VERDICT-P5B.md): an unmeasured-value leak in the observation export, an audit
anchor that lives in the database it protects, and a raw CSV upload path that returns 422.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("VIGIL_ACCEPT_P7") != "1":
    pytest.skip("set VIGIL_ACCEPT_P7=1 to run Phase 7 acceptance tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]

PRELUDE = """
import json, os, sqlite3, datetime as dt, sys
from fastapi.testclient import TestClient
from vigil_api.main import app
from vigil_api.database import Base, engine
import vigil_api.models.v2, vigil_api.models.patient
Base.metadata.create_all(bind=engine)
c = TestClient(app, raise_server_exceptions=False)
H = {"X-Vigil-Role": "clinician"}; A = {"X-Vigil-Role": "admin"}
DB = os.environ["DATABASE_URL"].replace("sqlite:///", "")
pid = c.post("/api/v1/patients/", json={"age": 55, "status": "active"}, headers=H).json()["id"]
c.post(f"/api/v1/patients/{pid}/consent", json={"scope": "clinical_care", "granted": True}, headers=H)
"""


def run(body: str, tmp_path: Path, **env) -> dict:
    code = PRELUDE + textwrap.dedent(body) + "\n"
    e = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'api.db'}", **env}
    p = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=e, cwd=ROOT, timeout=300
    )
    out = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "{}"
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(out)


@pytest.mark.parametrize("gen", ["G1_SMOOTH", "G2_BURST", "G3_NOISE"])
def test_unobserved_values_are_never_exported(gen):
    """RR-new: a value flagged `observed_<analyte>` == False must be NaN in the observation export.
    Latent truth may only appear under a `latent_` prefix and must never be a model input."""
    from vigil_sim.generators import GeneratorType, get_generator

    names = {m.name: m for m in GeneratorType}
    if gen not in names:
        pytest.skip(f"{gen} not in this build")
    cohort = get_generator(names[gen], seed=3).generate_cohort(120, duration_days=730.0)
    df = cohort.to_observations_dataframe()
    masks = [c for c in df.columns if c.startswith("observed_")]
    assert masks, "no observed_* mask columns found"
    checked = 0
    for m in masks:
        col = m[len("observed_") :]
        if col not in df.columns:
            continue
        unobs = ~df[m].astype(bool)
        checked += int(unobs.sum())
        leaked = int(df.loc[unobs, col].notna().sum())
        assert leaked == 0, f"{leaked} unmeasured values leaked in `{col}` ({gen})"
    assert checked > 0, "fixture never exercised an unobserved row"


def test_feature_matrix_is_invariant_to_latent_columns():
    """Features must not change when `latent_*` columns are scrambled."""
    from vigil_sim.generators import GeneratorType, get_generator

    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=4).generate_cohort(80, duration_days=730.0)
    df = cohort.to_observations_dataframe()
    latent = [c for c in df.columns if c.startswith("latent_")]
    if not latent:
        return  # nothing to scramble: acceptable
    import importlib

    feats = importlib.import_module("vigil_ml.features")
    build = getattr(feats, "build_landmark_features", None) or getattr(feats, "build_features")
    rng = np.random.default_rng(0)
    scrambled = df.copy()
    for c in latent:
        scrambled[c] = rng.permutation(scrambled[c].to_numpy())
    pts = cohort.to_patients_dataframe()
    a = build(df, pts, 365.0) if build.__code__.co_argcount >= 3 else build(df, 365.0)
    b = build(scrambled, pts, 365.0) if build.__code__.co_argcount >= 3 else build(scrambled, 365.0)
    a = a[0] if isinstance(a, tuple) else a
    b = b[0] if isinstance(b, tuple) else b
    assert a.equals(b), "features depend on latent_* columns"


def test_audit_tail_deletion_is_detected_even_if_the_whole_database_is_rewritten(tmp_path):
    """The audit head must be anchored OUTSIDE the database it protects. With
    VIGIL_AUDIT_ANCHOR_PATH set, anchors are appended to that file; an attacker who deletes the last
    audit rows and rewrites every table in the DB (including any anchor table) must still be caught."""
    anchor = tmp_path / "anchor.log"
    body = """
    for i in range(4):
        c.post(f"/api/v1/patients/{pid}/observations", json={"analyte_code": "ca_15_3", "value": 18.0 + i, "unit": "U/mL",
               "specimen_collected_at": f"2026-0{i+1}-01T00:00:00+00:00"}, headers=H)
    before = c.get("/api/v1/audit/verify", headers=A).json()
    con = sqlite3.connect(DB); cur = con.cursor()
    ids = [r[0] for r in cur.execute("select id from audit_events order by rowid")]
    head = cur.execute("select curr_hash from audit_events where id=?", (ids[-3],)).fetchone()[0]
    cur.execute("delete from audit_events where id in (?,?)", (ids[-1], ids[-2]))
    for (t,) in cur.execute("select name from sqlite_master where type='table' and name like '%anchor%'").fetchall():
        cols = [r[1] for r in cur.execute(f"pragma table_info({t})")]
        if "head_hash" in cols: cur.execute(f"update {t} set head_hash=?", (head,))
        if "total_events" in cols: cur.execute(f"update {t} set total_events=?", (len(ids) - 2,))
    con.commit(); con.close()
    after = c.get("/api/v1/audit/verify", headers=A).json()
    print(json.dumps({"before_valid": before.get("valid"), "after_valid": after.get("valid")}))
    """
    r = run(body, tmp_path, VIGIL_AUDIT_ANCHOR_PATH=str(anchor))
    assert r["before_valid"] is True
    assert anchor.exists() and anchor.stat().st_size > 0, "no external anchor was written"
    assert r["after_valid"] is False, "tail deletion + DB rewrite went undetected"


def test_raw_csv_body_upload_is_accepted(tmp_path):
    """The documented raw `text/csv` upload must work, not return 422."""
    body = """
    csv = ("patient_id,analyte_code,value,unit,specimen_collected_at\\n"
           f"{pid},ca_15_3,20.0,U/mL,2026-06-01T00:00:00+00:00\\n"
           f"{pid},ca_15_3,abc,U/mL,2026-06-02T00:00:00+00:00\\n")
    r = c.post("/api/v1/observations/batch-import", content=csv.encode(), headers={**H, "content-type": "text/csv"})
    b = r.json() if r.status_code == 200 else {}
    print(json.dumps({"status": r.status_code, "imported": b.get("imported_count"), "rejected": b.get("rejected_count")}))
    """
    r = run(body, tmp_path)
    assert r["status"] == 200, f"raw CSV upload returned {r['status']}"
    assert r["imported"] == 1 and r["rejected"] == 1
