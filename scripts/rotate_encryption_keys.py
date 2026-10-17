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

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add apps/api to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from vigil_api.config import settings  # noqa: E402
from vigil_api.keyrotation import rotate_patient_keys as rotate_patient_keys_session  # noqa: E402


def rotate_patient_keys(db_url: str, dry_run: bool = False) -> Tuple[int, int]:
    """Rotate encrypted fields in the patients table to the primary key.

    Returns (total_scanned, total_rotated).
    """
    engine = create_engine(db_url)
    with Session(engine) as session:
        return rotate_patient_keys_session(session, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate field-level encryption keys for Vigil.")
    parser.add_argument(
        "--db-url", default=settings.DATABASE_URL, help="Database URL to connect to"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Scan and report without updating database"
    )
    args = parser.parse_args()

    print(f"Connecting to database: {args.db_url}")
    print(f"Dry run mode: {args.dry_run}")

    scanned, rotated = rotate_patient_keys(args.db_url, dry_run=args.dry_run)
    print(f"Rotation complete: {scanned} patients scanned, {rotated} patients updated.")


if __name__ == "__main__":
    main()
