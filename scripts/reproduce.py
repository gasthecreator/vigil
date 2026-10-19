#!/usr/bin/env python3
"""One-command report regeneration (G-11).

Regenerates / verifies every *cheap* committed study report from a clean tooling
checkout, then diffs governance artefacts that must stay fresh.

Usage:
  make reproduce
  uv run python scripts/reproduce.py
  uv run python scripts/reproduce.py --smoke   # PR CI (same checks; alias kept for clarity)

Full multi-hour ML benchmark regeneration remains `make reproduce-ml` (nightly).
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "quality" / "REPRODUCE_LAST_RUN.json"


def _run(cmd: list[str], *, label: str) -> bool:
    print(f"\n==> {label}\n    {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        print(f"❌ {label} failed (exit {res.returncode})")
        return False
    print(f"✅ {label}")
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--smoke",
        action="store_true",
        help="PR-friendly alias; currently identical to the default path.",
    )
    p.add_argument(
        "--seed-fail",
        action="store_true",
        help="Demonstrate the gate failing (non-zero exit without running checks).",
    )
    args = p.parse_args()
    if args.seed_fail:
        print("Seeded failure: make reproduce / scripts/reproduce.py --seed-fail")
        return 1

    steps: list[tuple[list[str], str]] = [
        (
            [sys.executable, str(ROOT / "scripts" / "verify_study_reproducibility.py")],
            "Study report regeneration + bit-diff (verify_study_reproducibility)",
        ),
        (
            [sys.executable, str(ROOT / "scripts" / "generate_status.py"), "--check"],
            "docs/STATUS.md freshness",
        ),
        (
            [sys.executable, str(ROOT / "scripts" / "generate_sbom.py")],
            "Regenerate SBOM JSON under reports/sbom/",
        ),
    ]

    ok = True
    results: list[dict[str, object]] = []
    for cmd, label in steps:
        passed = _run(cmd, label=label)
        results.append({"label": label, "command": cmd, "ok": passed})
        if not passed:
            ok = False

    # SBOM must match what is committed (no silent drift after lockfile changes).
    sbom_diff = subprocess.run(
        ["git", "diff", "--exit-code", "--", "reports/sbom/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    sbom_ok = sbom_diff.returncode == 0
    results.append(
        {
            "label": "Committed SBOM matches regeneration",
            "command": ["git", "diff", "--exit-code", "--", "reports/sbom/"],
            "ok": sbom_ok,
        }
    )
    if sbom_ok:
        print("✅ Committed SBOM matches regeneration")
    else:
        print("❌ reports/sbom/ drifted after generate_sbom.py — commit the refreshed files")
        print(sbom_diff.stdout[:2000])
        ok = False

    # Verify committed release hashes (does not rewrite the manifest; refuses dirty listed files).
    verify_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_release_manifest.py"),
        "verify",
        "--release",
        "v1.0.0-rc.2",
    ]
    verify_ok = _run(verify_cmd, label="Verify release hash manifest (v1.0.0-rc.2)")
    results.append({"label": "Verify release hash manifest (v1.0.0-rc.2)", "command": verify_cmd, "ok": verify_ok})
    if not verify_ok:
        ok = False

    payload = {
        "ok": ok,
        "mode": "smoke" if args.smoke else "default",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "machine": {"platform": platform.platform(), "python": sys.version.split()[0]},
        "steps": results,
        "note": (
            "Cheap study regeneration + STATUS/SBOM/manifest. "
            "Full classical ML suite: make reproduce-ml (nightly)."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
