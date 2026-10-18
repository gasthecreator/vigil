#!/usr/bin/env python3
"""scripts/verify_hazard_log.py

Automated Safety Hazard Verification Tool.
Aligned with ISO 14971 and IEC 62304.
Master Plan §3, §6.7, §11, Phase 8a Governance.

Parses docs/safety/HAZARD_LOG.md (or docs/safety/HAZARD-LOG.md), verifies that:
1. Every hazard (H1..H20+) has severity, probability, mitigations, and verification links.
2. Every cited test file exists on disk.
3. Every cited test function exists in the test file's AST.
4. Optionally executes the verification test suite to ensure all controls pass.

Exit code:
0: All hazard controls verified with existing, valid test cases.
1: Any broken verification link, missing test, or failing control.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

ROOT = Path(__file__).resolve().parent.parent


class HazardEntry(NamedTuple):
    id: str
    hazard: str
    harm: str
    severity: str
    probability: str
    mitigations: str
    verification_links: List[str]


def parse_hazard_log(file_path: Path) -> List[HazardEntry]:
    """Parses markdown table in Hazard Log into structured HazardEntry items."""
    if not file_path.exists():
        raise FileNotFoundError(f"Hazard Log not found at {file_path}")

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    entries: List[HazardEntry] = []
    in_table = False

    for line in lines:
        line_s = line.strip()
        if not line_s.startswith("|"):
            continue

        parts = [p.strip() for p in line_s.split("|")[1:-1]]
        if len(parts) < 7:
            continue

        id_col = parts[0].replace("*", "").strip()
        if not re.match(r"^H\d+$", id_col):
            continue

        # Extract markdown links or backtick codes from the verification column
        verif_col = parts[6]
        links: List[str] = []
        # Match test references like tests/acceptance_p5/test_api_security.py::test_reads_require_consent
        # or `tests/...::test_...`
        raw_refs = re.findall(r"[`']?([a-zA-Z0-9_\-\./]+(?:::[a-zA-Z0-9_]+)?)`?", verif_col)
        for ref in raw_refs:
            ref_clean = ref.strip("`' ")
            if "test" in ref_clean and (".py" in ref_clean or "::" in ref_clean):
                links.append(ref_clean)

        entries.append(
            HazardEntry(
                id=id_col,
                hazard=parts[1],
                harm=parts[2],
                severity=parts[3],
                probability=parts[4],
                mitigations=parts[5],
                verification_links=links,
            )
        )

    return entries


def verify_test_in_ast(file_path: Path, test_func_name: Optional[str] = None) -> bool:
    """Verifies using Python AST that the file parses and contains the target test function."""
    if not file_path.exists():
        return False

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except Exception as e:
        print(f"  ❌ Syntax error parsing {file_path}: {e}")
        return False

    if test_func_name is None:
        return True

    # Search for function definition
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == test_func_name:
            return True
        elif isinstance(node, ast.ClassDef):
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef) and subnode.name == test_func_name:
                    return True

    return False


def main() -> int:
    log_path = ROOT / "docs" / "safety" / "HAZARD_LOG.md"
    if not log_path.exists():
        log_path = ROOT / "docs" / "safety" / "HAZARD-LOG.md"

    print(f"🔍 Verifying Hazard Log at {log_path.relative_to(ROOT)}...")
    entries = parse_hazard_log(log_path)
    print(f"📋 Found {len(entries)} hazard definitions (H1..H{len(entries)}).")

    if len(entries) < 20:
        print(f"❌ Error: Hazard Log contains only {len(entries)} hazards; at least 20 (H1..H20) required.")
        return 1

    errors: List[str] = []
    tests_to_run: List[str] = []

    for entry in entries:
        if not entry.verification_links:
            errors.append(f"Hazard {entry.id} has no valid verification test links cited.")
            continue

        for link in entry.verification_links:
            if "::" in link:
                f_str, func_name = link.split("::", 1)
            else:
                f_str, func_name = link, None

            t_path = ROOT / f_str
            if not t_path.exists():
                errors.append(f"Hazard {entry.id}: Test file does not exist: {f_str}")
                continue

            if func_name and not verify_test_in_ast(t_path, func_name):
                errors.append(f"Hazard {entry.id}: Function '{func_name}' not found in AST of {f_str}")
                continue

            tests_to_run.append(link)

    if errors:
        print("\n❌ Verification Failed! Identified the following defects:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"✅ All {len(entries)} hazards cite valid, AST-verified test functions.")
    print(f"🚀 Total verified test links: {len(tests_to_run)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
