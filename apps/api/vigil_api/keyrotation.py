"""Key rotation service for Field-Level Encryption.

Rotates encrypted fields in the database using the provided SQLAlchemy Session.
Master Plan §11 / Condition P9-E.
"""

from __future__ import annotations

from typing import Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from vigil_api.crypto import get_multi_fernet, rotate_field_ciphertext


def rotate_patient_keys(db: Session, dry_run: bool = False) -> Tuple[int, int]:
    """Rotate encrypted fields in the patients table to the primary key.

    Uses the existing SQLAlchemy Session without opening separate connections.
    Returns (total_scanned, total_rotated).
    """
    multi_fernet = get_multi_fernet()

    # If only 1 key configured, nothing to rotate
    if len(multi_fernet._fernets) <= 1:
        count = db.execute(text("SELECT count(*) FROM patients")).scalar() or 0
        return int(count), 0

    total_scanned = 0
    total_rotated = 0

    rows = db.execute(text("SELECT id, mrn, external_id FROM patients")).fetchall()
    for row in rows:
        p_id, raw_mrn, raw_ext_id = row[0], row[1], row[2]
        total_scanned += 1

        new_mrn, mrn_rotated = None, False
        if raw_mrn:
            try:
                new_mrn, mrn_rotated = rotate_field_ciphertext(raw_mrn, multi_fernet)
            except Exception:
                pass

        new_ext, ext_rotated = None, False
        if raw_ext_id:
            try:
                new_ext, ext_rotated = rotate_field_ciphertext(raw_ext_id, multi_fernet)
            except Exception:
                pass

        if mrn_rotated or ext_rotated:
            total_rotated += 1
            if not dry_run:
                # Column names are fixed literals (not user input); values are bound.
                allowed_columns = {"mrn", "external_id"}
                updates = {}
                if mrn_rotated:
                    updates["mrn"] = new_mrn
                if ext_rotated:
                    updates["external_id"] = new_ext
                if not set(updates).issubset(allowed_columns):
                    raise RuntimeError("refusing unexpected column in key rotation")
                set_clauses = ", ".join(f"{col} = :{col}" for col in updates)
                updates["id"] = p_id
                db.execute(
                    text(f"UPDATE patients SET {set_clauses} WHERE id = :id"),  # nosec B608
                    updates,
                )

    if not dry_run:
        db.commit()

    return total_scanned, total_rotated
