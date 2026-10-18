#!/usr/bin/env python3
"""One command: rehearse the whole partner path on SYNTHETIC data and write reports/clinical/dry_run/.

  messy/   the messy partner extraction through ingestion (rejection report; the analysis stops at the stop rate)
  signal/  a synthetic cohort with a planted CA 15-3 rise before recurrence, ingestion + full evaluation
  null/    a synthetic cohort where recurrence is independent of every laboratory value, same pipeline

The numbers are plumbing and null-behaviour checks on invented data. They are not performance results.
`--check` re-runs everything and fails if a committed file differs (used by tests and CI).

Reproducibility is byte-exact on the platform that wrote the committed files. XGBoost (the B4 candidate) is not
bit-reproducible across operating systems or CPUs: the first CI run on Linux differed from the files written on
macOS in `null/` and `signal/` (recalibration slope 0.374 vs 0.380, an operating threshold 0.182 vs 0.184,
bootstrap intervals in the third decimal). So when bytes differ, `--check` falls back to `agree()`: the files must
have the same structure, identical integers, strings and booleans (counts, verdicts, "met"/"not met"), and decimals
within `ABS_TOL + REL_TOL * magnitude`. These tolerances were chosen after seeing that drift (disclosed in the Tier 1
report); a hand-edited decimal that stays inside them is not caught.
"""

from __future__ import annotations

import argparse
import difflib
import filecmp
import json
import re
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ABS_TOL = 0.03
REL_TOL = 0.05
_DECIMAL = re.compile(r"(?<![\w.])-?\d+\.\d+(?![\w.])")
sys.path.insert(0, str(ROOT / "scripts"))

import make_dryrun_cohort as gen  # noqa: E402
import run_partner_evaluation as ev  # noqa: E402
import run_partner_ingest as ing  # noqa: E402

OUT = ROOT / "reports" / "clinical" / "dry_run"
ALERT_BUDGET = "5"  # PR-04 has no proposed default; this value exists only for the rehearsal
KEEP = ("ingest_report.json", "ingest_report.md", "report.json", "REPORT.md")


def build(dest: Path, n_patients: int = 600) -> dict[str, int]:
    warnings.filterwarnings("ignore", category=FutureWarning)
    codes: dict[str, int] = {}
    tmp = Path(tempfile.mkdtemp())
    try:
        messy = ROOT / "data" / "fixtures" / "partner_messy"
        codes["messy_ingest"] = ing.main([str(messy), "--out", str(dest / "messy")])
        for extra in [*(dest / "messy").glob("clean_*.csv"), dest / "messy" / "flagged_labs.csv"]:
            extra.unlink()  # copies of the fixture; the report is what this folder is for
        codes["messy_evaluation"] = ev.main(
            [
                str(messy),
                "--out",
                str(tmp / "messy_ev"),
                "--synthetic-dry-run",
                "--alert-budget",
                ALERT_BUDGET,
            ]
        )
        shutil.copy(tmp / "messy_ev" / "report.json", dest / "messy" / "report.json")
        shutil.copy(tmp / "messy_ev" / "REPORT.md", dest / "messy" / "REPORT.md")
        for mode in ("signal", "null"):
            data = tmp / f"cohort_{mode}"
            gen.generate(data, n_patients, mode, gen_seed())
            (data / "SYNTHETIC").write_text(
                f"All data in this folder are invented (scripts/make_dryrun_cohort.py, mode {mode}).\n",
                encoding="utf-8",
            )
            work = tmp / f"out_{mode}"
            codes[mode] = ev.main(
                [
                    str(data),
                    "--out",
                    str(work),
                    "--synthetic-dry-run",
                    "--alert-budget",
                    ALERT_BUDGET,
                ]
            )
            (dest / mode).mkdir(parents=True, exist_ok=True)
            for name in KEEP:
                if (work / name).exists():
                    shutil.copy(work / name, dest / mode / name)
        (dest / "README.md").write_text(
            "# Partner path dry run (SYNTHETIC)\n\nWritten by `scripts/run_partner_dry_run.py`; do not edit. Every file here comes from invented data. "
            "`messy/` shows the rejection report and the analysis stopping at the stop rate; `signal/` and `null/` run the full evaluation on cohorts with and "
            "without a planted laboratory signal. They check plumbing and null behaviour; they are not performance results and say nothing about real patients.\n\n"
            f"Exit codes of the steps: `{json.dumps(codes, sort_keys=True)}` (messy_ingest 2 and messy_evaluation 2 mean 'stopped at the stop rate', as intended).\n",
            encoding="utf-8",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return codes


def gen_seed() -> int:
    return 20261018


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= ABS_TOL + REL_TOL * max(abs(a), abs(b))


def _json_agree(a: object, b: object) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, float) and isinstance(b, float):
        return _close(a, b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_json_agree(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_json_agree(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _text_agree(a: str, b: str) -> bool:
    """Same text except that decimals (digits.digits) may differ within tolerance."""
    if _DECIMAL.sub("<d>", a) != _DECIMAL.sub("<d>", b):
        return False
    return all(_close(float(x), float(y)) for x, y in zip(_DECIMAL.findall(a), _DECIMAL.findall(b)))


def agree(committed: Path, rebuilt: Path) -> bool:
    """Byte-identical, or (platform float drift) equal structure with decimals within tolerance."""
    if filecmp.cmp(committed, rebuilt, shallow=False):
        return True
    if committed.suffix == ".json":
        return _json_agree(
            json.loads(committed.read_text(encoding="utf-8")),
            json.loads(rebuilt.read_text(encoding="utf-8")),
        )
    if committed.suffix == ".md":
        return _text_agree(
            committed.read_text(encoding="utf-8"), rebuilt.read_text(encoding="utf-8")
        )
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="rebuild in a temporary folder and compare with the committed files",
    )
    args = ap.parse_args(argv)
    if not args.check:
        OUT.mkdir(parents=True, exist_ok=True)
        print(build(OUT))
        return 0
    tmp = Path(tempfile.mkdtemp())
    try:
        build(tmp)
        bad = []
        for f in sorted(p for p in tmp.rglob("*") if p.is_file()):
            ref = OUT / f.relative_to(tmp)
            if not ref.exists() or not agree(ref, f):
                bad.append(str(f.relative_to(tmp)))
        if bad:
            print("dry-run reports differ from the committed files:", *bad, sep="\n  ")
            for name in bad:
                ref, new = OUT / name, tmp / name
                if ref.exists():
                    delta = difflib.unified_diff(
                        ref.read_text().splitlines(),
                        new.read_text().splitlines(),
                        "committed/" + name,
                        "rebuilt/" + name,
                        lineterm="",
                        n=0,
                    )
                    print(*list(delta)[:40], sep="\n")
            return 1
        print("dry-run reports reproduce (byte-exact, or within the documented float tolerance)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
