#!/usr/bin/env python3
"""Coverage ratchet (G-06).

Targets (MASTER_PLAN §12): ≥90% on vigil-core / explanation verifier; ≥80% elsewhere.
Floor: measured value written to reports/quality/COVERAGE_RATCHET.json (never lower the floor
to make CI pass — only raise it when measured coverage increases).

Usage:
  uv run pytest ... --cov=... --cov-report=json:reports/quality/coverage-run.json
  uv run python scripts/check_coverage_ratchet.py --coverage-json reports/quality/coverage-run.json
  uv run python scripts/check_coverage_ratchet.py --seed-fail   # exits 1 (gate demo)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RATCHET = ROOT / "reports" / "quality" / "COVERAGE_RATCHET.json"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--coverage-json", type=Path, help="pytest-cov JSON report")
    p.add_argument(
        "--seed-fail",
        action="store_true",
        help="Demonstrate the gate failing by requiring an impossible floor",
    )
    args = p.parse_args()

    if args.seed_fail:
        print("Seeded failure: requiring 100.0% against a synthetic 0.0% run")
        print("❌ coverage 0.00% < floor 100.00%")
        return 1

    if not args.coverage_json or not args.coverage_json.exists():
        print(f"Missing coverage JSON: {args.coverage_json}", file=sys.stderr)
        return 2

    if not RATCHET.exists():
        print(f"Missing ratchet file: {RATCHET}", file=sys.stderr)
        return 2

    cov = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    ratchet = json.loads(RATCHET.read_text(encoding="utf-8"))
    measured = float(cov["totals"]["percent_covered"])
    floor = float(ratchet["floor_percent"])
    target = float(ratchet["target_percent"])

    print(f"measured={measured:.2f}% floor={floor:.2f}% target={target:.2f}%")
    print(f"scope={ratchet.get('scope')}")
    print(f"command={ratchet.get('measurement_command')}")
    print(f"machine={ratchet.get('machine')}")

    if measured + 1e-9 < floor:
        print(f"❌ coverage {measured:.2f}% < floor {floor:.2f}%")
        return 1

    if measured + 1e-9 < target:
        print(
            f"⚠️  coverage {measured:.2f}% is below plan target {target:.2f}% "
            f"but meets the measured floor {floor:.2f}% (do not reword the target)."
        )
    else:
        print(f"✅ coverage meets plan target {target:.2f}%")

    # Optional auto-raise: write a suggestion file, never silently lower.
    if measured > floor + 0.5:
        print(
            f"Note: measured exceeds floor by >0.5 pp — consider raising floor to "
            f"{measured:.2f} in a dedicated commit."
        )
    print("✅ coverage ratchet passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
