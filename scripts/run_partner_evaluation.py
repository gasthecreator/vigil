#!/usr/bin/env python3
"""Pre-registered partner evaluation (docs/clinical/PREREGISTRATION.md; definitions in docs/clinical/ANALYSIS-SPEC.md).

Real data:   refuses to run unless the pre-registration is frozen (scripts/check_prereg_freeze.py), reads the ratified
             parameters, bootstrap seed and partition key identifier from docs/clinical/PREREG-FREEZE.json, and takes the
             partition key from the environment variable VIGIL_PARTITION_KEY (never from a file in the repository).
Dry run:     --synthetic-dry-run rehearses the same code on SYNTHETIC data with the PROPOSED parameters. Its output is
             labelled SYNTHETIC and is never a result. It is refused unless the input folder holds the SYNTHETIC marker
             file that the synthetic-data generators write (an accident guard; real data has no such file).

Exit codes: 0 report written; 1 input refused; 2 rejection rate above the stop rate; 3 analysis not run (insufficient
data, reason in the report); 4 pre-registration not frozen; 5 test split already opened (needs --acknowledge-deviation).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_prereg_freeze as gate  # noqa: E402
import partner_analysis as pa  # noqa: E402
from contracts.partner import PartnerIngestAborted, ingest_path, render_markdown  # type: ignore[import-untyped]  # noqa: E402
from vigil_eval.audit import FrozenTestAccessLogger  # noqa: E402

DRYRUN_KEY = (
    b"synthetic-dry-run-partition-key"  # not a secret: it only partitions invented patients
)
DRYRUN_SEED = 20261018
PARAM_IDS = ["PR-0%d" % i for i in range(1, 10)]


def _num(cell: str) -> float:
    m = re.search(r"-?\d+(?:\.\d+)?", cell)
    if not m:
        raise SystemExit(f"cannot read a number from parameter value {cell!r}")
    return float(m.group(0))


def load_parameters(
    dry_run: bool, alert_budget: float | None
) -> tuple[dict[str, float], int, str, str, list[float] | None]:
    """Return ratified analysis settings, including an explicit DCA grid when frozen."""
    if dry_run:
        proposed = gate.parameters(gate.PREREG.read_text(encoding="utf-8"))
        params = {k: _num(v) for k, v in proposed.items() if k not in {"PR-04", "PR-10"}}
        if alert_budget is None:
            raise SystemExit(
                "--alert-budget is required with --synthetic-dry-run (PR-04 has no proposed default)"
            )
        params["PR-04"] = float(alert_budget)
        return (
            params,
            DRYRUN_SEED,
            "SYNTHETIC-DRYRUN-KEY",
            "PROPOSED values of PREREGISTRATION.md (not ratified); PR-04 supplied on the command line",
            None,
        )
    gate.require_frozen()
    rec = json.loads(gate.FREEZE.read_text(encoding="utf-8"))
    params = {r["id"]: _num(str(r["value"])) for r in rec["ratifications"] if r["id"] != "PR-10"}
    dca_ratification = next(r for r in rec["ratifications"] if r["id"] == "PR-10")
    dca_thresholds = json.loads(str(dca_ratification["value"]))
    return (
        params,
        int(rec["bootstrap_seed"]),
        str(rec["partition_key_id"]),
        "ratified values in PREREG-FREEZE.json",
        [float(value) for value in dca_thresholds],
    )


SYNTHETIC_MARKER = "SYNTHETIC"


def has_synthetic_marker(path: Path) -> bool:
    """Accident guard, not tamper protection: generators of invented data write a ``SYNTHETIC`` file next to it."""
    folder = path if path.is_dir() else path.parent
    f = folder / SYNTHETIC_MARKER
    return f.is_file() and "invented" in f.read_text(encoding="utf-8").lower()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--synthetic-dry-run", action="store_true")
    ap.add_argument("--alert-budget", type=float, default=None, help="PR-04, dry run only")
    ap.add_argument(
        "--n-boot", type=int, default=None, help="dry run only; the pre-registered value is 2000"
    )
    ap.add_argument(
        "--acknowledge-deviation",
        action="store_true",
        help="re-open an already opened test split; recorded as a protocol deviation",
    )
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=FutureWarning)
    dry = args.synthetic_dry_run
    if dry and not has_synthetic_marker(args.input):
        print(
            "refused: --synthetic-dry-run needs a SYNTHETIC marker file, written by a synthetic-data generator, next to the input; real data needs the frozen pre-registration",
            file=sys.stderr,
        )
        return 4
    if not dry and (args.n_boot is not None or args.alert_budget is not None):
        print(
            "refused: --n-boot and --alert-budget are dry-run options; real runs use the ratified values",
            file=sys.stderr,
        )
        return 4
    try:
        params, seed, key_id, provenance, dca_thresholds = load_parameters(dry, args.alert_budget)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 4
    n_boot = args.n_boot if (dry and args.n_boot) else 2000
    if dry:
        key = DRYRUN_KEY
    else:
        key = os.environ.get("VIGIL_PARTITION_KEY", "").encode("utf-8")
        if len(key) < 16:
            print(
                "refused: set VIGIL_PARTITION_KEY (at least 16 bytes, held by the data steward)",
                file=sys.stderr,
            )
            return 4
    args.out.mkdir(parents=True, exist_ok=True)
    tier = "SYNTHETIC DRY RUN - NOT A RESULT" if dry else "T-R retrospective partner cohort"

    try:
        ing = ingest_path(args.input, params["PR-07"])
    except PartnerIngestAborted as exc:
        (args.out / "ingest_report.md").write_text(render_markdown(exc.report), encoding="utf-8")
        (args.out / "ingest_report.json").write_text(
            json.dumps(exc.report, indent=2) + "\n", encoding="utf-8"
        )
        print(f"input refused: {exc}")
        return 1
    (args.out / "ingest_report.json").write_text(
        json.dumps(ing.report, indent=2) + "\n", encoding="utf-8"
    )
    report: dict[str, Any] = {
        "tier": tier,
        "parameters": params,
        "parameter_provenance": provenance,
        "dca_thresholds": dca_thresholds,
        "bootstrap_seed": seed,
        "bootstrap_resamples": n_boot,
        "partition_key_id": key_id,
        "data_quality": {
            k: ing.report[k]
            for k in (
                "per_table",
                "rejection_codes",
                "rejection_rate",
                "stop_rate",
                "duplicates_dropped",
                "normalised_cells",
            )
        },
        "deviations": [],
    }
    report["data_quality"]["flagged_labs"] = len(ing.report["flagged_labs"])
    report["data_quality"]["complete_case_patients"] = ing.report["cohort"]["complete_case"]

    def finish(code: int, status: str, reason: str = "") -> int:
        report["status"], report["reason"] = status, reason
        (args.out / "report.json").write_text(
            json.dumps(report, indent=2, default=float) + "\n", encoding="utf-8"
        )
        (args.out / "REPORT.md").write_text(render_report(report), encoding="utf-8")
        print(f"{status}: {reason}" if reason else status)
        return code

    if ing.report["exceeds_stop_rate"]:
        return finish(
            2,
            "STOPPED",
            f"rejection rate {ing.report['rejection_rate']:.3f} exceeds PR-07 = {params['PR-07']}; review the extraction with the partner (PREREGISTRATION section 5.6)",
        )
    try:
        lm = pa.build_landmarks(ing.tables, ing.cohort_ids)
        split = {pid: pa.assign_split(pid, key) for pid in lm.patients["patient_id"]}
        dev = lm.subset([p for p, s in split.items() if s == "dev"])
        test = lm.subset([p for p, s in split.items() if s == "test"])
        report["cohort"] = {
            **lm.counts,
            "development_patients": int(dev.first.sum()),
            "test_patients": int(test.first.sum()),
            "development_events_at_first_landmark": int(
                ((dev.E == 1) & (dev.T <= pa.HORIZON) & dev.first).sum()
            ),
            "test_events_at_first_landmark": int(
                ((test.E == 1) & (test.T <= pa.HORIZON) & test.first).sum()
            ),
        }
        plan = pa.fit_on_development(dev, alert_budget=params["PR-04"])
    except pa.InsufficientData as exc:
        return finish(3, "NOT RUN", str(exc))
    report["development"] = {
        "comparator": plan.comparator_name,
        "comparator_dev_auc_out_of_fold": plan.dev_auc,
        "recalibration_intercept": plan.recal_intercept,
        "recalibration_slope": plan.recal_slope,
        "operating_threshold": plan.threshold,
        "dev_alert_rate_per_100_patient_months": plan.dev_alert_rate,
        "notes": plan.notes,
    }

    ds = (
        "SYNTHETIC-DRYRUN-" + args.input.name
        if dry
        else "PARTNER-"
        + hashlib.sha256(
            json.dumps([i["sha256"] for i in ing.report["inputs"]]).encode()
        ).hexdigest()[:12]
    )
    logger = FrozenTestAccessLogger(args.out / "frozen_test_access_log.jsonl")
    prior = logger.get_access_history(ds)
    if prior and not args.acknowledge_deviation:
        report["status"] = "REFUSED"
        print(
            f"the test split of {ds} was already opened {len(prior)} time(s); re-run with --acknowledge-deviation to proceed as a recorded protocol deviation",
            file=sys.stderr,
        )
        return 5
    if prior:
        report["deviations"].append(
            f"test split opened again ({len(prior)} earlier access(es)); protocol deviation (PREREGISTRATION section 3)"
        )
    logger.log_access(
        ds,
        "partner_confirmatory_evaluation",
        "scripts/run_partner_evaluation.py",
        f"{tier}: C1-C3 and secondary analyses",
        int(test.first.sum()),
    )

    try:
        report["confirmatory"] = pa.confirmatory(test, plan, params, n_boot, seed)
    except pa.InsufficientData as exc:
        return finish(3, "NOT RUN", str(exc))
    report["secondary"] = pa.secondary(
        test, plan, params, n_boot, seed, dca_thresholds=dca_thresholds
    )
    return finish(0, "COMPLETED")


def _fmt(x: Any) -> str:
    return f"{x:.3f}" if isinstance(x, float) else str(x)


def render_report(r: dict[str, Any]) -> str:
    L = [
        f"# Partner evaluation report: {r['tier']}",
        "",
        f"> Written by `scripts/run_partner_evaluation.py`; do not edit by hand. Status: **{r['status']}**"
        + (f" ({r['reason']})" if r.get("reason") else "")
        + ".",
        "",
    ]
    if "SYNTHETIC" in r["tier"]:
        L += [
            "**SYNTHETIC. The data are invented. This run rehearses the code path; it is not a result and says nothing about performance on real patients.**",
            "",
        ]
    L += [
        f"Parameters: {r['parameter_provenance']}. Bootstrap: {r['bootstrap_resamples']} resamples over patients, seed {r['bootstrap_seed']}. Partition key identifier: `{r['partition_key_id']}`.",
        "",
    ]
    dq = r["data_quality"]
    L += [
        "## Data quality (PREREGISTRATION section 5.6)",
        "",
        "| table | rows in | clean | rejected | flagged |",
        "|---|---:|---:|---:|---:|",
    ]
    L += [
        f"| {t} | {v['rows_in']} | {v['rows_clean']} | {v['rows_rejected']} | {v['rows_flagged']} |"
        for t, v in dq["per_table"].items()
    ]
    L += [
        "",
        f"Rejection rate {dq['rejection_rate']:.3f} against stop rate {dq['stop_rate']}. Rejections by code: {dq['rejection_codes'] or 'none'}. Complete-case patients: {dq['complete_case_patients']}.",
        "",
    ]
    if "cohort" in r:
        L += [
            "## Cohort",
            "",
            *[f"- {k.replace('_', ' ')}: {v}" for k, v in r["cohort"].items()],
            "",
        ]
    if "development" in r:
        d = r["development"]
        L += [
            "## Development split",
            "",
            f"- comparator chosen (out-of-fold IPCW AUC): **{d['comparator']}** from "
            + ", ".join(f"{k} {_fmt(v)}" for k, v in d["comparator_dev_auc_out_of_fold"].items()),
            f"- recalibration on out-of-fold predictions: intercept {_fmt(d['recalibration_intercept'])}, slope {_fmt(d['recalibration_slope'])}",
            f"- operating threshold {_fmt(d['operating_threshold'])} (development alert rate {_fmt(d['dev_alert_rate_per_100_patient_months'])} per 100 patient-months)",
            *[f"- {n}" for n in d["notes"]],
            "",
        ]
    if "confirmatory" in r:
        c = r["confirmatory"]
        L += [
            "## Confirmatory hypotheses (Holm-Bonferroni across three)",
            "",
            f"{c['decision_rule']}. Test patients: {c['n_test_patients']}.",
            "",
            "| id | estimate | 95% CI | criterion | CI criterion | p (one-sided) | p Holm | met |",
            "|---|---:|---|---|---|---:|---:|---|",
        ]
        for k in ("C1", "C2", "C3"):
            v = c[k]
            L.append(
                f"| {k} | {_fmt(float(v['estimate']))} | [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}] | {v['criterion']} | {'yes' if v['ci_criterion_met'] else 'no'} | {v['p']:.3f} | {v['p_holm']:.3f} | **{'YES' if v['met'] else 'no'}** |"
            )
        L += [
            "",
            "A criterion not met is reported as not met. C3 measures workload only; meeting it says nothing about whether alerts are correct.",
            "",
        ]
    if "secondary" in r:
        s = r["secondary"]
        L += ["## Secondary and descriptive analyses (no pass/fail claim)", ""]
        for k, v in s.items():
            L += [
                f"### {k.replace('_', ' ')}",
                "",
                "```json",
                json.dumps(v, indent=2, default=float),
                "```",
                "",
            ]
    if r["deviations"]:
        L += ["## Protocol deviations", "", *[f"- {d}" for d in r["deviations"]], ""]
    L += [
        "## What this report does not claim",
        "",
        "No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.",
        "",
    ]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
