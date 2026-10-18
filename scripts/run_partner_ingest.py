#!/usr/bin/env python3
"""Validate a partner extraction (CSV folder or Excel workbook) and write the rejection report.

Run this *inside the hospital* before anything is sent (docs/clinical/PARTNERSHIP/DEIDENTIFICATION-CHECKLIST.md).

Exit codes: 0 accepted; 1 refused as a whole (direct identifier or schema); 2 rejection rate above the stop rate.
Outputs in --out: ingest_report.json, ingest_report.md, and (unless refused) clean_<table>.csv, flagged_labs.csv.
The stop rate defaults to the ratified PR-07 when docs/clinical/PREREG-FREEZE.json exists, else to the PROPOSED
value of PREREGISTRATION.md (0.10) and says so.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_prereg_freeze import FREEZE, PREREG, parameters  # noqa: E402
from contracts.partner import PartnerIngestAborted, ingest_path, render_markdown  # noqa: E402


def stop_rate() -> tuple[float, str]:
    if FREEZE.exists():
        rec = json.loads(FREEZE.read_text(encoding="utf-8"))
        for r in rec.get("ratifications", []):
            if r.get("id") == "PR-07":
                return float(r["value"]), "ratified PR-07"
    proposed = parameters(PREREG.read_text(encoding="utf-8")).get("PR-07", "0.10")
    return float(proposed), "PROPOSED PR-07 (pre-registration not frozen)"


def write_csv(path: Path, rows: list[dict]) -> None:
    cols = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("input", type=Path, help="folder with the four CSV files, or an .xlsx workbook")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--stop-rate", type=float, default=None, help="override (default: PR-07)")
    args = ap.parse_args(argv)
    rate, source = (args.stop_rate, "command line") if args.stop_rate is not None else stop_rate()
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        res = ingest_path(args.input, rate)
    except PartnerIngestAborted as exc:
        (args.out / "ingest_report.json").write_text(
            json.dumps(exc.report, indent=2) + "\n", encoding="utf-8"
        )
        (args.out / "ingest_report.md").write_text(render_markdown(exc.report), encoding="utf-8")
        print(f"REFUSED as a whole: {exc}. See {args.out / 'ingest_report.md'}")
        return 1
    res.report["stop_rate_source"] = source
    (args.out / "ingest_report.json").write_text(
        json.dumps(res.report, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "ingest_report.md").write_text(render_markdown(res.report), encoding="utf-8")
    for name, rows in res.tables.items():
        write_csv(args.out / f"clean_{name}.csv", rows)
    write_csv(args.out / "flagged_labs.csv", res.flagged_labs)
    r = res.report
    print(
        f"rejection rate {r['rejection_rate']:.3f} vs stop rate {rate:.3f} ({source}); complete-case patients {r['cohort']['complete_case']}"
    )
    if r["exceeds_stop_rate"]:
        print("STOP: rejection rate exceeds the stop rate; review the extraction with the partner.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
