#!/usr/bin/env python3
"""Generate third-party licence inventory + NOTICE fragments (G-10).

Writes:
  reports/quality/LICENCE_INVENTORY.json
  NOTICE  (Apache-2.0 header + summarised third-party list)

Usage:
  uv run python scripts/generate_licence_inventory.py
  uv run python scripts/generate_licence_inventory.py --seed-fail
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "reports" / "quality" / "LICENCE_INVENTORY.json"
NOTICE = ROOT / "NOTICE"


def _uv_pip_licences() -> list[dict]:
    """Best-effort: parse `uv export` + importlib metadata when available."""
    rows: list[dict] = []
    try:
        import importlib.metadata as md
    except ImportError:
        return rows

    for dist in sorted(md.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"]
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "version": dist.version,
                "license": dist.metadata.get("License")
                or dist.metadata.get("License-Expression")
                or "UNKNOWN",
            }
        )
    return rows


def write_notice(entries: list[dict]) -> None:
    lines = [
        "Vigil",
        "Copyright (c) Vigil contributors",
        "",
        "This product includes software developed under the Apache License 2.0.",
        "See the LICENSE file for the Vigil project licence.",
        "",
        "Third-party components (Python environment at generation time):",
        "",
    ]
    for e in entries[:500]:
        lines.append(f"  - {e['name']} {e['version']} ({e['license']})")
    if len(entries) > 500:
        lines.append(f"  … and {len(entries) - 500} more (see reports/quality/LICENCE_INVENTORY.json)")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append("Regenerate: uv run python scripts/generate_licence_inventory.py")
    lines.append("")
    NOTICE.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-fail", action="store_true", help="Exit 1 after writing a marker (CI fail-then-pass)")
    args = parser.parse_args()

    entries = _uv_pip_licences()
    if not entries:
        # Fallback: at least record that generation ran in a minimal env.
        entries = [{"name": "vigil-workspace", "version": "0.1.0-alpha", "license": "Apache-2.0"}]

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(entries),
        "packages": entries,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_notice(entries)
    print(f"Wrote {OUT_JSON} ({len(entries)} packages) and {NOTICE}")

    if args.seed_fail:
        print("seed-fail: refusing success", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
