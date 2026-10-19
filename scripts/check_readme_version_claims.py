#!/usr/bin/env python3
"""Fail when version claims in README.md disagree with the pins that actually decide them (G-10).

Claims are *extracted from the README text* and compared with: pyproject `requires-python`, uv.lock,
package.json `engines`, package-lock.json, the CI workflows' python/node versions, the compose Postgres
image, and the Master Plan header version. A claim the checker cannot map to a pin is reported, not ignored.

  uv run python scripts/check_readme_version_claims.py
  uv run python scripts/check_readme_version_claims.py --seed-fail   # runs the real checker on a doctored README
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _min_version(spec: str) -> tuple[int, ...] | None:
    m = re.search(r">=\s*(\d+(?:\.\d+)*)", spec)
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def _ver(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3])


def _lock_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    uv = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    for p in uv.get("package", []):
        out[p["name"].lower()] = p.get("version", "")
    npm = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    for path, pkg in npm.get("packages", {}).items():
        if path.startswith("node_modules/") and pkg.get("version"):
            out.setdefault(path[len("node_modules/") :].lower(), pkg["version"])
    return out


def _ci_versions(key: str) -> set[str]:
    found: set[str] = set()
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        found |= set(re.findall(rf'{key}:\s*"?([\d.]+)"?', wf.read_text(encoding="utf-8")))
    return found


def check(readme: str) -> list[str]:
    problems: list[str] = []
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    locks = _lock_versions()

    # --- Python claim: "Python 3.11+" ---
    py_claims = re.findall(r"Python\s+(\d+\.\d+)\+", readme)
    if not py_claims:
        problems.append("README states no 'Python X.Y+' prerequisite")
    declared = _min_version(pyproject["project"].get("requires-python", ""))
    for c in py_claims:
        if declared is None or _ver(c) < declared:
            problems.append(
                f"README says Python {c}+ but requires-python is {pyproject['project'].get('requires-python')!r}"
            )
    lowest_claim = min((_ver(c) for c in py_claims), default=None)
    if (
        lowest_claim
        and declared
        and lowest_claim != declared
        and _ver(f"{declared[0]}.{declared[1]}") != lowest_claim
    ):
        problems.append(
            f"README lowest Python {lowest_claim} != requires-python minimum {declared}"
        )
    for v in _ci_versions("python-version"):
        if declared and _ver(v) < declared:
            problems.append(f"CI runs Python {v}, below requires-python {declared}")

    # --- Node / npm claims ---
    engines = pkg.get("engines") or {}
    for tool, label in (("node", r"Node\.js"), ("npm", r"npm")):
        claims = re.findall(rf"{label}\s+v?(\d+)\+", readme)
        if not claims:
            problems.append(f"README states no '{label} N+' prerequisite")
        pin = _min_version(engines.get(tool, ""))
        if not pin:
            problems.append(f"package.json engines.{tool} is not pinned (README claims {claims})")
            continue
        for c in claims:
            if int(c) != pin[0]:
                problems.append(
                    f"README says {tool} {c}+ but package.json engines.{tool}={engines[tool]!r}"
                )
    for v in _ci_versions("node-version"):
        pin = _min_version(engines.get("node", ""))
        if pin and int(v.split(".")[0]) < pin[0]:
            problems.append(f"CI runs Node {v}, below engines.node {engines.get('node')}")

    # --- Library / service claims: "Next.js 15", "FastAPI 0.115", "PostgreSQL 16" ... ---
    libs = {
        "next.js": "next",
        "fastapi": "fastapi",
        "react": "react",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic",
    }
    for m in re.finditer(
        r"(Next\.js|FastAPI|React|SQLAlchemy|Pydantic)\s+v?(\d+(?:\.\d+)?)", readme
    ):
        name, claim = m.group(1), m.group(2)
        locked = locks.get(libs[name.lower()])
        if not locked:
            problems.append(f"README claims {name} {claim} but it is not in the lockfiles")
        elif _ver(locked)[: len(_ver(claim))] != _ver(claim):
            problems.append(f"README claims {name} {claim} but the lockfile pins {locked}")
    for m in re.finditer(r"Postgre(?:SQL|s)\s+v?(\d+)", readme):
        img = (ROOT / "infra" / "docker-compose.yml").read_text(encoding="utf-8")
        tag = re.search(r"image:\s*postgres:(\d+)", img)
        if not tag or tag.group(1) != m.group(1):
            problems.append(
                f"README claims PostgreSQL {m.group(1)} but compose uses {tag.group(1) if tag else '?'}"
            )

    # --- Master Plan version badge ---
    plan = (ROOT / "docs" / "MASTER_PLAN.md").read_text(encoding="utf-8")[:3000]
    pv = re.search(r"Version\s+(\d+\.\d+)", plan)
    badge = re.search(r"Master[_ ]Plan[-: ]+v?(\d+\.\d+)", readme)
    if not pv:
        problems.append("could not read the Master Plan version from docs/MASTER_PLAN.md")
    elif not badge or badge.group(1) != pv.group(1):
        problems.append(
            f"README Master Plan version {badge.group(1) if badge else None} != plan header {pv.group(1)}"
        )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-fail", action="store_true")
    args = ap.parse_args()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if args.seed_fail:
        # Doctor the README with wrong claims and run the REAL checker; it must find them.
        readme = readme.replace("Node.js v20+", "Node.js v18+").replace(
            "Python 3.11+", "Python 3.8+"
        )
        readme += "\nBuilt with Next.js 9 and Master_Plan-v0.1\n"
    problems = check(readme)
    if problems:
        print("README version claim check FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("README version claim check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
