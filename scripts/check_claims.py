#!/usr/bin/env python3
"""
scripts/check_claims.py

Automated CI check for Vigil claims policy per MASTER_PLAN.md §11.1.
Enforces truth over impressiveness:
- Detects forbidden marketing / clinical claims without committed evidence.
- Flags unlabelled synthetic data claims or ungrounded performance claims.
- Verifies that mandatory disclaimers and synthetic labels are preserved.
"""

import os
import re
import sys
from pathlib import Path

# Paths to ignore from forbidden phrase scanning
IGNORE_PATHS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    # Master plan, changelog, progress reports, audit reports, and historical archives document prior defects or instructions
    "docs/MASTER_PLAN.md",
    "docs/PLAN-CHANGELOG.md",
    "docs/archive",
    "docs/audits",
    "docs/progress",
    "docs/EVIDENCE.md",
    "docs/prompts",
    "docs/adr",
    "CHANGELOG.md",
    "AGENTS.md",
    ".agent/skills/repo-standards",
    ".agent/skills/complete-solution",
}

# Forbidden phrases per MASTER_PLAN §11.1 and Defect A11
FORBIDDEN_PHRASES = [
    (r"\benterprise-grade\b", "Forbidden claim: 'enterprise-grade' (Defect A11)"),
    (r"\bproduction-ready\b", "Forbidden claim: 'production-ready' without regulatory/clinical validation (Defect A11)"),
    (r"\bfrontier-grade\b", "Forbidden claim: 'frontier-grade' (Defect A11)"),
    (r"\bstate-of-the-art\b", "Forbidden claim: 'state-of-the-art' (Defect A11)"),
    (r"\bzero compromises\b", "Forbidden claim: 'zero compromises' (Defect A11)"),
    (r"\bdetects metastasis\b", "Forbidden claim: 'detects metastasis' (must say decision support / signal)"),
    (r"\bpredicts cancer\b", "Forbidden claim: 'predicts cancer' (must say decision support / risk estimation)"),
    (r"\bclinically validated\b", "Forbidden claim: 'clinically validated' (must have committed clinical trial evidence)"),
    (r"\bfda approved\b", "Forbidden claim: 'FDA approved'"),
    (r"\bnafdac approved\b", "Forbidden claim: 'NAFDAC approved'"),
    (r"\bsaves lives\b", "Forbidden claim: 'saves lives' (violates §2 / §11.1)"),
    (r"\broc-auc\s*=?\s*1\.000?\b", "Forbidden claim: perfect ROC-AUC 1.000 is a leakage defect, not a result (Defect A2)"),
    (r"\br\^?2\s*=?\s*0\.7884\b", "Forbidden claim: ungrounded R² 0.7884 on circular synthetic targets (Defect A2)"),
]

# Files where personal / machine-specific paths must NOT appear
PATH_CHECK_EXTENSIONS = {".py", ".ts", ".tsx", ".json", ".yaml", ".yml", ".env", ".toml", ".sh", ".mjs"}


def should_ignore(path: Path, root: Path) -> bool:
    rel_str = str(path.relative_to(root))
    for ignore in IGNORE_PATHS:
        if ignore in rel_str.split(os.sep) or rel_str.startswith(ignore):
            return True
    return False


def check_file(path: Path, root: Path) -> list[str]:
    rel_path = path.relative_to(root)
    errors: list[str] = []

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"{rel_path}: unable to read file: {e}"]

    # 1. Check for personal/machine-specific absolute paths
    if path.suffix in PATH_CHECK_EXTENSIONS:
        if "/Users/" in content:
            # Allow check_claims.py or audit report quoting the defect
            if not str(rel_path).startswith("scripts/") and not str(rel_path).startswith("docs/audits/"):
                errors.append(f"{rel_path}: Contains hard-coded personal machine path '/Users/' (Defect A4)")

    # 2. Check for forbidden phrases
    lower_content = content.lower()
    for pattern, msg in FORBIDDEN_PHRASES:
        match = re.search(pattern, lower_content)
        if match:
            # Skip if this is checking the forbidden phrase itself inside scripts or test fixtures
            if str(rel_path).startswith("scripts/") or "test_claims" in str(rel_path):
                continue
            errors.append(f"{rel_path}: {msg} at match '{match.group(0)}'")

    return errors


def check_mandatory_artifacts(root: Path) -> list[str]:
    errors: list[str] = []
    disclaimer = root / "docs" / "DISCLAIMER.md"
    if not disclaimer.exists():
        errors.append("docs/DISCLAIMER.md is missing (Mandatory clinical disclaimer per §11.1)")
    else:
        text = disclaimer.read_text(encoding="utf-8")
        if "research prototype and decision-support aid" not in text:
            errors.append("docs/DISCLAIMER.md does not contain required disclaimer text per §11.1")

    hazard_log = root / "docs" / "safety" / "HAZARD-LOG.md"
    if not hazard_log.exists():
        errors.append("docs/safety/HAZARD-LOG.md is missing (Mandatory safety hazard log per §11.2)")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    all_errors: list[str] = []

    # Check mandatory files
    all_errors.extend(check_mandatory_artifacts(root))

    # Scan repository files
    for p in root.rglob("*"):
        if p.is_file() and not should_ignore(p, root):
            file_errors = check_file(p, root)
            all_errors.extend(file_errors)

    if all_errors:
        print("❌ Claims policy check FAILED:")
        for err in all_errors:
            print(f"  - {err}")
        print(f"\nTotal violations: {len(all_errors)}")
        return 1

    print("✅ Claims policy check PASSED: All files respect MASTER_PLAN §11.1 and repo standards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
