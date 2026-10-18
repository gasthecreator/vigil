#!/usr/bin/env python3
"""Generate the audit-hash compatibility golden fixture from the OLD production code (P15-G).

The old ``calculate_audit_hash`` (before the Phase 8b change that normalised string timestamps)
is extracted verbatim from git history (commit OLD_SHA, ``apps/api/vigil_api/models/v2.py``) and
executed here. Nothing in the fixture is computed by the current implementation, so a test that
verifies it with the current code is a real backwards-compatibility check (ADR-0020).

Output: tests/resilience/fixtures/audit_chain_v0_golden.json
Usage:  python scripts/generate_audit_compat_fixture.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
OLD_SHA = "9709295"  # last commit before 370dc54 (Phase 8b) changed the function
OUT = ROOT / "tests" / "resilience" / "fixtures" / "audit_chain_v0_golden.json"


def load_old_function() -> Any:
    src = subprocess.run(
        ["git", "show", f"{OLD_SHA}:apps/api/vigil_api/models/v2.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    m = re.search(r"^def calculate_audit_hash\(.*?(?=^# =====)", src, flags=re.S | re.M)
    assert m, "old calculate_audit_hash not found in history"
    ns: Dict[str, Any] = {
        "hashlib": hashlib,
        "json": json,
        "datetime": datetime,
        "timezone": timezone,
        "Any": Any,
        "Dict": Dict,
    }
    exec(compile(m.group(0), f"{OLD_SHA}:models/v2.py", "exec"), ns)  # noqa: S102
    assert "ts_str = str(timestamp)" in m.group(0)
    return ns["calculate_audit_hash"], m.group(0)


def main() -> None:
    old_hash, old_src = load_old_function()
    base = datetime(2026, 3, 1, 8, 30, 15, 123456, tzinfo=timezone.utc)
    actions = [
        ("USR-DR-01", "clinician", "patient.read", "patient", "PAT-001", {"fields": ["name", "mrn"]}),
        ("USR-DR-01", "clinician", "observation.create", "observation", "OBS-001", {"analyte": "CA15-3", "value": 41.2, "unit": "U/mL"}),
        ("USR-NURSE-01", "nurse_clerk", "observation.create", "observation", "OBS-002", {"note": "Ọmọ́ Adébáyọ̀ — unicode ✓", "nested": {"b": 2, "a": [1, 2, {"z": None}]}}),
        ("SYSTEM", "admin", "alert.escalate", "alert", "ALT-001", {"tier": "REVIEW", "p": 0.0123456789}),
        ("USR-ADMIN-01", "admin", "consent.revoke", "consent", "CON-001", {}),
        ("USR-DR-01", "clinician", "continuity.schedule_confirmed", "course", "RTC-001", {"moves": 3}),
    ]
    rows_dt = []  # chain A: what the old code wrote in production (datetime inputs)
    prev = "0" * 64
    for i in range(12):
        actor, role, action, rtype, rid, details = actions[i % len(actions)]
        # alternate tz-aware UTC, tz-aware non-UTC offset, and naive (taken as UTC) inputs
        ts_aware = base + timedelta(minutes=7 * i, microseconds=i * 1001)
        if i % 3 == 1:
            ts_in = ts_aware.astimezone(timezone(timedelta(hours=1)))  # Lagos time, WAT
        elif i % 3 == 2:
            ts_in = ts_aware.replace(tzinfo=None)
        else:
            ts_in = ts_aware
        h = old_hash(prev, ts_in, actor, role, action, rtype, rid, details)
        utc = ts_aware.astimezone(timezone.utc)
        rows_dt.append(
            {
                "id": f"EVT-A-{i:03d}",
                "timestamp_iso_utc": utc.isoformat(),  # JSONL export form
                "timestamp_sqlite": utc.replace(tzinfo=None).isoformat(sep=" "),  # SQLite/SQLAlchemy storage form
                "actor_id": actor,
                "actor_role": role,
                "action": action,
                "resource_type": rtype,
                "resource_id": rid,
                "details": details,
                "prev_hash": prev,
                "curr_hash": h,
                "input_kind": "naive" if ts_in.tzinfo is None else "aware",
            }
        )
        prev = h

    rows_str = []  # chain B: rows hashed by the old code from a raw timestamp STRING (old string path)
    prev = "0" * 64
    for i in range(8):
        actor, role, action, rtype, rid, details = actions[(i + 2) % len(actions)]
        ts = base + timedelta(hours=1, minutes=3 * i)
        raw = ts.replace(tzinfo=None).isoformat(sep=" ")  # "YYYY-MM-DD HH:MM:SS.ffffff"
        h = old_hash(prev, raw, actor, role, action, rtype, rid, details)
        rows_str.append(
            {
                "id": f"EVT-B-{i:03d}",
                "timestamp_sqlite": raw,
                "actor_id": actor,
                "actor_role": role,
                "action": action,
                "resource_type": rtype,
                "resource_id": rid,
                "details": details,
                "prev_hash": prev,
                "curr_hash": h,
            }
        )
        prev = h

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated_by": "scripts/generate_audit_compat_fixture.py",
                "old_function_commit": OLD_SHA,
                "old_function_source_sha256": hashlib.sha256(old_src.encode()).hexdigest(),
                "chain_written_from_datetime": rows_dt,
                "chain_hashed_from_raw_string": rows_str,
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({len(rows_dt)} + {len(rows_str)} rows) from old function at {OLD_SHA}")


if __name__ == "__main__":
    main()
