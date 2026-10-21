#!/usr/bin/env python3
"""One-time runner for the preregistered source-aligned synthetic E1 study."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "vigil-core"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-sim"))

from vigil_sim.e1_comparison import evaluate_e1_source_comparison  # noqa: E402
from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402

EXPERIMENT = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json"
PREREG_PATH = EXPERIMENT / "PREREG.md"
ACCESS_LOG_PATH = EXPERIMENT / "ACCESS_LOG.jsonl"
RESULTS_PATH = EXPERIMENT / "results.json"
REPORT_PATH = EXPERIMENT / "REPORT.md"
COMPLETION_PATH = EXPERIMENT / "RUN_COMPLETION.json"

# These values are the executable form of the committed preregistration.
EXPERIMENT_ID = "EXP-SIM-CAL-E1-001"
PROFILE_SHA256 = "d4e29b2b4bb5b51a04487b73c38dd3b48b4ac2d161bfaa2dc28757693210aa57"
GENERATORS = (
    ("G1", GeneratorType.G1_SMOOTH, 100),
    ("G2", GeneratorType.G2_BURST, 200),
    ("G3", GeneratorType.G3_NOISE, 300),
)
REPLICATES = 30
PATIENTS_PER_COHORT = 1023
FOLLOWUP_DAYS = 2263.0
SEED_BASE = 514000
BOOTSTRAP_REPLICATES = 10000
BOOTSTRAP_SEED = 514999
MIN_DEFINED_REPLICATES = 24
CONFIDENCE_LEVEL = 0.95


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _require_clean_checkout() -> str:
    source_commit = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("study runner requires a clean checkout")
    return source_commit


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def _append_access(entry: dict[str, Any]) -> None:
    with ACCESS_LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _start_access_log(entry: dict[str, Any]) -> None:
    """Atomically claim the one-time run before any cohort access."""
    descriptor = os.open(ACCESS_LOG_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _seed(generator_offset: int, replicate: int) -> int:
    return SEED_BASE + generator_offset + replicate


def _bootstrap_summary(values: list[float | None], rng: np.random.Generator) -> dict[str, Any]:
    defined = np.asarray([value for value in values if value is not None], dtype=float)
    result: dict[str, Any] = {
        "defined_replicates": int(defined.size),
        "total_replicates": REPLICATES,
        "mean": float(np.mean(defined)) if defined.size else None,
        "ci_level": CONFIDENCE_LEVEL,
        "ci_method": "percentile bootstrap over independent seed replicates",
        "ci_replicates": BOOTSTRAP_REPLICATES,
    }
    if defined.size < MIN_DEFINED_REPLICATES:
        result["ci"] = None
        result["status"] = "not_estimable"
        return result
    draws = rng.choice(defined, size=(BOOTSTRAP_REPLICATES, defined.size), replace=True)
    means = np.mean(draws, axis=1)
    alpha = 1.0 - CONFIDENCE_LEVEL
    low, high = np.quantile(means, [alpha / 2.0, 1.0 - alpha / 2.0])
    result["ci"] = [float(low), float(high)]
    result["status"] = "estimated"
    return result


def render_report(results: dict[str, Any]) -> str:
    lines = [
        "# EXP-SIM-CAL-E1-001: Source-aligned synthetic CA 15-3 comparison",
        "",
        "> Synthetic simulator diagnostics only. These results do not establish clinical calibration,",
        "> diagnostic performance, benefit, or an appropriate clinical cutoff.",
        "",
        "[Molina et al. 1995](https://pubmed.ncbi.nlm.nih.gov/7579505/) reported 37/91 CA 15-3",
        "elevations before diagnosis (41%), a lead-time summary of",
        "4.2 ± 2.3 months, 54% sensitivity after excluding locoregional recurrences, and 99%",
        "specificity among 444 NED patients. The abstract does not define the dispersion convention",
        "for ± 2.3. Current [ASCO guidance (2026)](https://ascopubs.org/doi/10.1200/JCO-26-01700)",
        "does not recommend routine tumor markers for asymptomatic surveillance.",
        "",
        f"Synthetic profile: `{results['profile_id']}`.",
        f"Source cutoff: > {results['cutoff']['source_value']} {results['cutoff']['source_unit']} = "
        f"> {results['cutoff']['value']} {results['cutoff']['canonical_unit']}.",
        "The synthetic profile is an uncalibrated stress assumption. Comparisons are descriptive;",
        "there are no pass thresholds and no simulator parameters were tuned.",
        "",
        "## Across-seed estimates",
        "",
        "Intervals resample whole independent seed replicates. Rows with undefined metrics remain",
        "in the per-seed output; an interval is withheld when fewer than 24 of 30 replicates define it.",
        "",
        "| Generator | Metric | Defined seeds | Mean | 95% interval |",
        "|---|---|---:|---:|---:|",
    ]
    for name, summary in results["aggregate"].items():
        for metric, stats in summary.items():
            mean = "not estimable" if stats["mean"] is None else f"{stats['mean']:.6g}"
            interval = (
                "not estimable"
                if stats["ci"] is None
                else f"[{stats['ci'][0]:.6g}, {stats['ci'][1]:.6g}]"
            )
            lines.append(
                f"| {name} | {metric} | {stats['defined_replicates']}/{stats['total_replicates']} | {mean} | {interval} |"
            )
    lines.extend(
        [
            "",
            "## Per-seed counts and estimates",
            "",
            "Fractions are shown as numerator/denominator; `—` means the metric is undefined.",
            "The case monitored fraction uses only diagnosed cases with a measured value strictly",
            "before diagnosis. Observed-NED coverage is measured patients over eligible observed-NED",
            "patients. Oracle counts are synthetic latent-truth sensitivity analyses.",
            "",
            "| Generator | Seed | Detected / monitored cases | Detected / all diagnosed | Monitored cases / diagnosed | Lead time mean ± sample SD (months) | Observed-NED negative / measured | Measured / eligible NED | Oracle negative / measured |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for generator, rows in results.get("replicates", {}).items():
        for row in rows:
            cases = row["case_detection"]
            lead = row["conditional_lead_time"]
            observed_ned = row["observed_ned_specificity"]
            oracle_ned = row["oracle_recurrence_free_specificity"]

            def fraction(numerator: int, denominator: int) -> str:
                return f"{numerator}/{denominator}" if denominator else "—"

            lead_mean = lead["mean_months"]
            lead_sd = lead["sample_sd_months"]
            lead_summary = (
                "—"
                if lead_mean is None
                else f"{lead_mean:.4g} ± {lead_sd:.4g}"
                if lead_sd is not None
                else f"{lead_mean:.4g} ± —"
            )
            lines.append(
                "| {generator} | {seed} | {monitored_detected} | {all_detected} | "
                "{coverage} | {lead} | {observed} | {ned_coverage} | {oracle} |".format(
                    generator=generator,
                    seed=row["seed"],
                    monitored_detected=fraction(cases["detected_cases"], cases["monitored_cases"]),
                    all_detected=fraction(cases["detected_cases"], cases["diagnosed_cases"]),
                    coverage=fraction(cases["monitored_cases"], cases["diagnosed_cases"]),
                    lead=lead_summary,
                    observed=fraction(
                        observed_ned["negative_measured_ned_patients"],
                        observed_ned["measured_ned_patients"],
                    ),
                    ned_coverage=fraction(
                        observed_ned["measured_ned_patients"],
                        observed_ned["eligible_ned_patients"],
                    ),
                    oracle=fraction(
                        oracle_ned["negative_measured_patients"],
                        oracle_ned["measured_recurrence_free_patients"],
                    ),
                )
            )
    lines.extend(
        [
            "",
            "## Unsupported source endpoint",
            "",
            "E1's 54% distant-recurrence sensitivity is `not_estimable`: these G1/G2/G3 site",
            "mechanisms do not include locoregional recurrence, so the source denominator cannot be",
            "reconstructed. The observed-NED specificity may include occult latent recurrence; an",
            "oracle recurrence-free sensitivity analysis is provided separately in the JSON.",
            "",
            "See `PREREG.md` for the endpoint definitions, fixed seeds, and limitations. Values are",
            "generated from `results.json`; this report must be reproduced byte-for-byte by the runner.",
            "",
        ]
    )
    return "\n".join(lines)


def _aggregate(replicates: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    aggregate: dict[str, Any] = {}
    metrics = {
        "monitored_case_detection_fraction": lambda row: row["case_detection"][
            "fraction_monitored_detected"
        ],
        "all_diagnosed_case_detection_fraction": lambda row: row["case_detection"][
            "fraction_all_diagnosed_detected"
        ],
        "conditional_lead_time_mean_months": lambda row: row["conditional_lead_time"][
            "mean_months"
        ],
        "observed_ned_specificity": lambda row: row["observed_ned_specificity"]["specificity"],
        "oracle_recurrence_free_specificity": lambda row: row["oracle_recurrence_free_specificity"][
            "specificity"
        ],
    }
    for generator, rows in replicates.items():
        aggregate[generator] = {
            metric: _bootstrap_summary([extract(row) for row in rows], rng)
            for metric, extract in metrics.items()
        }
    return aggregate


def run_study() -> dict[str, Any]:
    if any(path.exists() for path in (ACCESS_LOG_PATH, RESULTS_PATH, REPORT_PATH, COMPLETION_PATH)):
        raise RuntimeError("study artifacts already exist; frozen cohorts cannot be rerun")
    source_commit = _require_clean_checkout()
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.get("profile_id") != "balanced_synthetic_core_v4":
        raise RuntimeError("unexpected synthetic profile")
    if sha256(PROFILE_PATH) != PROFILE_SHA256:
        raise RuntimeError("synthetic profile hash differs from preregistration")
    prereg_commit = _git("log", "-1", "--format=%H", "--", str(PREREG_PATH.relative_to(ROOT)))
    sources = [
        PROFILE_PATH,
        PREREG_PATH,
        Path(__file__),
        ROOT / "packages/vigil-sim/vigil_sim/generators.py",
        ROOT / "packages/vigil-sim/vigil_sim/e1_comparison.py",
        ROOT / "packages/vigil-core/vigil_core/units.py",
        ROOT / "uv.lock",
    ]
    _start_access_log(
        {
            "event": "run_started",
            "experiment_id": EXPERIMENT_ID,
            "utc": datetime.now(UTC).isoformat(),
            "source_commit": source_commit,
            "preregistration_commit": prereg_commit,
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "source_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in sources},
            "expected_seed_count": len(GENERATORS) * REPLICATES,
            "study_cohort_generation_begins_after_this_record": True,
        }
    )

    replicate_results: dict[str, list[dict[str, Any]]] = {}
    for generator_name, generator_type, offset in GENERATORS:
        replicate_results[generator_name] = []
        for replicate in range(REPLICATES):
            seed = _seed(offset, replicate)
            cohort_name = f"SYNTHETIC-SIM-CAL-E1-001-{generator_name}-REP-{replicate:02d}"
            _append_access(
                {
                    "event": "cohort_access_started",
                    "experiment_id": EXPERIMENT_ID,
                    "cohort_name": cohort_name,
                    "generator": generator_name,
                    "replicate": replicate,
                    "seed": seed,
                    "utc": datetime.now(UTC).isoformat(),
                }
            )
            cohort = get_generator(
                generator_type, seed=seed, population_config=profile
            ).generate_cohort(
                num_patients=PATIENTS_PER_COHORT,
                duration_days=FOLLOWUP_DAYS,
            )
            row = evaluate_e1_source_comparison(cohort, administrative_followup_days=FOLLOWUP_DAYS)
            row["cohort_name"] = cohort_name
            row["replicate"] = replicate
            replicate_results[generator_name].append(row)
            _append_access(
                {
                    "event": "cohort_generated_and_evaluated",
                    "experiment_id": EXPERIMENT_ID,
                    "cohort_name": cohort_name,
                    "generator": generator_name,
                    "replicate": replicate,
                    "seed": seed,
                    "result_row_sha256": hashlib.sha256(
                        json.dumps(row, sort_keys=True, allow_nan=False).encode()
                    ).hexdigest(),
                    "utc": datetime.now(UTC).isoformat(),
                }
            )

    cutoff = replicate_results["G1"][0]["ca_15_3_cutoff"]
    results = {
        "experiment_id": EXPERIMENT_ID,
        "synthetic_only": True,
        "profile_id": profile["profile_id"],
        "profile_sha256": sha256(PROFILE_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "source_commit": source_commit,
        "design": {
            "replicates_per_generator": REPLICATES,
            "patients_per_cohort": PATIENTS_PER_COHORT,
            "administrative_followup_days": FOLLOWUP_DAYS,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "minimum_defined_replicates": MIN_DEFINED_REPLICATES,
        },
        "cutoff": cutoff,
        "replicates": replicate_results,
        "aggregate": _aggregate(replicate_results),
    }
    report = render_report(results)
    _atomic_json(RESULTS_PATH, results)
    REPORT_PATH.write_text(report, encoding="utf-8")
    _append_access(
        {
            "event": "run_completed",
            "experiment_id": EXPERIMENT_ID,
            "source_commit": source_commit,
            "completed_utc": datetime.now(UTC).isoformat(),
            "results_sha256": sha256(RESULTS_PATH),
            "report_sha256": sha256(REPORT_PATH),
        }
    )
    completion = {
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "completed_utc": datetime.now(UTC).isoformat(),
        "access_log_sha256": sha256(ACCESS_LOG_PATH),
        "results_sha256": sha256(RESULTS_PATH),
        "report_sha256": sha256(REPORT_PATH),
    }
    _atomic_json(COMPLETION_PATH, completion)
    return results


def main() -> None:
    results = run_study()
    print(f"Wrote {RESULTS_PATH.relative_to(ROOT)}")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    for generator, metrics in results["aggregate"].items():
        defined = sorted({value["defined_replicates"] for value in metrics.values()})
        print(f"{generator}: aggregate metrics contain {defined} defined replicates")


if __name__ == "__main__":
    main()
