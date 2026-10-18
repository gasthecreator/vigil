#!/usr/bin/env python3
"""Operator tool for silent mode (docs/clinical/PREREGISTRATION.md section 6; docs/clinical/SILENT-MODE.md).

  report           build the monitoring report from the SHADOW STORE ONLY (alarm rate, calibration drift, conformal
                   coverage, data shift) and write silent_monitoring_report.{md,json} to --out.
  import-outcomes  load steward-supplied outcomes (CSV: patient_id,event_type,event_time) into the shadow store.

Parameters:
  real use         the pre-registration must be frozen (scripts/check_prereg_freeze.py); the ratified values of
                   PR-01, PR-02, PR-04, PR-08, PR-09 come from docs/clinical/PREREG-FREEZE.json.
  --synthetic-dry-run   PROPOSED values of PREREGISTRATION.md, PR-04 from --alert-budget (it has no default); the
                   report is labelled as a rehearsal on unratified parameters.

Exit codes (report): 0 no breach and every monitor evaluable; 3 breach (start the review in
docs/clinical/PILOT/STOP-RULES.md); 4 pre-registration not frozen; 5 no breach but a monitor could not be evaluated.
The shadow store URL comes from --shadow-url or VIGIL_SILENT_SHADOW_DATABASE_URL.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "apps" / "api"))

import check_prereg_freeze as gate  # noqa: E402
import run_partner_evaluation as evaluation  # noqa: E402
from vigil_api import silent_monitoring as sm  # noqa: E402
from vigil_api.shadow_store import ShadowStore  # noqa: E402


def parameters(dry_run: bool, alert_budget: float | None) -> sm.Parameters:
    if dry_run:
        proposed = gate.parameters(gate.PREREG.read_text(encoding="utf-8"))
        values = {k: evaluation._num(v) for k, v in proposed.items() if k != "PR-04"}
        provenance = "PROPOSED values of PREREGISTRATION.md (not ratified); rehearsal only"
    else:
        problems = gate.check()
        if problems:
            print("pre-registration is not frozen:\n  " + "\n  ".join(problems), file=sys.stderr)
            raise SystemExit(4)
        record = json.loads(gate.FREEZE.read_text(encoding="utf-8"))
        values = {r["id"]: evaluation._num(str(r["value"])) for r in record["ratifications"] if r["id"] != "PR-04"}
        budget_row = next((r for r in record["ratifications"] if r["id"] == "PR-04"), None)
        alert_budget = alert_budget if alert_budget is not None else (evaluation._num(str(budget_row["value"])) if budget_row else None)
        provenance = "ratified values in PREREG-FREEZE.json"
    return sm.Parameters(
        slope_low=values["PR-01"], slope_high=values["PR-02"], alert_budget=alert_budget,
        min_window=int(values["PR-08"]), coverage_shortfall=values["PR-09"], provenance=provenance,
    )


def open_store(url: str | None) -> ShadowStore:
    url = url or os.environ.get("VIGIL_SILENT_SHADOW_DATABASE_URL", "")
    if not url:
        raise SystemExit("no shadow store: pass --shadow-url or set VIGIL_SILENT_SHADOW_DATABASE_URL")
    return ShadowStore(url)


def cmd_report(args: argparse.Namespace) -> int:
    if args.synthetic_dry_run and args.alert_budget is None:
        raise SystemExit("--alert-budget is required with --synthetic-dry-run (PR-04 has no proposed default)")
    params = parameters(args.synthetic_dry_run, args.alert_budget)
    store = open_store(args.shadow_url)
    report = sm.build_report(store, params)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "silent_monitoring_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    md = sm.render_markdown(report)
    if args.synthetic_dry_run:
        md = "> **REHEARSAL on unratified parameters. Not a monitoring result.**\n\n" + md
    (out / "silent_monitoring_report.md").write_text(md, encoding="utf-8")
    print(f"wrote {out / 'silent_monitoring_report.md'}")
    if report["breach"]:
        return 3
    return 5 if report["incomplete"] else 0


def cmd_import(args: argparse.Namespace) -> int:
    store = open_store(args.shadow_url)
    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    report = sm.import_outcomes(store, rows, source=Path(args.csv).name)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["accepted"] > 0 or not rows else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("--shadow-url")
    r.add_argument("--out", required=True)
    r.add_argument("--synthetic-dry-run", action="store_true")
    r.add_argument("--alert-budget", type=float)
    r.set_defaults(func=cmd_report)
    i = sub.add_parser("import-outcomes")
    i.add_argument("--shadow-url")
    i.add_argument("--csv", required=True)
    i.set_defaults(func=cmd_import)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
