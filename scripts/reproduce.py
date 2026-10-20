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


def _release_manifests_for_head(head_sha: str) -> list[str]:
    """Return release IDs whose manifest was generated from this exact commit."""
    manifest_dir = ROOT / "docs" / "release"
    releases = []
    for path in sorted(manifest_dir.glob("RELEASE_MANIFEST_*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("git_commit") == head_sha:
            releases.append(path.stem.removeprefix("RELEASE_MANIFEST_"))
    return releases


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
            [sys.executable, str(ROOT / "scripts" / "run_alert_fatigue_simulation.py"), "--verify"],
            "EXP-UF-001 synthetic alert-burden metrics",
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

    # A release manifest hashes one immutable commit, not every later PR checkout.
    # The release workflow generates and verifies a fresh manifest for tagged commits.
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    if head.returncode != 0:
        print(
            f"❌ Could not determine HEAD for release manifest verification: {head.stderr.strip()}"
        )
        results.append(
            {
                "label": "Verify release hash manifest",
                "command": ["git", "rev-parse", "HEAD"],
                "ok": False,
            }
        )
        ok = False
    else:
        head_sha = head.stdout.strip()
        releases = _release_manifests_for_head(head_sha)
        if releases:
            for release in releases:
                verify_cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_release_manifest.py"),
                    "verify",
                    "--release",
                    release,
                ]
                verify_ok = _run(verify_cmd, label=f"Verify release hash manifest ({release})")
                results.append(
                    {
                        "label": f"Verify release hash manifest ({release})",
                        "command": verify_cmd,
                        "ok": verify_ok,
                    }
                )
                if not verify_ok:
                    ok = False
        else:
            print(
                "⏭️ Release manifest verification not applicable: no committed release manifest "
                f"records HEAD {head_sha}. The release workflow generates and verifies a manifest "
                "for the tagged commit."
            )
            results.append(
                {
                    "label": "Verify release hash manifest",
                    "command": [],
                    "ok": True,
                    "status": "not_applicable_to_this_commit",
                    "head_commit": head_sha,
                }
            )

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
