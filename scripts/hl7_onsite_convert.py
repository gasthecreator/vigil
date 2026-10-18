#!/usr/bin/env python3
"""Convert HL7 v2 ORU^R01 messages to lab_observations.csv rows. RUN INSIDE THE HOSPITAL ONLY.

Inputs that never leave the site:
  * the HL7 message file (messages separated by a blank line);
  * a JSON map {local patient id: "YYYY-MM-DD" diagnosis date};
  * the pseudonym secret, read from the environment variable VIGIL_PSEUDONYM_SECRET (at least 16 bytes).
Only the output CSV (pseudonym, relative day) and the reason-code summary are exported.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from contracts.partner.hl7_onsite import convert_messages, hmac_pseudonym  # noqa: E402

COLS = [
    "patient_id",
    "observation_day",
    "analyte_code",
    "analyte_name",
    "value_numeric",
    "unit_ucum",
    "ref_low",
    "ref_high",
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("messages", type=Path)
    ap.add_argument("--index-dates", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="lab_observations.csv to write")
    args = ap.parse_args(argv)
    secret = os.environ.get("VIGIL_PSEUDONYM_SECRET", "").encode("utf-8")
    try:
        pseud = hmac_pseudonym(secret)
    except ValueError as exc:
        print(f"error: {exc} (set VIGIL_PSEUDONYM_SECRET)", file=sys.stderr)
        return 1
    idx = {
        k: date.fromisoformat(v)
        for k, v in json.loads(args.index_dates.read_text(encoding="utf-8")).items()
    }
    msgs = [m for m in args.messages.read_text(encoding="utf-8").split("\n\n") if m.strip()]
    rows, rejected = convert_messages(msgs, idx, pseud)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(
        f"converted {len(rows)} results from {len(msgs)} messages; not converted: {dict(Counter(r['code'] for r in rejected))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
