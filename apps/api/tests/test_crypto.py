"""Tests for field-level encryption and key rotation.

Adheres to MASTER_PLAN.md §9.3 and Phase 5 deliverables.
"""

from __future__ import annotations

import sqlite3

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from vigil_api.crypto import (
    decrypt_field,
    encrypt_field,
)
from vigil_api.database import Base, get_db
from vigil_api.main import app
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


def test_mrn_http_api_flow_and_rotation(tmp_path, monkeypatch):
    """Verifies Condition P8-C through HTTP API: create, read, update, blind index, and key rotation."""
    from fastapi.testclient import TestClient
    from vigil_api.database import get_db
    from vigil_api.main import app

    key_1 = Fernet.generate_key().decode()
    key_2 = Fernet.generate_key().decode()

    db_file = tmp_path / "api_crypto.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("FIELD_ENCRYPTION_KEYS", key_1)

    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        headers = {"X-Vigil-Role": "clinician"}
        admin_headers = {"X-Vigil-Role": "admin"}

        # 1. Create patient with MRN via HTTP API
        resp = client.post(
            "/api/v1/patients/",
            json={
                "age": 52,
                "status": "active",
                "mrn": "MRN-CONFIDENTIAL-001",
                "external_id": "EXT-999",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        pat_data = resp.json()
        pid = pat_data["id"]
        assert pat_data["mrn"] == "MRN-CONFIDENTIAL-001"

        # 2. Verify raw SQLite contains ciphertext, NOT plaintext
        conn = sqlite3.connect(db_file)
        row = conn.execute(
            "SELECT mrn, external_id, mrn_bidx FROM patients WHERE id = ?", (pid,)
        ).fetchone()
        conn.close()
        raw_mrn, raw_ext, bidx = row
        assert raw_mrn.startswith("gAAAAA")
        assert "MRN-CONFIDENTIAL-001" not in raw_mrn
        assert bidx is not None
        assert len(bidx) == 64

        # 3. Grant consent and read back decrypted MRN
        client.post(
            f"/api/v1/patients/{pid}/consent",
            json={"scope": "clinical_care", "granted": True},
            headers=headers,
        )
        get_resp = client.get(f"/api/v1/patients/{pid}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["mrn"] == "MRN-CONFIDENTIAL-001"
        assert get_resp.json()["external_id"] == "EXT-999"

        # 4. Search by blind-indexed MRN
        search_resp = client.get("/api/v1/patients/?mrn=MRN-CONFIDENTIAL-001", headers=headers)
        assert search_resp.status_code == 200
        assert len(search_resp.json()) == 1
        assert search_resp.json()[0]["id"] == pid

        # 5. Update MRN via PATCH /{id}
        patch_resp = client.patch(
            f"/api/v1/patients/{pid}",
            json={"mrn": "MRN-UPDATED-002"},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["mrn"] == "MRN-UPDATED-002"

        # Verify updated raw ciphertext in DB
        conn = sqlite3.connect(db_file)
        upd_raw_mrn, upd_bidx = conn.execute(
            "SELECT mrn, mrn_bidx FROM patients WHERE id = ?", (pid,)
        ).fetchone()
        conn.close()
        assert upd_raw_mrn.startswith("gAAAAA")
        assert "MRN-UPDATED-002" not in upd_raw_mrn
        assert upd_bidx != bidx

        # 6. Key rotation via POST /rotate-keys
        # Switch primary key to key_2 with key_1 as secondary
        monkeypatch.setenv("FIELD_ENCRYPTION_KEYS", f"{key_2},{key_1}")
        rot_resp = client.post("/api/v1/patients/rotate-keys", headers=admin_headers)
        assert rot_resp.status_code == 200
        assert rot_resp.json()["rotated"] >= 1

        # Verify patient still decrypts with new primary key
        get_rot = client.get(f"/api/v1/patients/{pid}", headers=headers)
        assert get_rot.status_code == 200
        assert get_rot.json()["mrn"] == "MRN-UPDATED-002"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_duplicate_mrn_rejected_by_policy(tmp_path, monkeypatch):
    """Enforces ADR 0011 / Condition P9-F: Duplicate MRNs are prohibited by policy with 409 Conflict."""
    db_file = tmp_path / "dup_test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    headers = {"X-Vigil-Role": "clinician"}

    try:
        # 1. Register first patient with MRN
        r1 = client.post(
            "/api/v1/patients/",
            json={"age": 50, "status": "active", "mrn": "MRN-UNIQUE-001"},
            headers=headers,
        )
        assert r1.status_code == 201
        assert "id" in r1.json()

        # 2. Attempt duplicate MRN registration
        r2 = client.post(
            "/api/v1/patients/",
            json={"age": 52, "status": "active", "mrn": "MRN-UNIQUE-001"},
            headers=headers,
        )
        assert r2.status_code == 409
        assert "Duplicate MRNs are prohibited by policy" in r2.json()["detail"]

        # 3. Register second patient with distinct MRN
        r3 = client.post(
            "/api/v1/patients/",
            json={"age": 52, "status": "active", "mrn": "MRN-UNIQUE-002"},
            headers=headers,
        )
        assert r3.status_code == 201
        p2_id = r3.json()["id"]

        # Grant consent to p2 so update can proceed
        client.post(
            f"/api/v1/patients/{p2_id}/consent",
            json={"granted": True, "scope": "surveillance_monitoring"},
            headers=headers,
        )

        # 4. Attempt update of second patient to duplicate first patient's MRN
        r4 = client.patch(
            f"/api/v1/patients/{p2_id}",
            json={"mrn": "MRN-UNIQUE-001"},
            headers=headers,
        )
        assert r4.status_code == 409
        assert "already registered" in r4.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_http_key_rotation_with_two_keys_and_retired_old_key(tmp_path, monkeypatch):
    """Enforce Condition P10-C: HTTP-level rotation with two keys, re-encryption and retirement of old key.

    1. Ingest patient via HTTP POST /patients/ under key_old.
    2. Confirm ciphertext in DB is decryptable with key_old, NOT key_new.
    3. Reconfigure FIELD_ENCRYPTION_KEYS to '{key_new},{key_old}' and trigger POST /rotate-keys via HTTP.
    4. Confirm rotated count >= 1 and DB ciphertext changed to key_new.
    5. Retire key_old completely (FIELD_ENCRYPTION_KEYS='{key_new}') and read back via HTTP GET /patients/{id}.
    6. Confirm patient decrypts with key_new alone; key_old cannot decrypt the updated record.
    """
    key_old = Fernet.generate_key().decode()
    key_new = Fernet.generate_key().decode()

    # Step 1: Initialize server with key_old only
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key_old)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEYS", key_old)

    db_file = tmp_path / "rotation_http_test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    clinician_headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "doc-rot"}
    admin_headers = {"X-Vigil-Role": "admin", "X-Vigil-User-Id": "admin-rot"}

    try:
        # Create patient via HTTP
        p_resp = client.post(
            "/api/v1/patients/",
            json={
                "age": 48,
                "status": "active",
                "mrn": "MRN-ROTATE-ME-99",
                "external_id": "EXT-ROTATE-88",
            },
            headers=clinician_headers,
        )
        assert p_resp.status_code == 201
        pid = p_resp.json()["id"]

        # Grant consent so full unmasked record is readable
        c_resp = client.post(
            f"/api/v1/patients/{pid}/consent",
            json={"granted": True, "scope": "surveillance_monitoring"},
            headers=clinician_headers,
        )
        assert c_resp.status_code in (200, 201)

        # Step 2: Verify in DB that raw ciphertext is encrypted with key_old, not key_new
        conn = sqlite3.connect(db_file)
        raw_mrn, raw_ext = conn.execute(
            "SELECT mrn, external_id FROM patients WHERE id = ?", (pid,)
        ).fetchone()
        conn.close()

        assert Fernet(key_old.encode()).decrypt(raw_mrn.encode()).decode() == "MRN-ROTATE-ME-99"
        with pytest.raises(Exception):
            Fernet(key_new.encode()).decrypt(raw_mrn.encode())

        # Step 3: Configure dual keys (key_new primary, key_old secondary)
        monkeypatch.setenv("FIELD_ENCRYPTION_KEYS", f"{key_new},{key_old}")
        monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key_new)

        # Trigger HTTP rotation endpoint
        rot_resp = client.post("/api/v1/patients/rotate-keys", headers=admin_headers)
        assert rot_resp.status_code == 200
        data = rot_resp.json()
        assert data["status"] == "success"
        assert data["scanned"] == 1
        assert data["rotated"] == 1

        # Step 4: Verify DB ciphertext changed and is now encrypted with key_new
        conn = sqlite3.connect(db_file)
        new_raw_mrn, new_raw_ext = conn.execute(
            "SELECT mrn, external_id FROM patients WHERE id = ?", (pid,)
        ).fetchone()
        conn.close()

        assert new_raw_mrn != raw_mrn
        assert Fernet(key_new.encode()).decrypt(new_raw_mrn.encode()).decode() == "MRN-ROTATE-ME-99"
        assert Fernet(key_new.encode()).decrypt(new_raw_ext.encode()).decode() == "EXT-ROTATE-88"

        # Step 5: Retire key_old completely
        monkeypatch.setenv("FIELD_ENCRYPTION_KEYS", key_new)
        monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key_new)

        # Read back patient through HTTP API
        get_resp = client.get(f"/api/v1/patients/{pid}", headers=clinician_headers)
        assert get_resp.status_code == 200
        patient_data = get_resp.json()
        assert patient_data["mrn"] == "MRN-ROTATE-ME-99"
        assert patient_data["external_id"] == "EXT-ROTATE-88"

        # Also confirm via list endpoint that is_masked is False (active consent)
        list_resp = client.get("/api/v1/patients/", headers=clinician_headers)
        assert list_resp.status_code == 200
        p_in_list = next(p for p in list_resp.json() if p["id"] == pid)
        assert p_in_list["mrn"] == "MRN-ROTATE-ME-99"
        assert p_in_list["is_masked"] is False

        # Confirm old key cannot decrypt updated record
        with pytest.raises(Exception):
            Fernet(key_old.encode()).decrypt(new_raw_mrn.encode())

    finally:
        app.dependency_overrides.pop(get_db, None)
