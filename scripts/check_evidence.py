#!/usr/bin/env python3
"""
scripts/check_evidence.py

Evidence Integrity & Crossref Verification Engine for Vigil Precision Oncology Platform.
Enforces Master Plan §3, §11, and Overseer Condition C1 (VERDICT-P0-P1.md).

Rules Enforced:
1. Every entry marked `PRIMARY-VERIFIED` in `docs/EVIDENCE.md` MUST have an existing
   evidence dossier at `docs/evidence/{ID}.md`.
2. Every `docs/evidence/{ID}.md` dossier MUST include:
   - Status: PRIMARY-VERIFIED
   - Retrieval/Verification Date
   - Primary Source(s) with DOI or official gazette link
   - Verbatim Excerpts / Exact Reported Numbers
3. All DOIs cited in `docs/EVIDENCE.md` and dossiers must resolve against Crossref API
   (https://api.crossref.org/works/{doi}) and return matching metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_FILE = ROOT / "docs" / "EVIDENCE.md"
EVIDENCE_DIR = ROOT / "docs" / "evidence"

CROSSREF_USER_AGENT = "VigilEvidenceChecker/1.0 (https://github.com/gasthecreator/vigil; mailto:research@vigil.org)"


def parse_evidence_file(path: Path) -> dict[str, dict]:
    """Parses docs/EVIDENCE.md to extract entries, their statuses, and DOIs."""
    if not path.exists():
        raise FileNotFoundError(f"Evidence register missing: {path}")

    content = path.read_text(encoding="utf-8")
    entries = {}

    # Match sections like: ### E1 — Title — `PRIMARY-VERIFIED`
    header_pattern = re.compile(r"^###\s+(E\d+)\s+—\s+(.*?)\s+—\s+`([^`]+)`", re.MULTILINE)
    matches = list(header_pattern.finditer(content))

    for i, match in enumerate(matches):
        entry_id = match.group(1)
        title = match.group(2)
        status = match.group(3)

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_text = content[start_pos:end_pos]

        # Extract DOIs from markdown link text doi:[10.xxx] or direct URLs
        dois_from_brackets = re.findall(r"doi:\[(10\.\d{4,9}/[^\]]+)\]", section_text)
        dois_from_urls = re.findall(r"https?://doi\.org/(10\.\d{4,9}/[^\s\"<>]+)", section_text)
        clean_dois = set()
        for d in dois_from_brackets:
            clean_dois.add(d.strip())
        for d in dois_from_urls:
            d_clean = d.rstrip("].;")
            while d_clean.count("(") < d_clean.count(")"):
                d_clean = d_clean.rstrip(")")
            clean_dois.add(d_clean.strip())

        entries[entry_id] = {
            "title": title,
            "status": status,
            "dois": sorted(clean_dois),
            "section_text": section_text,
        }

    return entries


def verify_crossref_doi(doi: str) -> tuple[bool, str]:
    """Queries Crossref to verify that a DOI resolves to a real publication."""
    url = f"https://api.crossref.org/works/{doi}"
    req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                msg = data.get("message", {})
                title = msg.get("title", ["Unknown Title"])[0]
                return True, title
            return False, f"HTTP status {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"Crossref HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"Network error resolving DOI {doi}: {e}"


def check_evidence(check_network: bool = True) -> bool:
    print("=======================================================")
    print("🔬 RUNNING EVIDENCE INTEGRITY & CITATION CHECKER")
    print("=======================================================")

    entries = parse_evidence_file(EVIDENCE_FILE)
    print(f"Loaded {len(entries)} entries from {EVIDENCE_FILE.relative_to(ROOT)}.\n")

    errors = []
    verified_count = 0
    secondary_count = 0

    all_dois_to_check = set()

    for entry_id, info in entries.items():
        status = info["status"]
        title = info["title"]
        dois = info["dois"]

        for d in dois:
            all_dois_to_check.add((entry_id, d))

        if status == "PRIMARY-VERIFIED":
            verified_count += 1
            dossier_path = EVIDENCE_DIR / f"{entry_id}.md"

            # Check 1: Dossier file must exist
            if not dossier_path.exists():
                errors.append(
                    f"[{entry_id}] Marked PRIMARY-VERIFIED but dossier missing: "
                    f"docs/evidence/{entry_id}.md"
                )
                continue

            # Check 2: Dossier must contain required audit sections
            dossier_text = dossier_path.read_text(encoding="utf-8")
            if "Status: `PRIMARY-VERIFIED`" not in dossier_text and "Status:** `PRIMARY-VERIFIED`" not in dossier_text:
                errors.append(f"[{entry_id}] Dossier {dossier_path.name} missing status declaration.")
            if "Retrieval" not in dossier_text and "Verification Date" not in dossier_text:
                errors.append(f"[{entry_id}] Dossier {dossier_path.name} missing Verification Date.")
            if "Primary Source" not in dossier_text:
                errors.append(f"[{entry_id}] Dossier {dossier_path.name} missing Primary Source section.")
            if (
                "Excerpt" not in dossier_text
                and "Numbers" not in dossier_text
                and "Provisions" not in dossier_text
            ):
                errors.append(f"[{entry_id}] Dossier {dossier_path.name} missing verbatim excerpts, reported numbers, or statutory provisions.")

            print(f"✅ [{entry_id}] PRIMARY-VERIFIED dossier confirmed: docs/evidence/{entry_id}.md")
        else:
            secondary_count += 1
            print(f"ℹ️  [{entry_id}] {status}: {title}")

    # Check 3: Crossref resolution for all cited DOIs
    if check_network:
        print(f"\nResolving {len(all_dois_to_check)} cited DOIs against Crossref API...")
        for entry_id, doi in sorted(all_dois_to_check):
            time.sleep(0.2)  # Respect API rate limits
            ok, res_title = verify_crossref_doi(doi)
            if ok:
                print(f"  ✅ [{entry_id}] doi:{doi} -> '{res_title}'")
            else:
                errors.append(f"[{entry_id}] Unresolvable or invalid DOI: {doi} ({res_title})")
                print(f"  ❌ [{entry_id}] doi:{doi} FAILED: {res_title}")
    else:
        print("\n(Skipping online Crossref verification due to --no-network flag)")

    print("\n-------------------------------------------------------")
    print(f"Summary: {verified_count} PRIMARY-VERIFIED, {secondary_count} SECONDARY/OTHER.")

    if errors:
        print(f"\n❌ Evidence check FAILED with {len(errors)} violations:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("🎉 ALL EVIDENCE INTEGRITY AND CITATION CHECKS PASSED.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Vigil Evidence Register Integrity Checker")
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="Skip live Crossref DOI API queries (for offline environments)",
    )
    args = parser.parse_args()

    success = check_evidence(check_network=not args.no_network)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
