#!/usr/bin/env python3
"""One-time synthetic audit of the registered K3-v2 observation process."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for package in ("vigil-sim", "vigil-core"):
    sys.path.insert(0, str(ROOT / "packages" / package))

from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402

EXP = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "packages/vigil-sim/vigil_sim/config/synthetic_population_k3_v2.json"
PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
GENERATORS = (
    ("G1", GeneratorType.G1_SMOOTH),
    ("G2", GeneratorType.G2_BURST),
    ("G3", GeneratorType.G3_NOISE),
)
N_PATIENTS = 2_000
DURATION_DAYS = 730.0
REPLICATES = range(5)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    radius = z * np.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return [float(center - radius), float(center + radius)]


def summarize_count(successes: int, total: int, expected: float) -> dict[str, Any]:
    return {
        "successes": int(successes),
        "total": int(total),
        "observed_rate": float(successes / total) if total else None,
        "expected_probability": float(expected),
        "absolute_deviation": float(abs(successes / total - expected)) if total else None,
        "wilson_95": wilson(successes, total),
    }


def require_clean_committed_tree() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    if status:
        raise RuntimeError("Refusing EXP-CORE-ML-005 access from a dirty working tree")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> None:
    access_path = EXP / "ACCESS_LOG.json"
    results_path = EXP / "results.json"
    report_path = EXP / "REPORT.md"
    if any(path.exists() for path in (access_path, results_path, report_path)):
        raise RuntimeError("EXP-CORE-ML-005 is one-time; an access or result artifact already exists")
    source_commit = require_clean_committed_tree()
    profile_hash = sha256(PROFILE_PATH)
    lock_path = ROOT / "uv.lock"
    access: dict[str, Any] = {
        "experiment_id": "EXP-CORE-ML-005",
        "protocol_version": "1.0",
        "source_commit": source_commit,
        "runner_sha256": sha256(Path(__file__)),
        "profile_sha256": profile_hash,
        "environment_lock_sha256": sha256(lock_path) if lock_path.exists() else None,
        "started_utc_epoch": time.time(),
        "completed": False,
        "design": {
            "generators": [name for name, _ in GENERATORS],
            "seed_formula": "910000 + 10000 * generator_index + replicate_index",
            "replicates_per_generator": len(REPLICATES),
            "patients_per_cell": N_PATIENTS,
            "duration_days": DURATION_DAYS,
        },
    }
    access_path.write_text(json.dumps(access, indent=2) + "\n", encoding="utf-8")

    propensity_cells: dict[str, list[dict[str, float]]] = {name: [] for name, _ in GENERATORS}
    result_cells: dict[str, dict[str, list[int]]] = {
        name: {"visible_recurrence": [0, 0], "nonvisible_recurrence": [0, 0], "no_recurrence": [0, 0]}
        for name, _ in GENERATORS
    }
    missingness_cells: dict[str, dict[str, list[float]]] = {
        name: {} for name, _ in GENERATORS
    }
    g1_missingness_by_factor: dict[str, list[list[float]]] = {}
    facility_distributions: dict[str, dict[str, list[list[float]]]] = {
        name: {} for name, _ in GENERATORS
    }
    facility_checks: dict[str, dict[str, int]] = {name: {"patients": 0, "facilities": 0, "inconsistent": 0} for name, _ in GENERATORS}
    verification = PROFILE["verification"]
    missing_cfg = PROFILE["measurement_missingness"]

    for generator_index, (name, generator_type) in enumerate(GENERATORS):
        for replicate in REPLICATES:
            seed = 910000 + 10000 * generator_index + replicate
            cohort = get_generator(
                generator_type, seed=seed, population_config=PROFILE
            ).generate_cohort(num_patients=N_PATIENTS, duration_days=DURATION_DAYS)
            patients = {patient.patient_id: patient for patient in cohort.patients}
            states = {(state.patient_id, float(state.day)): state for state in cohort.latent_states}
            obs_rows = cohort.observations
            friction_values = np.asarray(
                [patient.out_of_pocket_delay_factor for patient in cohort.patients], dtype=float
            )
            friction_cutpoints = np.quantile(friction_values, [0.2, 0.4, 0.6, 0.8])
            if name == "G1":
                for analyte in missing_cfg["high_cost_analytes"]:
                    g1_missingness_by_factor.setdefault(analyte, [[0.0, 0.0, 0.0] for _ in range(5)])

            # Per-visit propensity calibration, grouped into deterministic equal-frequency deciles.
            order = np.argsort([float(obs.imaging_probability) for obs in obs_rows], kind="stable")
            for decile, indices in enumerate(np.array_split(order, 10)):
                if len(indices) == 0:
                    continue
                selected = [obs_rows[int(index)] for index in indices]
                propensity_cells[name].append({
                    "replicate": float(replicate),
                    "decile": float(decile + 1),
                    "n": float(len(selected)),
                    "expected": float(np.mean([obs.imaging_probability for obs in selected])),
                    "performed": float(sum(obs.imaging_performed for obs in selected)),
                })

            for obs in obs_rows:
                patient = patients[obs.patient_id]
                state = states[(obs.patient_id, float(obs.day))]
                burden = state.b_loc + state.b_bone + state.b_liver + state.b_lung + state.b_brain
                if not patient.true_recurrence_event:
                    result_stratum = "no_recurrence"
                elif burden >= verification["visible_burden_threshold"]:
                    result_stratum = "visible_recurrence"
                else:
                    result_stratum = "nonvisible_recurrence"
                if obs.imaging_performed:
                    counts = result_cells[name][result_stratum]
                    counts[1] += 1
                    counts[0] += int(bool(obs.imaging_result))

                for analyte, observed in obs.observed_mask.items():
                    friction_bin = int(np.searchsorted(
                        friction_cutpoints, patient.out_of_pocket_delay_factor, side="right"
                    ))
                    expected_skip = (
                        min(1.0, missing_cfg["high_cost_skip_probability_per_cost_factor"]
                            * patient.out_of_pocket_delay_factor)
                        if name == "G1" and analyte in missing_cfg["high_cost_analytes"]
                        else missing_cfg["base_skip_probability_by_generator"][generator_type.value]
                    )
                    values = missingness_cells[name].setdefault(analyte, [0.0, 0.0, 0.0])
                    values[0] += float(not observed)
                    values[1] += 1.0
                    values[2] += float(expected_skip)
                    if name == "G1" and analyte in missing_cfg["high_cost_analytes"]:
                        bin_values = g1_missingness_by_factor[analyte][friction_bin]
                        bin_values[0] += float(not observed)
                        bin_values[1] += 1.0
                        bin_values[2] += expected_skip

            facility_map: dict[str, dict[str, tuple[float, float]]] = {}
            for patient in cohort.patients:
                facility_checks[name]["patients"] += 1
                facility_map.setdefault(patient.facility_id, {})
                for analyte, offset in patient.lab_offsets.items():
                    effect = (offset, patient.lab_scales[analyte])
                    previous = facility_map[patient.facility_id].setdefault(analyte, effect)
                    if previous != effect:
                        facility_checks[name]["inconsistent"] += 1
            facility_checks[name]["facilities"] += len(facility_map)
            for facility_effects in facility_map.values():
                for analyte, (offset, scale) in facility_effects.items():
                    effects = facility_distributions[name].setdefault(analyte, [[], []])
                    effects[0].append(offset)
                    effects[1].append(scale)

    output: dict[str, Any] = {
        "experiment_id": "EXP-CORE-ML-005",
        "source_commit": source_commit,
        "profile_sha256": profile_hash,
        "design": access["design"],
        "synthetic_only": True,
        "imaging_propensity_by_generator": {},
        "imaging_result_by_generator_and_stratum": {},
        "assay_missingness_by_generator_and_analyte": {},
        "g1_high_cost_missingness_by_factor_quintile": {},
        "facility_effect_distribution_by_generator_and_analyte": {},
        "facility_effect_invariants": facility_checks,
    }
    for name, _ in GENERATORS:
        rows = propensity_cells[name]
        by_decile = []
        for decile in range(1, 11):
            subset = [row for row in rows if row["decile"] == decile]
            expected = float(np.average([row["expected"] for row in subset], weights=[row["n"] for row in subset]))
            performed = int(sum(row["performed"] for row in subset))
            total = int(sum(row["n"] for row in subset))
            by_decile.append({"decile": decile, **summarize_count(performed, total, expected)})
        output["imaging_propensity_by_generator"][name] = by_decile
        output["imaging_result_by_generator_and_stratum"][name] = {
            stratum: summarize_count(*counts, expected=(
                verification["sensitivity"] if stratum == "visible_recurrence"
                else 1.0 - verification["specificity"]
            ))
            for stratum, counts in result_cells[name].items()
        }
        output["assay_missingness_by_generator_and_analyte"][name] = {
            analyte: {
                "missing": int(values[0]),
                "total": int(values[1]),
                "observed_missing_rate": float(values[0] / values[1]),
                "mean_expected_missing_probability": float(values[2] / values[1]),
            }
            for analyte, values in sorted(missingness_cells[name].items())
        }
        output["facility_effect_distribution_by_generator_and_analyte"][name] = {
            analyte: {
                "facilities_observed": len(effects[0]),
                "offset_mean": float(np.mean(effects[0])),
                "offset_sd": float(np.std(effects[0], ddof=1)) if len(effects[0]) > 1 else None,
                "offset_min": float(np.min(effects[0])),
                "offset_max": float(np.max(effects[0])),
                "scale_mean": float(np.mean(effects[1])),
                "scale_sd": float(np.std(effects[1], ddof=1)) if len(effects[1]) > 1 else None,
                "scale_min": float(np.min(effects[1])),
                "scale_max": float(np.max(effects[1])),
            }
            for analyte, effects in sorted(facility_distributions[name].items())
        }
    output["g1_high_cost_missingness_by_factor_quintile"] = {
        analyte: [
            {"quintile": index + 1, **summarize_count(
                int(values[0]), int(values[1]), values[2] / values[1] if values[1] else 0.0
            )}
            for index, values in enumerate(quintiles)
        ]
        for analyte, quintiles in sorted(g1_missingness_by_factor.items())
    }

    results_bytes = (json.dumps(output, indent=2, sort_keys=True) + "\n").encode()
    results_path.write_bytes(results_bytes)
    lines = [
        "# EXP-CORE-ML-005: synthetic observation-process calibration",
        "",
        "> Synthetic simulator mechanics audit only. This does not establish clinical test accuracy, simulator realism, model performance, or verification-bias correction.",
        "",
        f"- Source commit: `{source_commit}`",
        f"- Profile SHA-256: `{profile_hash}`",
        f"- Patients: {N_PATIENTS} per generator/replicate; five replicates; 730 days.",
        "- All registered cells are included; proportions and Monte Carlo intervals describe only this configuration.",
        "",
        "## Imaging propensity",
        "",
    ]
    for name, deciles in output["imaging_propensity_by_generator"].items():
        lines.extend([f"### {name}", "", "| Decile | N | Expected mean | Observed rate | Wilson 95% interval |", "|---:|---:|---:|---:|---:|"])
        for cell in deciles:
            ci = cell["wilson_95"]
            interval = "undefined" if ci is None else f"[{ci[0]:.4f}, {ci[1]:.4f}]"
            lines.append(f"| {cell['decile']} | {cell['total']} | {cell['expected_probability']:.4f} | {cell['observed_rate']:.4f} | {interval} |")
        lines.append("")
    lines.extend(["## Imaging result generation", "", "| Generator | Stratum | N performed | Expected positive probability | Observed positive rate | Wilson 95% interval |", "|---|---|---:|---:|---:|---:|"])
    for name, strata in output["imaging_result_by_generator_and_stratum"].items():
        for stratum, cell in strata.items():
            ci = cell["wilson_95"]
            interval = "undefined" if ci is None else f"[{ci[0]:.4f}, {ci[1]:.4f}]"
            lines.append(f"| {name} | {stratum} | {cell['total']} | {cell['expected_probability']:.4f} | {cell['observed_rate']} | {interval} |")
    lines.extend(["", "## Assay missingness", "", "| Generator | Analyte | N | Expected mean missing probability | Observed missing rate |", "|---|---|---:|---:|---:|"])
    for name, analytes in output["assay_missingness_by_generator_and_analyte"].items():
        for analyte, cell in analytes.items():
            lines.append(f"| {name} | {analyte} | {cell['total']} | {cell['mean_expected_missing_probability']:.4f} | {cell['observed_missing_rate']:.4f} |")
    lines.extend(["", "## Facility invariants", "", "| Generator | Patients | Facilities across replicates | Within-facility inconsistencies |", "|---|---:|---:|---:|"])
    for name, cell in facility_checks.items():
        lines.append(f"| {name} | {cell['patients']} | {cell['facilities']} | {cell['inconsistent']} |")
    lines.extend(["", "## G1 high-cost assay missingness by out-of-pocket factor quintile", "", "| Analyte | Quintile | N | Expected mean | Observed missing rate | Wilson 95% interval |", "|---|---:|---:|---:|---:|---:|"])
    for analyte, quintiles in output["g1_high_cost_missingness_by_factor_quintile"].items():
        for cell in quintiles:
            ci = cell["wilson_95"]
            interval = "undefined" if ci is None else f"[{ci[0]:.4f}, {ci[1]:.4f}]"
            lines.append(f"| {analyte} | {cell['quintile']} | {cell['total']} | {cell['expected_probability']:.4f} | {cell['observed_rate']:.4f} | {interval} |")
    lines.extend(["", "## Facility effect distribution", "", "Per-generator/analyte mean, sample SD, minimum, and maximum for shared facility offsets and scales are in `results.json`; the table above reports within-facility equality checks.", "", "## Interpretation", "", "Read the generated rates against the preregistered configuration and their denominators. These results only diagnose implementation behavior in the named synthetic profile. No result supports a clinical-performance claim or a correction method for selective verification.", ""])
    report_bytes = "\n".join(lines).encode()
    report_path.write_bytes(report_bytes)
    access.update({
        "completed": True,
        "completed_utc_epoch": time.time(),
        "results_sha256": hashlib.sha256(results_bytes).hexdigest(),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
    })
    access_path.write_text(json.dumps(access, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {results_path} and {report_path}")


if __name__ == "__main__":
    main()
