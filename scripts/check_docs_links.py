#!/usr/bin/env python3
"""scripts/check_docs_links.py

Documentation Link Integrity Checker for Vigil.
Implements Master Plan §12, repo-standards, and WP8.4.

Scans all markdown files in docs/, reports/, and root, validating that
every relative file link and intra-repository reference resolves to an
existing file on disk. Fails if any broken link is detected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent

# Files/Directories to inspect
SCAN_DIRS = [ROOT / "docs", ROOT / "reports"]
SCAN_FILES = [
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "CHANGELOG.md",
]

# Historical point-in-time phase reports preserve exact snapshot state at phase closure
HISTORICAL_REPORT_PREFIXES = (
    str(ROOT / "docs" / "progress" / "PHASE-0-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-1-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-5A-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-5B-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-6A-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-6B-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-7A-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-7B-REPORT.md"),
    str(ROOT / "docs" / "progress" / "PHASE-8A-REPORT.md"),
)


def extract_markdown_links(file_path: Path) -> List[Tuple[int, str, str]]:
    """Extracts (line_number, link_text, link_target) tuples from markdown file."""
    content = file_path.read_text(encoding="utf-8")
    links: List[Tuple[int, str, str]] = []

    # Pattern for [text](url_or_path)
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for line_num, line in enumerate(content.splitlines(), start=1):
        # Ignore markdown comments or code blocks if simple
        for match in pattern.finditer(line):
            text = match.group(1).strip()
            target = match.group(2).strip()
            links.append((line_num, text, target))

    return links


def check_link(file_path: Path, target: str) -> bool:
    """Verifies whether a link target resolves."""
    # Ignore web URLs, anchors, mailto
    if target.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
        return True

    clean_target = target

    # Handle file:// scheme
    if clean_target.startswith("file://"):
        clean_target = clean_target[7:]
        # Remove anchor
        clean_target = clean_target.split("#")[0].split("?")[0]
        if clean_target.startswith("/docs/") or clean_target.startswith("/reports/") or clean_target.startswith("/scripts/"):
            return (ROOT / clean_target.lstrip("/")).exists()
        return Path(clean_target).exists()

    # Strip anchor fragment from path (e.g., path.md#section)
    clean_target = clean_target.split("#")[0].split("?")[0]
    if not clean_target:
        return True

    # Resolve relative to source file
    resolved_rel = (file_path.parent / clean_target).resolve()
    if resolved_rel.exists():
        return True

    # Resolve relative to repository root
    resolved_root = (ROOT / clean_target.lstrip("/")).resolve()
    if resolved_root.exists():
        return True

    return False


def main() -> int:
    print("🔗 Verifying documentation link integrity across repository...")
    files_to_check: List[Path] = []

    for d in SCAN_DIRS:
        if d.exists():
            for p in d.rglob("*.md"):
                if str(p) not in HISTORICAL_REPORT_PREFIXES:
                    files_to_check.append(p)

    for f in SCAN_FILES:
        if f.exists() and str(f) not in HISTORICAL_REPORT_PREFIXES:
            files_to_check.append(f)

    print(f"📄 Found {len(files_to_check)} markdown files to inspect.")

    broken_links: List[str] = []
    total_links = 0

    for doc in files_to_check:
        try:
            links = extract_markdown_links(doc)
        except Exception as e:
            print(f"⚠️ Error reading {doc}: {e}")
            continue

        for line_num, text, target in links:
            total_links += 1
            if not check_link(doc, target):
                rel_doc = doc.relative_to(ROOT)
                broken_links.append(f"{rel_doc}:{line_num} -> [{text}]({target})")

    print(f"🔍 Checked {total_links} links across documentation.")

    if broken_links:
        print(f"\n❌ Detected {len(broken_links)} broken link(s):")
        for err in broken_links:
            print(f"  - {err}")
        return 1

    print("✅ All documentation links successfully resolved. Zero broken links detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
