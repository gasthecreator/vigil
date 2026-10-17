#!/usr/bin/env python3
"""Key rotation script for field-level encrypted columns in Vigil.

Adheres to MASTER_PLAN.md §9.3 and Phase 5 deliverables.
Rotates ciphertext encrypted with secondary keys to the primary encryption key.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Tuple

from sqlalchemy import create_engine, text

# Add apps/api to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from vigil_api.config import settings
from vigil_api.crypto import get_multi_fernet, rotate_field_ciphertext


def rotate_patient_keys(db_url: str, dry_run: bool = False) -> Tuple[int, int]:
    """Rotate encrypted fields in the patients table to the primary key.

    Returns (total_scanned, total_rotated).
    """
    engine = create_engine(db_url)
    multi_fernet = get_multi_fernet()

    total_scanned = 0
    total_rotated = 0

    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, mrn, external_id FROM patients")).fetchall()
        for row in rows:
            p_id, raw_mrn, raw_ext_id = row[0], row[1], row[2]
            total_scanned += 1

            new_mrn, mrn_rotated = None, False
            if raw_mrn:
                try:
                    new_mrn, mrn_rotated = rotate_field_ciphertext(raw_mrn, multi_fernet)
                except Exception as e:
                    print(f"Warning: Failed to rotate mrn for patient {p_id}: {e}", file=sys.stderr)

            new_ext, ext_rotated = None, False
            if raw_ext_id:
                try:
                    new_ext, ext_rotated = rotate_field_ciphertext(raw_ext_id, multi_fernet)
                except Exception as e:
                    print(f"Warning: Failed to rotate external_id for patient {p_id}: {e}", file=sys.stderr)

            if mrn_rotated or ext_rotated:
                total_rotated += 1
                if not dry_run:
                    updates = {}
                    if mrn_rotated:
                        updates["mrn"] = new_mrn
                    if ext_rotated:
                        updates["external_id"] = new_ext
                    set_clauses = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    updates["id"] = p_id
                    conn.execute(
                        text(f"UPDATE patients SET {set_clauses} WHERE id = :id"),
                        updates,
                    )

    return total_scanned, total_rotated


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate field-level encryption keys for Vigil.")
    parser.add_argument("--db-url", default=settings.DATABASE_URL, help="Database URL to connect to")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without updating database")
    args = parser.parse_args()

    print(f"Connecting to database: {args.db_url}")
    print(f"Dry run mode: {args.dry_run}")

    scanned, rotated = rotate_patient_keys(args.db_url, dry_run=args.dry_run)
    print(f"Rotation complete: {scanned} patients scanned, {rotated} patients updated.")


if __name__ == "__main__":
    main()
