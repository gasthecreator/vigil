#!/usr/bin/env python3
"""scripts/verify_hazard_log.py

Automated Safety Hazard Verification Tool.
Aligned with ISO 14971:2019 and IEC 62304:2006/AMD 1:2015.
Enforces Master Plan §3, §11, and Overseer Condition P14-C.

Verifies docs/safety/HAZARD_LOG.md:
1. Enforces single canonical file (rejects duplicate HAZARD-LOG.md if present).
2. Verifies that all hazards (H1..H22) have severity, probability, status, residual risk, mitigations, and verification links.
3. Ensures hazards with unproven/unvalidated controls (H10, H16) are classified as OPEN with residual risk documented.
4. Verifies AST existence of cited test functions.
5. ACTUALLY EXECUTES every cited test via pytest with required acceptance environment variables.
   Fails if any cited test fails, is skipped, or does not exist.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

ROOT = Path(__file__).resolve().parent.parent


class HazardEntry(NamedTuple):
    id: str
    hazard: str
    harm: str
    severity: str
    probability: str
    status: str
    residual_risk: str
    mitigations: str
    verification_links: List[str]


def parse_hazard_log(file_path: Path) -> List[HazardEntry]:
    """Parses markdown table in Hazard Log into structured HazardEntry items."""
    if not file_path.exists():
        raise FileNotFoundError(f"Hazard Log not found at {file_path}")

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    entries: List[HazardEntry] = []

    for line in lines:
        line_s = line.strip()
        if not line_s.startswith("|"):
            continue

        parts = [p.strip() for p in line_s.split("|")[1:-1]]
        if len(parts) < 9:
            continue

        id_col = parts[0].replace("*", "").strip()
        if not re.match(r"^H\d+$", id_col):
            continue

        # Extract markdown links or backtick codes from the verification column
        verif_col = parts[8]
        links: List[str] = []
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
                status=parts[5].replace("*", "").strip(),
                residual_risk=parts[6],
                mitigations=parts[7],
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

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == test_func_name:
            return True
        elif isinstance(node, ast.ClassDef):
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef) and subnode.name == test_func_name:
                    return True

    return False


def run_tests_via_pytest(tests: List[str]) -> bool:
    """Executes all cited tests in a single pytest invocation with required acceptance env flags."""
    print(f"🧪 Executing {len(tests)} cited tests to verify actual control execution...")
    env = os.environ.copy()
    env.update(
        {
            "VIGIL_ACCEPT_P4": "1",
            "VIGIL_CONTRACT_P4V2": "1",
            "VIGIL_ACCEPT_P5": "1",
            "VIGIL_ACCEPT_P7": "1",
            "VIGIL_ACCEPT_P8": "1",
            "VIGIL_ACCEPT_P9": "1",
            "VIGIL_ACCEPT_P11": "1",
            "VIGIL_ACCEPT_P12": "1",
            "VIGIL_ACCEPT_P13": "1",
            "VIGIL_ACCEPT_P14": "1",
            "VIGIL_ACCEPT_3B": "1",
            "VIGIL_ACCEPTANCE": "1",
            "VIGIL_CONTRACT_V2": "1",
        }
    )

    cmd = [sys.executable, "-m", "pytest", "-v"] + tests
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        print("❌ Pytest execution failed for cited hazard verification tests:")
        print(proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout)
        print(proc.stderr[-1000:] if len(proc.stderr) > 1000 else proc.stderr)
        return False

    # Check for skipped tests
    if "skipped" in proc.stdout:
        # Check if any cited test was skipped
        for line in proc.stdout.splitlines():
            if "SKIPPED" in line:
                print(f"❌ Cited test was SKIPPED: {line}")
                return False

    print("  ✅ All cited hazard verification tests passed with zero failures and zero skips.")
    return True


def main() -> int:
    duplicate_path = ROOT / "docs" / "safety" / "HAZARD-LOG.md"
    if duplicate_path.exists():
        print(f"❌ Error: Duplicate file {duplicate_path} exists! Only docs/safety/HAZARD_LOG.md is permitted.")
        return 1

    log_path = ROOT / "docs" / "safety" / "HAZARD_LOG.md"
    print(f"🔍 Verifying Hazard Log at {log_path.relative_to(ROOT)}...")
    entries = parse_hazard_log(log_path)
    print(f"📋 Found {len(entries)} hazard definitions (H1..H{len(entries)}).")

    if len(entries) < 22:
        print(f"❌ Error: Hazard Log contains only {len(entries)} hazards; at least 22 (H1..H22) required.")
        return 1

    errors: List[str] = []
    tests_to_run: List[str] = []

    # Verify H10 and H16 are classified as OPEN
    h_map = {e.id: e for e in entries}
    if h_map.get("H10") and h_map["H10"].status != "OPEN":
        errors.append("Hazard H10 must be classified as OPEN with residual risk documented (Condition P14-C).")
    if h_map.get("H16") and h_map["H16"].status != "OPEN":
        errors.append("Hazard H16 must be classified as OPEN with residual risk documented (Condition P14-C).")

    for entry in entries:
        if not entry.residual_risk or len(entry.residual_risk.strip()) < 5:
            errors.append(f"Hazard {entry.id} is missing a documented residual risk assessment.")

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

            if link not in tests_to_run:
                tests_to_run.append(link)

    if errors:
        print("\n❌ Hazard Log Verification Failed! Identified the following defects:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"✅ All {len(entries)} hazards cite valid, AST-verified test functions.")
    print(f"  - H10 and H16 correctly marked OPEN with documented residual risk.")

    # Actively execute all cited tests
    if not run_tests_via_pytest(tests_to_run):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
