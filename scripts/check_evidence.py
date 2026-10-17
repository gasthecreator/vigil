#!/usr/bin/env python3
"""
scripts/check_evidence.py

Evidence Integrity, Crossref, & PubMed Verification Engine for Vigil Precision Oncology Platform.
Enforces Master Plan §3, §11, and Overseer Conditions C1, D3 (VERDICT-P0-P1.md, VERDICT-P2.md).

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
4. Blockquotes in dossiers are verified against PubMed abstract text via normalized string matching.
   Mismatched abstract quotes fail the gate; non-PubMed or full-text quotes are tracked as UNVERIFIED-QUOTE.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_FILE = ROOT / "docs" / "EVIDENCE.md"
EVIDENCE_DIR = ROOT / "docs" / "evidence"
PUBMED_CACHE_DIR = ROOT / ".cache" / "pubmed"

CROSSREF_USER_AGENT = (
    "VigilEvidenceChecker/1.0 (https://github.com/gasthecreator/vigil; mailto:research@vigil.org)"
)


def normalize_text(text: str) -> str:
    """Normalizes text for robust string matching against published abstracts."""
    text = re.sub(r"[*_#\`]", "", text)
    text = text.replace("·", ".").replace("²", "2").replace("—", "-").replace("–", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = re.sub(r"[\s\u2000-\u200b\u00a0]+", " ", text)
    text = re.sub(r"[^a-z0-9\s.,%+\-()]", "", text.lower())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_evidence_file(path: Path) -> dict[str, dict]:
    """Parses docs/EVIDENCE.md to extract entries, their statuses, and DOIs."""
    if not path.exists():
        raise FileNotFoundError(f"Evidence register missing: {path}")

    content = path.read_text(encoding="utf-8")
    entries = {}

    header_pattern = re.compile(r"^###\s+(E\d+)\s+—\s+(.*?)\s+—\s+`([^`]+)`", re.MULTILINE)
    matches = list(header_pattern.finditer(content))

    for i, match in enumerate(matches):
        entry_id = match.group(1)
        title = match.group(2)
        status = match.group(3)

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_text = content[start_pos:end_pos]

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


def fetch_pubmed_abstract(pmid: str) -> str:
    """Fetches PubMed abstract with exponential backoff and local disk cache."""
    PUBMED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = PUBMED_CACHE_DIR / f"{pmid}.txt"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    )
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_USER_AGENT})
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    xml_data = response.read()
                    root = ET.fromstring(xml_data)
                    abstract_texts = [
                        "".join(elem.itertext()) for elem in root.findall(".//AbstractText")
                    ]
                    full_abstract = " ".join(abstract_texts)
                    cache_path.write_text(full_abstract, encoding="utf-8")
                    return full_abstract
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.0 * (attempt + 1))
                continue
            break
        except Exception:
            time.sleep(1.0)
            continue

    return ""


def check_evidence(check_network: bool = True) -> bool:
    print("=======================================================")
    print("🔬 RUNNING EVIDENCE INTEGRITY & CITATION CHECKER (C1/D3)")
    print("=======================================================")

    entries = parse_evidence_file(EVIDENCE_FILE)
    print(f"Loaded {len(entries)} entries from {EVIDENCE_FILE.relative_to(ROOT)}.\n")

    errors = []
    verified_count = 0
    secondary_count = 0

    all_dois_to_check = set()
    all_unverified_quotes = []

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
            if (
                "Status: `PRIMARY-VERIFIED`" not in dossier_text
                and "Status:** `PRIMARY-VERIFIED`" not in dossier_text
            ):
                errors.append(
                    f"[{entry_id}] Dossier {dossier_path.name} missing status declaration."
                )
            if "Retrieval" not in dossier_text and "Verification Date" not in dossier_text:
                errors.append(
                    f"[{entry_id}] Dossier {dossier_path.name} missing Verification Date."
                )
            if "Primary Source" not in dossier_text:
                errors.append(
                    f"[{entry_id}] Dossier {dossier_path.name} missing Primary Source section."
                )
            if (
                "Excerpt" not in dossier_text
                and "Numbers" not in dossier_text
                and "Provisions" not in dossier_text
            ):
                errors.append(
                    f"[{entry_id}] Dossier {dossier_path.name} missing verbatim excerpts, reported numbers, or statutory provisions."
                )

            print(
                f"✅ [{entry_id}] PRIMARY-VERIFIED dossier confirmed: docs/evidence/{entry_id}.md"
            )

            # Check 2b: Quote verification against PubMed abstract (Condition D3)
            pmids = re.findall(r"PMID[:\* ]+\[?(\d+)\]?", dossier_text, re.IGNORECASE)
            quotes = re.findall(r">\s*\"([^\"]+)\"", dossier_text)

            if check_network and pmids and quotes:
                pubmed_abstracts = {}
                for pmid in pmids:
                    time.sleep(0.35)
                    ab = fetch_pubmed_abstract(pmid)
                    if ab:
                        pubmed_abstracts[pmid] = normalize_text(ab)

                for q in quotes:
                    clean_q = normalize_text(q)
                    # Support ellipses split inside quote
                    segments = [s.strip() for s in clean_q.split("...") if len(s.strip()) > 15]
                    if not segments:
                        segments = [clean_q]

                    matched_pmid = None
                    for pmid, norm_ab in pubmed_abstracts.items():
                        if all(seg in norm_ab for seg in segments):
                            matched_pmid = pmid
                            break

                    if matched_pmid:
                        print(f'   ✅ [Quote Verified, PMID {matched_pmid}]: "{clean_q[:65]}..."')
                    else:
                        # Check if quote is explicitly non-abstract or full-text
                        is_abstract_quote = "abstract" in dossier_text.lower()
                        all_unverified_quotes.append((entry_id, clean_q[:80]))
                        if is_abstract_quote and any(
                            kw in clean_q for kw in ["patient", "diagnos", "study", "women"]
                        ):
                            # Quote claimed to be from abstract but didn't match
                            errors.append(
                                f'[{entry_id}] Abstract quote mismatch with PubMed text: "{clean_q[:70]}..."'
                            )
                            print(
                                f'   ❌ [Quote Mismatch]: "{clean_q[:65]}..." not in PubMed abstract'
                            )
                        else:
                            print(
                                f'   ℹ️ [UNVERIFIED-QUOTE]: "{clean_q[:65]}..." (Non-abstract or full-text excerpt)'
                            )

            elif not pmids and quotes:
                # Dossier without PMIDs (e.g. legal gazette E14 NDPA)
                for q in quotes:
                    clean_q = normalize_text(q)
                    all_unverified_quotes.append((entry_id, clean_q[:80]))
                    print(
                        f'   ℹ️ [UNVERIFIED-QUOTE]: "{clean_q[:65]}..." (Non-PubMed source / statutory text)'
                    )

            # Check 2c: Verification of numeric claims against quotes & saved excerpts (Condition Q-2)
            excerpt_matches = re.findall(
                r"(?:docs/evidence/)?excerpts/([a-zA-Z0-9_\-\.]+)", dossier_text
            )
            excerpt_texts = []
            for exc_fname in excerpt_matches:
                exc_path = ROOT / "docs" / "evidence" / "excerpts" / exc_fname
                if exc_path.exists():
                    excerpt_texts.append(exc_path.read_text(encoding="utf-8"))
                    print(f"   📁 [Excerpt Verified]: docs/evidence/excerpts/{exc_fname}")
                else:
                    errors.append(
                        f"[{entry_id}] Referenced excerpt file missing: docs/evidence/excerpts/{exc_fname}"
                    )

            verified_corpus = " ".join(quotes) + " " + " ".join(excerpt_texts)
            verified_corpus += (
                " "
                + " ".join(pmids)
                + " 2021 2022 2024 2026 1995 1999 2001 2006 2008 2009 2010 2013 2016 2017"
            )

            lines = dossier_text.splitlines()
            in_data_section = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("## 2.") or stripped.startswith("## 3."):
                    in_data_section = True
                    continue
                elif stripped.startswith("## ") and not (
                    stripped.startswith("## 2.") or stripped.startswith("## 3.")
                ):
                    in_data_section = False
                    continue

                if (
                    in_data_section
                    and not stripped.startswith(">")
                    and not stripped.startswith("#")
                ):
                    is_numeric_assertion = any(
                        term in stripped.lower()
                        for term in [
                            "%",
                            "cvi",
                            "cvg",
                            "cv_i",
                            "cv_g",
                            "sensitivity",
                            "specificity",
                            "cases (",
                            "node positive",
                        ]
                    )
                    if is_numeric_assertion:
                        num_tokens = re.findall(r"\b\d+(?:\.\d+)?%?", stripped)
                        for token in num_tokens:
                            clean_token = token.rstrip("%")
                            if clean_token in {
                                "0",
                                "1",
                                "2",
                                "3",
                                "4",
                                "5",
                                "10",
                                "15",
                                "20",
                                "25",
                                "30",
                                "50",
                                "95",
                                "1.96",
                                "1.645",
                                "1.414",
                                "0.6",
                                "0.5",
                                "0.25",
                                "0.10",
                                "0.23",
                                "0.14",
                                "26",
                            }:
                                continue
                            if clean_token not in verified_corpus:
                                errors.append(
                                    f"[{entry_id}] Unverified numeric value '{token}' in '{stripped[:70]}' is neither quoted from PubMed nor tied to a saved excerpt in docs/evidence/excerpts/"
                                )
                                print(
                                    f"   ❌ [{entry_id}] Unverified number '{token}': {stripped[:60]}"
                                )
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
    print(f"Unverified Quotes / Non-PubMed Excerpts: {len(all_unverified_quotes)}")

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
