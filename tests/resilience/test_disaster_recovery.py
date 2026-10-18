"""tests/resilience/test_disaster_recovery.py

Automated Disaster Recovery & Business Continuity Drill.
Enforces Master Plan §6.0, §11.2 (H13), and WP8.4.
Verifies RPO = 0, RTO < 5 seconds, and cryptographic tamper detection.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from backup_restore import (
    compute_sha256,
    create_backup,
    restore_backup,
    verify_backup_integrity,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from vigil_api.database import Base
from vigil_api.models.v2 import AuditEvent, Facility, Patient, calculate_audit_hash


def populate_test_database(db_path: Path) -> int:
    """Populates test database with facility, users, patients, and hash-chained audit events."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create facility
        fac = Facility(id="FAC-001", name="National Oncology Centre", code="NOC-01")
        session.add(fac)

        # Create patient
        p = Patient(
            id="PAT-DISASTER-01",
            mrn="MRN-DISASTER-01",
            facility_id="FAC-001",
            age=45,
            primary_cancer_type="breast",
            initial_stage="IIB",
            synthetic=True,
        )
        session.add(p)
        session.commit()

        # Create hash-chained audit events
        prev_hash = "GENESIS"
        num_events = 5
        for i in range(num_events):
            ts = datetime.datetime.now(datetime.timezone.utc)
            action = f"clinical_action_{i}"
            details = {"event_index": i, "note": f"Disaster recovery test event {i}"}
            curr_hash = calculate_audit_hash(
                prev_hash=prev_hash,
                timestamp=ts,
                actor_id="DR-TEST-ACTOR",
                actor_role="clinician",
                action=action,
                resource_type="patient",
                resource_id="PAT-DISASTER-01",
                details=details,
            )
            ev = AuditEvent(
                id=f"EVT-DR-{i:03d}",
                timestamp=ts,
                actor_id="DR-TEST-ACTOR",
                actor_role="clinician",
                action=action,
                resource_type="patient",
                resource_id="PAT-DISASTER-01",
                details=details,
                prev_hash=prev_hash,
                curr_hash=curr_hash,
            )
            session.add(ev)
            session.commit()
            prev_hash = curr_hash

        return num_events
    finally:
        session.close()
        engine.dispose()


def test_disaster_recovery_full_lifecycle(tmp_path):
    """Executes full disaster recovery lifecycle: backup, verification, restore, and assertions."""
    source_db = tmp_path / "production_source.db"
    backup_root = tmp_path / "backups"
    restored_db = tmp_path / "restored_production.db"

    # 1. Populate initial production database
    events_count = populate_test_database(source_db)
    assert source_db.exists()

    # 2. Execute hot online backup
    backup_folder = create_backup(source_db, backup_root)
    assert backup_folder.exists()
    assert (backup_folder / "database.db").exists()
    assert (backup_folder / "audit_ledger.jsonl").exists()
    assert (backup_folder / "manifest.json").exists()

    # Verify manifest integrity
    valid, msg = verify_backup_integrity(backup_folder)
    assert valid is True, msg

    # 3. Simulate disaster (source database destroyed)
    source_db.unlink()
    assert not source_db.exists()

    # 4. Measure RTO during recovery
    t_start = time.perf_counter()
    success = restore_backup(backup_folder, restored_db, verify_audit_chain=True)
    rto_seconds = time.perf_counter() - t_start

    assert success is True
    assert restored_db.exists()

    # Assert Recovery Time Objective (RTO < 5 seconds)
    assert rto_seconds < 5.0, f"RTO violated: took {rto_seconds:.2f}s (budget: <5.0s)"

    # 5. Measure Recovery Point Objective (RPO = 0 lost records)
    conn = sqlite3.connect(str(restored_db))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM patients")
    patient_count = cur.fetchone()[0]
    assert patient_count == 1, "RPO violated: patient record lost during disaster recovery!"

    cur.execute("SELECT COUNT(*) FROM audit_events")
    restored_events = cur.fetchone()[0]
    assert restored_events == events_count, "RPO violated: audit records lost during recovery!"
    conn.close()


def test_disaster_recovery_detects_database_tampering(tmp_path):
    """Asserts that modified database file in backup package is detected and rejected."""
    source_db = tmp_path / "tamper_source.db"
    backup_root = tmp_path / "backups_tamper"
    target_db = tmp_path / "target_tamper.db"

    populate_test_database(source_db)
    backup_folder = create_backup(source_db, backup_root)

    # Tamper with database file by appending corrupt byte
    db_file = backup_folder / "database.db"
    with open(db_file, "ab") as f:
        f.write(b"\x00\xffCORRUPT_TAMPER_BYTES")

    # Restore must reject corrupted backup
    with pytest.raises(ValueError, match="TamperDetectedError"):
        restore_backup(backup_folder, target_db)


def test_disaster_recovery_detects_broken_audit_chain(tmp_path):
    """Asserts that unbroken hash-chain violation in database halts restoration."""
    source_db = tmp_path / "chain_source.db"
    backup_root = tmp_path / "backups_chain"
    target_db = tmp_path / "target_chain.db"

    populate_test_database(source_db)
    backup_folder = create_backup(source_db, backup_root)

    # Connect to backup database and mutate an audit event's action without updating curr_hash
    db_file = backup_folder / "database.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("UPDATE audit_events SET action = 'unauthorized.action' WHERE rowid = 1")
    conn.commit()
    conn.close()

    # Recompute file sha256 in manifest so file checksum passes, but chain verification catches it
    manifest_file = backup_folder / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    manifest["database_sha256"] = compute_sha256(db_file)
    manifest_file.write_text(json.dumps(manifest))

    # Restore must fail due to broken audit chain
    with pytest.raises(ValueError, match="TamperDetectedError"):
        restore_backup(backup_folder, target_db, verify_audit_chain=True)
