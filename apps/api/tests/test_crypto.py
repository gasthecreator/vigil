"""Tests for field-level encryption and key rotation.

Adheres to MASTER_PLAN.md §9.3 and Phase 5 deliverables.
"""

from __future__ import annotations

import sqlite3

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from vigil_api.crypto import (
    decrypt_field,
    encrypt_field,
)
from vigil_api.database import Base
from vigil_api.models.v2 import Patient

from scripts.rotate_encryption_keys import rotate_patient_keys


def test_crypto_round_trip():
    plaintext = "MRN-TOP-SECRET-007"
    ciphertext = encrypt_field(plaintext)
    assert ciphertext is not None
    assert ciphertext != plaintext
    assert ciphertext.startswith("gAAAAA")

    decrypted = decrypt_field(ciphertext)
    assert decrypted == plaintext


def test_field_level_encryption_in_sqlite(tmp_path):
    db_file = tmp_path / "crypto_test.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    # Insert patient with direct identifier
    with Session() as session:
        pat = Patient(
            id="pat-crypto-01",
            mrn="MRN-SENSITIVE-999",
            external_id="EXT-ID-444",
            biological_sex="female",
            primary_cancer_type="breast",
            synthetic=True,
            status="active",
        )
        session.add(pat)
        session.commit()

    # 1. Verify raw SQL reveals ONLY ciphertext, NEVER plaintext
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT mrn, external_id FROM patients WHERE id = 'pat-crypto-01'")
    raw_mrn, raw_ext = cur.fetchone()
    conn.close()

    assert raw_mrn != "MRN-SENSITIVE-999"
    assert raw_mrn.startswith("gAAAAA")
    assert raw_ext != "EXT-ID-444"
    assert raw_ext.startswith("gAAAAA")

    # 2. Verify SQLAlchemy query decrypts transparently
    with Session() as session:
        loaded = session.query(Patient).filter(Patient.id == "pat-crypto-01").first()
        assert loaded is not None
        assert loaded.mrn == "MRN-SENSITIVE-999"
        assert loaded.external_id == "EXT-ID-444"


def test_key_rotation(tmp_path, monkeypatch):
    db_file = tmp_path / "rotation_test.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)

    # Key A (old primary) and Key B (new primary)
    key_a = Fernet.generate_key().decode("ascii")
    key_b = Fernet.generate_key().decode("ascii")

    # Phase 1: Encrypt under Key A
    f_a = Fernet(key_a.encode("ascii"))
    token_mrn_a = f_a.encrypt(b"MRN-ROTATION-ABC").decode("utf-8")

    now_iso = "2026-10-17 00:00:00"
    conn = sqlite3.connect(db_file)
    conn.execute(
        "INSERT INTO patients (id, mrn, external_id, biological_sex, primary_cancer_type, synthetic, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("pat-rot-01", token_mrn_a, None, "female", "breast", 1, "active", now_iso, now_iso),
    )
    conn.commit()
    conn.close()

    # Verify token_mrn_a can NOT be decrypted by key B
    f_b = Fernet(key_b.encode("ascii"))
    with pytest.raises(Exception):
        f_b.decrypt(token_mrn_a.encode("utf-8"))

    # Phase 2: Configure rotation with key_b (primary) and key_a (secondary)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEYS", f"{key_b},{key_a}")

    scanned, rotated = rotate_patient_keys(db_url, dry_run=False)
    assert scanned == 1
    assert rotated == 1

    # Verify raw token is now encrypted under key_b
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT mrn FROM patients WHERE id = 'pat-rot-01'")
    (new_raw_mrn,) = cur.fetchone()
    conn.close()

    assert new_raw_mrn != token_mrn_a
    # Decryptable by f_b directly!
    decrypted_by_b = f_b.decrypt(new_raw_mrn.encode("utf-8")).decode("utf-8")
    assert decrypted_by_b == "MRN-ROTATION-ABC"
