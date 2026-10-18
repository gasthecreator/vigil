"""tests/resilience/test_audit_hash_compat.py

P15-G / ADR-0020: audit chains and backups written with the OLD hash input still verify.

The golden fixture (tests/resilience/fixtures/audit_chain_v0_golden.json) is produced by
scripts/generate_audit_compat_fixture.py, which extracts the pre-Phase-8b
``calculate_audit_hash`` from git history and runs it. No hash in the fixture comes from the
current implementation.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from backup_restore import (  # noqa: E402
    compute_sha256,
    restore_backup,
    verify_backup_integrity,
    verify_restored_audit_chain,
)
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from vigil_api.audit import verify_audit_chain  # noqa: E402
from vigil_api.database import Base  # noqa: E402
from vigil_api.models.v2 import (  # noqa: E402
    AUDIT_HASH_SCHEME_V0,
    AUDIT_HASH_SCHEME_V1,
    AuditEvent,
    audit_hash_candidates,
    calculate_audit_hash,
)

FIXTURE = json.loads((ROOT / "tests" / "resilience" / "fixtures" / "audit_chain_v0_golden.json").read_text())
CHAIN_A = FIXTURE["chain_written_from_datetime"]
CHAIN_B = FIXTURE["chain_hashed_from_raw_string"]


def _args(row, ts):
    return dict(
        prev_hash=row["prev_hash"],
        timestamp=ts,
        actor_id=row["actor_id"],
        actor_role=row["actor_role"],
        action=row["action"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        details=row["details"],
    )


def test_fixture_comes_from_the_old_function_in_history():
    assert FIXTURE["old_function_commit"] == "9709295"
    assert len(CHAIN_A) == 12 and len(CHAIN_B) == 8
    assert {r["input_kind"] for r in CHAIN_A} == {"aware", "naive"}  # both old input kinds covered


@pytest.mark.parametrize("row", CHAIN_A, ids=lambda r: r["id"])
def test_new_hash_equals_old_hash_for_datetime_inputs(row):
    """Production write path: datetime in, identical digest out (no change for existing data)."""
    ts = datetime.fromisoformat(row["timestamp_iso_utc"])
    assert calculate_audit_hash(**_args(row, ts)) == row["curr_hash"]
    # naive datetime (SQLAlchemy/SQLite read-back) is taken as UTC
    assert calculate_audit_hash(**_args(row, ts.replace(tzinfo=None))) == row["curr_hash"]
    # string forms returned by raw SQLite and by the JSONL ledger normalise to the same digest
    assert calculate_audit_hash(**_args(row, row["timestamp_sqlite"])) == row["curr_hash"]
    assert calculate_audit_hash(**_args(row, row["timestamp_iso_utc"])) == row["curr_hash"]


@pytest.mark.parametrize("row", CHAIN_B, ids=lambda r: r["id"])
def test_rows_hashed_by_old_code_from_raw_string_verify_as_v0(row):
    cand = audit_hash_candidates(**_args(row, row["timestamp_sqlite"]))
    assert row["curr_hash"] in cand.values()
    assert [s for s, d in cand.items() if d == row["curr_hash"]] == [AUDIT_HASH_SCHEME_V0]
    # the v1 digest differs, so v0 acceptance is a real, separate code path
    assert cand[AUDIT_HASH_SCHEME_V1] != row["curr_hash"]


def _new_db(path: Path):
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)


def _insert_chain_a_via_orm(session):
    for r in CHAIN_A:
        session.add(
            AuditEvent(
                id=r["id"],
                timestamp=datetime.fromisoformat(r["timestamp_iso_utc"]),
                actor_id=r["actor_id"],
                actor_role=r["actor_role"],
                action=r["action"],
                resource_type=r["resource_type"],
                resource_id=r["resource_id"],
                details=r["details"],
                prev_hash=r["prev_hash"],
                curr_hash=r["curr_hash"],
            )
        )
    session.commit()


def _insert_chain_raw(db_path: Path, rows):
    conn = sqlite3.connect(db_path)
    for r in rows:
        conn.execute(
            "INSERT INTO audit_events (id, timestamp, actor_id, actor_role, action, resource_type, "
            "resource_id, details, prev_hash, curr_hash) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                r["id"], r["timestamp_sqlite"], r["actor_id"], r["actor_role"], r["action"],
                r["resource_type"], r["resource_id"], json.dumps(r["details"]), r["prev_hash"], r["curr_hash"],
            ),
        )
    conn.commit()
    conn.close()


def test_old_chain_verifies_through_the_production_verifier(tmp_path):
    _, S = _new_db(tmp_path / "a.db")
    with S() as s:
        _insert_chain_a_via_orm(s)
        res = verify_audit_chain(s)
    assert res["valid"] is True, res
    assert res["verified_events"] == 12
    assert res["hash_schemes"] == {AUDIT_HASH_SCHEME_V1: 12}


def test_tampering_with_an_old_chain_is_still_detected(tmp_path):
    _, S = _new_db(tmp_path / "a.db")
    with S() as s:
        _insert_chain_a_via_orm(s)
        ev = s.get(AuditEvent, "EVT-A-004")
        ev.details = {**ev.details, "forged": True}
        s.commit()
        res = verify_audit_chain(s)
    assert res["valid"] is False and res["tampered_event_id"] == "EVT-A-004"

    # one microsecond of timestamp change is also detected
    _, S2 = _new_db(tmp_path / "b.db")
    with S2() as s:
        _insert_chain_a_via_orm(s)
        ev = s.get(AuditEvent, "EVT-A-007")
        ev.timestamp = ev.timestamp.replace(microsecond=(ev.timestamp.microsecond + 1) % 1_000_000)
        s.commit()
        assert verify_audit_chain(s)["valid"] is False


def _make_old_format_backup(tmp_path: Path, rows, via_orm: bool) -> Path:
    """Build a backup package exactly like create_backup() of release rc.1 produced it."""
    db = tmp_path / "src" / "database.db"
    db.parent.mkdir(parents=True)
    _, S = _new_db(db)
    if via_orm:
        with S() as s:
            _insert_chain_a_via_orm(s)
    else:
        _insert_chain_raw(db, rows)
    folder = tmp_path / "backup_20260301_090000"
    folder.mkdir()
    shutil.copy2(db, folder / "database.db")
    conn = sqlite3.connect(folder / "database.db")
    ledger = []
    for row in conn.execute(
        "SELECT id, timestamp, actor_id, actor_role, action, resource_type, resource_id, details, prev_hash, curr_hash "
        "FROM audit_events ORDER BY timestamp ASC, rowid ASC"
    ):
        ledger.append(
            {
                "id": row[0], "timestamp": row[1], "actor_id": row[2], "actor_role": row[3],
                "action": row[4], "resource_type": row[5], "resource_id": row[6],
                "details": json.loads(row[7]) if isinstance(row[7], str) else row[7],
                "prev_hash": row[8], "curr_hash": row[9],
            }
        )
    conn.close()
    (folder / "audit_ledger.jsonl").write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in ledger), encoding="utf-8"
    )
    manifest = {
        "timestamp_utc": datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc).isoformat(),
        "database_sha256": compute_sha256(folder / "database.db"),
        "audit_ledger_sha256": compute_sha256(folder / "audit_ledger.jsonl"),
        "audit_chain_head": ledger[-1]["curr_hash"],
        "total_audit_events": len(ledger),
        "vigil_version": "1.0.0-rc.1",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder


@pytest.mark.parametrize("via_orm,rows,label", [(True, None, "datetime-hashed"), (False, CHAIN_B, "string-hashed")])
def test_restore_of_old_format_backup_verifies(tmp_path, via_orm, rows, label):
    folder = _make_old_format_backup(tmp_path, rows, via_orm)
    ok, msg = verify_backup_integrity(folder)
    assert ok, msg
    target = tmp_path / "restored" / "vigil.db"
    assert restore_backup(folder, target) is True
    ok, msg = verify_restored_audit_chain(target)
    assert ok, f"{label}: {msg}"
    assert "Verified unbroken chain" in msg


def test_restore_rejects_old_backup_whose_chain_was_forged_with_valid_checksums(tmp_path):
    """An attacker who edits the DB *and* recomputes the manifest still cannot pass chain verification."""
    folder = _make_old_format_backup(tmp_path, None, True)
    conn = sqlite3.connect(folder / "database.db")
    conn.execute("UPDATE audit_events SET action = 'patient.export' WHERE id = 'EVT-A-003'")
    conn.commit()
    conn.close()
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["database_sha256"] = compute_sha256(folder / "database.db")
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_backup_integrity(folder)[0] is True  # checksums were "fixed"
    with pytest.raises(ValueError, match="TamperDetectedError"):
        restore_backup(folder, tmp_path / "restored" / "vigil.db")
