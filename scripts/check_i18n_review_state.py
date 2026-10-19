#!/usr/bin/env python3
"""scripts/check_i18n_review_state.py

Enforces MASTER_PLAN §10.4 / Tier 2 localisation:

- Every UI string key in packages/ui/src/i18n/translations/*.ts is listed in
  packages/ui/i18n/review_state.json.
- Non-English locales (pcm, yo, ha, ig) stay status=unreviewed unless every
  string and glossary term for that locale is reviewed *and* reviewed_by is set.
- metadata.isReviewed in each translation file matches the locale status.
- Glossary terms exist for every supported locale.

Fails CI if review state is missing, stale, or claims a review that did not happen.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANS = ROOT / "packages" / "ui" / "src" / "i18n" / "translations"
REVIEW_PATH = ROOT / "packages" / "ui" / "i18n" / "review_state.json"
GLOSSARY_PATH = ROOT / "packages" / "ui" / "i18n" / "glossary" / "terms.json"
LOCALES = ("en-NG", "pcm", "yo", "ha", "ig")
NON_SOURCE = ("pcm", "yo", "ha", "ig")
META_SKIP = {"metadata.code", "metadata.name", "metadata.nativeName", "metadata.isReviewed"}
FILES = {
    "en-NG": TRANS / "en-NG.ts",
    "pcm": TRANS / "pcm.ts",
    "yo": TRANS / "yo.ts",
    "ha": TRANS / "ha.ts",
    "ig": TRANS / "ig.ts",
}


def extract_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    stack: list[str] = []
    for line in path.read_text().splitlines():
        if "//" in line:
            line = line.split("//")[0]
        if re.match(r"^\s*\},?\s*$", line):
            if stack:
                stack.pop()
            continue
        m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\{", line)
        if m:
            stack.append(m.group(2))
            continue
        m = re.match(
            r'^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*("(?:\\.|[^"\\])*"|true|false)',
            line,
        )
        if m:
            key = ".".join(stack + [m.group(2)])
            if key not in META_SKIP:
                keys.add(key)
    return keys


def metadata_is_reviewed(path: Path) -> bool:
    text = path.read_text()
    m = re.search(r"isReviewed\s*:\s*(true|false)", text)
    if not m:
        raise SystemExit(f"❌ {path}: missing metadata.isReviewed")
    return m.group(1) == "true"


def main() -> int:
    errors: list[str] = []
    if not REVIEW_PATH.exists():
        print(f"❌ missing {REVIEW_PATH}")
        return 1
    if not GLOSSARY_PATH.exists():
        print(f"❌ missing {GLOSSARY_PATH}")
        return 1

    review = json.loads(REVIEW_PATH.read_text())
    glossary = json.loads(GLOSSARY_PATH.read_text())
    if review.get("schema") != "vigil-i18n-review-v1":
        errors.append("review_state.json schema must be vigil-i18n-review-v1")
    if glossary.get("schema") != "vigil-medical-glossary-v1":
        errors.append("glossary/terms.json schema must be vigil-medical-glossary-v1")

    per_keys = {loc: extract_keys(path) for loc, path in FILES.items()}
    en_keys = per_keys["en-NG"]
    for loc in NON_SOURCE:
        missing = en_keys - per_keys[loc]
        if missing:
            errors.append(f"{loc}: missing UI keys present in en-NG: {sorted(missing)[:8]}")

    all_keys = set().union(*per_keys.values())
    stated_keys = set(review.get("string_keys", {}))
    if all_keys != stated_keys:
        errors.append(
            "string_keys in review_state.json do not match translation files: "
            f"missing={sorted(all_keys - stated_keys)[:8]} "
            f"extra={sorted(stated_keys - all_keys)[:8]}"
        )

    for loc in LOCALES:
        loc_meta = review.get("locales", {}).get(loc)
        if not loc_meta:
            errors.append(f"locales.{loc} missing from review_state.json")
            continue
        status = loc_meta.get("status")
        file_reviewed = metadata_is_reviewed(FILES[loc])
        if status == "reviewed" and not file_reviewed:
            errors.append(f"{loc}: review_state says reviewed but metadata.isReviewed is false")
        if status == "unreviewed" and file_reviewed:
            errors.append(f"{loc}: metadata.isReviewed is true but review_state says unreviewed")
        if loc in NON_SOURCE and status == "reviewed":
            # A non-source locale may only be reviewed if every present string and glossary term
            # is reviewed and a reviewer is named.
            if not loc_meta.get("reviewed_by"):
                errors.append(f"{loc}: status=reviewed but reviewed_by is empty")
            for key, statuses in review.get("string_keys", {}).items():
                st = statuses.get(loc)
                if st not in ("reviewed", "absent"):
                    errors.append(f"{loc}: string_keys.{key} is {st!r} while locale is reviewed")
            for term_id, statuses in review.get("glossary_terms", {}).items():
                if statuses.get(loc) != "reviewed":
                    errors.append(f"{loc}: glossary_terms.{term_id} is not reviewed")

    # Non-source locales must not silently claim reviewed strings without a locale review.
    for loc in NON_SOURCE:
        loc_status = review.get("locales", {}).get(loc, {}).get("status")
        if loc_status != "unreviewed":
            continue
        for key, statuses in review.get("string_keys", {}).items():
            st = statuses.get(loc)
            if st == "reviewed":
                errors.append(
                    f"{loc}: string_keys.{key}=reviewed while locale is unreviewed "
                    "(flip the locale only after H-118)"
                )
        for term_id, statuses in review.get("glossary_terms", {}).items():
            if statuses.get(loc) == "reviewed":
                errors.append(
                    f"{loc}: glossary_terms.{term_id}=reviewed while locale is unreviewed"
                )

    terms = glossary.get("terms") or []
    term_ids = {t.get("id") for t in terms}
    stated_terms = set(review.get("glossary_terms", {}))
    if term_ids != stated_terms:
        errors.append(
            f"glossary term ids != review_state glossary_terms: "
            f"{sorted(term_ids ^ stated_terms)}"
        )
    for term in terms:
        tid = term.get("id")
        for loc in LOCALES:
            entry = term.get(loc)
            if not isinstance(entry, dict) or "label" not in entry or "definition" not in entry:
                errors.append(f"glossary term {tid}: missing {loc}.label/definition")
            elif loc in NON_SOURCE and "[UNREVIEWED DRAFT]" not in str(entry.get("definition", "")):
                # Keep the honesty marker until H-118 flips the status.
                if review.get("glossary_terms", {}).get(tid, {}).get(loc) == "unreviewed":
                    errors.append(
                        f"glossary term {tid}/{loc}: unreviewed definition must contain "
                        "[UNREVIEWED DRAFT]"
                    )

    if errors:
        print("❌ i18n review-state check failed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(
        f"✅ i18n review-state OK: {len(all_keys)} UI keys, "
        f"{len(term_ids)} glossary terms; non-English locales remain unreviewed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
