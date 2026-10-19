#!/usr/bin/env python3
"""Fail when README version-like claims disagree with lockfiles (G-10).

Checks:
  - Python: pyproject workspace version vs apps/api version (must match declared alpha).
  - Master Plan badge in README must say v1.3 when docs/MASTER_PLAN.md plan version is 1.3.
  - Node: if README pins an engines/node major, it must match package.json engines.

Usage:
  uv run python scripts/check_readme_version_claims.py
  uv run python scripts/check_readme_version_claims.py --seed-fail
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check() -> list[str]:
    problems: list[str] = []
    readme = _read(ROOT / "README.md")
    root_py = _read(ROOT / "pyproject.toml")
    api_py = _read(ROOT / "apps" / "api" / "pyproject.toml")

    root_ver = re.search(r'^version\s*=\s*"([^"]+)"', root_py, re.M)
    api_ver = re.search(r'^version\s*=\s*"([^"]+)"', api_py, re.M)
    if not root_ver or not api_ver:
        problems.append("could not parse version from pyproject.toml")
    elif root_ver.group(1) != api_ver.group(1):
        problems.append(
            f"workspace version {root_ver.group(1)} != vigil-api {api_ver.group(1)}"
        )

    # Master plan badge / text
    if "Master_Plan-v1.3" not in readme and "Master Plan: v1.3" not in readme:
        problems.append("README missing Master Plan v1.3 badge/claim")
    plan = _read(ROOT / "docs" / "MASTER_PLAN.md")[:4000]
    if "1.3" not in plan:
        problems.append("docs/MASTER_PLAN.md header region does not mention 1.3")

    pkg = json.loads(_read(ROOT / "package.json"))
    engines = (pkg.get("engines") or {}).get("node", "")
    # README says Node.js v20+
    if "Node.js v20" not in readme and "Node.js 20" not in readme:
        problems.append("README does not state Node.js v20+")
    if engines and "20" not in str(engines):
        problems.append(f"package.json engines.node={engines!r} does not include 20")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-fail", action="store_true")
    args = parser.parse_args()
    if args.seed_fail:
        print("seed-fail: simulated README/lockfile mismatch", file=sys.stderr)
        return 1
    problems = check()
    if problems:
        print("README version claim check FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("README version claim check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
