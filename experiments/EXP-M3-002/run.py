#!/usr/bin/env python3
"""Run EXP-M3-002 once after its source and preregistration are committed."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, replace
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from vigil_ml.m3 import DEFAULT_M3_ASSUMPTIONS, M3Assumptions, adjudicate
from vigil_sim.generators import GeneratorType, get_generator

ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
RESULTS_PATH = EXP_DIR / "results.json"
REPORT_PATH = EXP_DIR / "REPORT.md"
ACCESS_PATH = EXP_DIR / "ACCESS_LOG.json"
CONFIG_PATH = ROOT / "packages/vigil-ml/vigil_ml/models/m3_assumptions_v1.json"
SIMULATOR_PROFILE_PATH = ROOT / "packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json"
GENERATORS = (
    ("G1", GeneratorType.G1_SMOOTH),
    ("G2", GeneratorType.G2_BURST),
    ("G3", GeneratorType.G3_NOISE),
)
STUDY_ID = "EXP-M3-002"
PROTOCOL_VERSION = "1.0"
SEEDS = (20261024, 20261025, 20261026)
N_PATIENTS = 500
DURATION_DAYS = 730.0
ERROR_INJECTION_PROBABILITY = 0.03


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    files = sorted(root.rglob("*.py"))
    return canonical_hash(
        [{"path": path.relative_to(root).as_posix(), "sha256": sha256(path)} for path in files]
    )


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def registered_configurations() -> list[M3Assumptions]:
    base = DEFAULT_M3_ASSUMPTIONS
    variants: list[tuple[str, dict[str, Any]]] = [
        ("error_prior_0_01", {"p_error_prior": 0.01}),
        ("error_prior_0_10", {"p_error_prior": 0.10}),
        ("real_prior_0_10", {"p_real_prior": 0.10}),
        ("real_prior_0_35", {"p_real_prior": 0.35}),
        ("real_ratio_1_2_2_0", {"real_change_ratio_min": 1.2, "real_change_ratio_max": 2.0}),
        ("real_ratio_1_8_4_0", {"real_change_ratio_min": 1.8, "real_change_ratio_max": 4.0}),
        ("population_median_12", {"population_error_log_median": 12.0}),
        ("population_median_24", {"population_error_log_median": 24.0}),
        ("population_log_sd_0_3", {"population_error_log_sd": 0.3}),
        ("population_log_sd_0_9", {"population_error_log_sd": 0.9}),
        ("inter_lab_cv_0_00", {"inter_lab_cv": 0.0}),
        ("inter_lab_cv_0_20", {"inter_lab_cv": 0.20}),
        ("decimal_shift_5", {"decimal_shift_factor": 5.0}),
        ("decimal_shift_20", {"decimal_shift_factor": 20.0}),
        ("population_error_heavy", {"gross_error_mode_weights": (0.60, 0.20, 0.20)}),
        ("decimal_error_heavy", {"gross_error_mode_weights": (0.20, 0.40, 0.40)}),
        ("error_action_threshold_0_20", {"error_needs_repeat_threshold": 0.20}),
        ("error_action_threshold_0_40", {"error_needs_repeat_threshold": 0.40}),
        ("real_action_threshold_0_50", {"real_change_escalate_threshold": 0.50}),
        ("real_action_threshold_0_70", {"real_change_escalate_threshold": 0.70}),
        ("stable_action_threshold_0_85", {"stable_explained_threshold": 0.85}),
        ("stable_action_threshold_0_95", {"stable_explained_threshold": 0.95}),
    ]
    return [base, *(replace(base, config_id=name, **values) for name, values in variants)]


def _inject_current_value(value: float, history: list[tuple[float, float]], seed_parts: list[int]) -> tuple[float, bool]:
    rng = np.random.default_rng(np.random.SeedSequence(seed_parts))
    if rng.random() >= ERROR_INJECTION_PROBABILITY:
        return value, False
    mode = int(rng.choice(3, p=DEFAULT_M3_ASSUMPTIONS.gross_error_mode_weights))
    if mode == 0:
        changed = float(
            rng.lognormal(
                mean=np.log(DEFAULT_M3_ASSUMPTIONS.population_error_log_median),
                sigma=DEFAULT_M3_ASSUMPTIONS.population_error_log_sd,
            )
        )
    else:
        baseline = float(np.exp(np.mean(np.log([value for _, value in history]))))
        factor = DEFAULT_M3_ASSUMPTIONS.decimal_shift_factor
        changed = baseline * factor if mode == 1 else baseline / factor
    return changed, True


def valid_marker_rows(patient_obs: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Keep only finite positive observed CA 15-3 values accepted by M3."""
    observed = patient_obs["observed_ca_15_3"].fillna(False).astype(bool)
    has_value = patient_obs["ca_15_3"].notna()
    available = patient_obs.loc[observed & has_value]
    raw_values = available["ca_15_3"].to_numpy(dtype=float)
    finite_values = np.isfinite(raw_values)
    positive_values = finite_values & (raw_values > 0.0)
    finite_days = np.isfinite(available["day"].to_numpy(dtype=float))
    selected = available.loc[positive_values & finite_days]
    exclusions = {
        "excluded_unobserved_observations": int((~observed).sum()),
        "excluded_missing_values": int((observed & ~has_value).sum()),
        "excluded_nonfinite_values": int((~finite_values).sum()),
        "excluded_nonpositive_values": int((finite_values & (raw_values <= 0.0)).sum()),
        "excluded_nonfinite_days": int((~finite_days).sum()),
    }
    return selected, exclusions


def strictly_prior_indices(days: np.ndarray, visit_index: int) -> np.ndarray:
    """Select only earlier visits, excluding same-day ties rejected by M3."""
    return np.flatnonzero(days[:visit_index] < days[visit_index])


def _build_stratum(generator_name: str, generator_type: GeneratorType, seed: int, generator_index: int) -> dict[str, Any]:
    profile = json.loads(SIMULATOR_PROFILE_PATH.read_text(encoding="utf-8"))
    cohort = get_generator(generator_type, seed=seed, population_config=profile).generate_cohort(
        N_PATIENTS, duration_days=DURATION_DAYS
    )
    obs = cohort.to_observations_dataframe()
    patients = cohort.to_patients_dataframe().set_index("patient_id")
    cases = []
    exclusions = {
        "excluded_unobserved_observations": 0,
        "excluded_missing_values": 0,
        "excluded_nonfinite_values": 0,
        "excluded_nonpositive_values": 0,
        "excluded_nonfinite_days": 0,
    }
    for patient_index, (patient_id, patient_obs) in enumerate(obs.groupby("patient_id", sort=True)):
        patient_obs = patient_obs.sort_values("day", kind="stable")
        patient_obs, patient_exclusions = valid_marker_rows(patient_obs)
        for key, count in patient_exclusions.items():
            exclusions[key] += count
        days = patient_obs["day"].to_numpy(dtype=float)
        values = patient_obs["ca_15_3"].to_numpy(dtype=float)
        facilities = patient_obs["facility_id"].fillna("").astype(str).to_numpy()
        truth = patients.loc[patient_id]
        has_recurrence = bool(truth["true_recurrence_event"]) if pd.notna(truth["true_recurrence_event"]) else False
        recurrence_day = float(truth["true_recurrence_day"]) if pd.notna(truth["true_recurrence_day"]) else float("inf")
        for visit_index in range(len(days)):
            prior_indices = strictly_prior_indices(days, visit_index)
            if len(prior_indices) < 3:
                continue
            history = [(float(days[index]), float(values[index])) for index in prior_indices]
            current_value, injected_error = _inject_current_value(
                float(values[visit_index]),
                history,
                [seed, generator_index, patient_index, visit_index, 7781],
            )
            case_id = f"{patient_id}:{visit_index}"
            cases.append(
                {
                    "case_id": case_id,
                    "history": history,
                    "new_day": float(days[visit_index]),
                    "new_value": current_value,
                    "lab_changed": bool(facilities[visit_index] != facilities[prior_indices[-1]]),
                    "recurrence_label": bool(has_recurrence and days[visit_index] >= recurrence_day),
                    "injected_error_label": injected_error,
                }
            )
    if not cases:
        raise RuntimeError(f"No eligible M3 cases in {generator_name}, seed {seed}")
    model_inputs = [
        {key: case[key] for key in ("case_id", "history", "new_day", "new_value", "lab_changed")}
        for case in cases
    ]
    analysis_labels = [
        {"case_id": case["case_id"], "recurrence_label": case["recurrence_label"], "injected_error_label": case["injected_error_label"]}
        for case in cases
    ]
    return {
        "generator": generator_name,
        "seed": seed,
        "cases": cases,
        "n_evaluations": len(cases),
        **exclusions,
        "model_input_sha256": canonical_hash(model_inputs),
        "analysis_label_sha256": canonical_hash(analysis_labels),
    }


def _auc(labels: list[bool], scores: list[float]) -> float | None:
    if len(set(labels)) < 2:
        return None
    return float(roc_auc_score(np.asarray(labels, dtype=int), np.asarray(scores, dtype=float)))


def _summarize(config: M3Assumptions, stratum: dict[str, Any], baseline: dict[str, dict[str, Any]]) -> dict[str, Any]:
    real_deltas: list[float] = []
    error_deltas: list[float] = []
    stable_deltas: list[float] = []
    current_actions: list[str] = []
    base_actions: list[str] = []
    real_scores: list[float] = []
    error_scores: list[float] = []
    recurrence_labels: list[bool] = []
    error_labels: list[bool] = []
    invalid_count = 0
    abstention_count = 0
    for case in stratum["cases"]:
        result = adjudicate(
            case["history"],
            case["new_day"],
            case["new_value"],
            cv_analytical=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_analytical,
            cv_within=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_within,
            lab_changed=case["lab_changed"],
            assumptions=config,
        )
        prior = baseline[case["case_id"]]
        abstention_count += int(bool(result.get("abstention")))
        probabilities = (result.get("p_real"), result.get("p_error"), result.get("p_stable"))
        invalid_count += int(
            result.get("action") not in {"explained", "needs_repeat", "escalate", "abstain"}
            or (not result.get("abstention") and (
                any(value is None or not np.isfinite(value) or not 0.0 <= value <= 1.0 for value in probabilities)
                or not np.isclose(sum(probabilities), 1.0)
            ))
        )
        real_deltas.append(abs(float(result["p_real"]) - float(prior["p_real"])))
        error_deltas.append(abs(float(result["p_error"]) - float(prior["p_error"])))
        stable_deltas.append(abs(float(result["p_stable"]) - float(prior["p_stable"])))
        current_actions.append(str(result["action"]))
        base_actions.append(str(prior["action"]))
        real_scores.append(float(result["p_real"]))
        error_scores.append(float(result["p_error"]))
        recurrence_labels.append(bool(case["recurrence_label"]))
        error_labels.append(bool(case["injected_error_label"]))
    all_deltas = np.concatenate((real_deltas, error_deltas, stable_deltas))
    action_counts = {action: current_actions.count(action) for action in ("explained", "needs_repeat", "escalate", "abstain")}
    return {
        "generator": stratum["generator"],
        "seed": stratum["seed"],
        "n_evaluations": len(current_actions),
        "invalid_count": invalid_count,
        "abstention_count": abstention_count,
        "model_input_sha256": stratum["model_input_sha256"],
        "analysis_label_sha256": stratum["analysis_label_sha256"],
        "median_absolute_score_delta": float(np.median(all_deltas)),
        "p95_absolute_score_delta": float(np.quantile(all_deltas, 0.95)),
        "component_median_absolute_deltas": {
            "p_real": float(np.median(real_deltas)),
            "p_error": float(np.median(error_deltas)),
            "p_stable": float(np.median(stable_deltas)),
        },
        "action_switch_rate": float(np.mean(np.asarray(current_actions) != np.asarray(base_actions))),
        "action_counts": action_counts,
        "descriptive_auc_recurrence": _auc(recurrence_labels, real_scores),
        "descriptive_auc_injected_error": _auc(error_labels, error_scores),
    }


def _assert_clean_committed_tree() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError(f"{STUDY_ID} requires a clean worktree before cohort generation")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True).stdout.strip()


def main() -> None:
    if any(path.exists() for path in (RESULTS_PATH, REPORT_PATH, ACCESS_PATH)):
        raise RuntimeError(f"{STUDY_ID} is one-time; an access or result artifact already exists")
    source_commit = _assert_clean_committed_tree()
    from render import render_report

    provenance = {
        "source_commit": source_commit,
        "preregistration_sha256": sha256(EXP_DIR / "PREREG.md"),
        "runner_sha256": sha256(Path(__file__)),
        "renderer_sha256": sha256(EXP_DIR / "render.py"),
        "m3_source_sha256": sha256(ROOT / "packages/vigil-ml/vigil_ml/m3.py"),
        "configuration_sha256": sha256(CONFIG_PATH),
        "simulator_package_sha256": tree_sha256(ROOT / "packages/vigil-sim/vigil_sim"),
        "simulator_profile_sha256": sha256(SIMULATOR_PROFILE_PATH),
        "analyte_registry_sha256": sha256(ROOT / "packages/vigil-core/vigil_core/analytes.py"),
        "environment_lock_sha256": sha256(ROOT / "uv.lock"),
    }
    environment = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": version("scikit-learn"),
    }
    access = {
        "study_id": STUDY_ID,
        "protocol_version": PROTOCOL_VERSION,
        "provenance": provenance,
        "environment": environment,
        "completed": False,
    }
    ACCESS_PATH.write_text(json.dumps(access, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        strata = []
        for generator_index, (generator_name, generator_type) in enumerate(GENERATORS):
            for seed in SEEDS:
                print(f"Generating {generator_name} cohort, seed={seed}, n={N_PATIENTS}", flush=True)
                strata.append(_build_stratum(generator_name, generator_type, seed, generator_index))
        baseline_config, *variants = registered_configurations()
        baseline_results: dict[str, dict[str, dict[str, Any]]] = {}
        baseline_summaries = []
        for stratum in strata:
            baseline_config_results = {
                case["case_id"]: adjudicate(
                    case["history"],
                    case["new_day"],
                    case["new_value"],
                    cv_analytical=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_analytical,
                    cv_within=DEFAULT_M3_ASSUMPTIONS.illustrative_cv_within,
                    lab_changed=case["lab_changed"],
                    assumptions=baseline_config,
                )
                for case in stratum["cases"]
            }
            baseline_results[f"{stratum['generator']}:{stratum['seed']}"] = baseline_config_results
            baseline_summaries.append(_summarize(baseline_config, stratum, {key: value for key, value in baseline_config_results.items()}))
        configuration_results = [{
            "config_id": baseline_config.config_id,
            "effective_config_sha256": baseline_config.effective_config_sha256,
            "settings": asdict(baseline_config),
            "strata": baseline_summaries,
        }]
        for config in variants:
            cells = []
            for stratum in strata:
                key = f"{stratum['generator']}:{stratum['seed']}"
                cells.append(_summarize(config, stratum, baseline_results[key]))
            configuration_results.append({
                "config_id": config.config_id,
                "effective_config_sha256": config.effective_config_sha256,
                "settings": asdict(config),
                "strata": cells,
            })
        for stratum in strata:
            expected_hashes = (stratum["model_input_sha256"], stratum["analysis_label_sha256"])
            for configuration in configuration_results:
                cell = next(
                    cell for cell in configuration["strata"]
                    if cell["generator"] == stratum["generator"] and cell["seed"] == stratum["seed"]
                )
                actual_hashes = (cell["model_input_sha256"], cell["analysis_label_sha256"])
                if actual_hashes != expected_hashes:
                    raise RuntimeError(f"{STUDY_ID} configuration changed registered inputs or analysis labels")
        results = {
        "study_id": STUDY_ID,
        "protocol_version": PROTOCOL_VERSION,
            "status": "synthetic_sensitivity_only",
            "source_commit": source_commit,
            "provenance": provenance,
            "environment": environment,
            "design": {
                "generators": [name for name, _ in GENERATORS],
                "seeds": list(SEEDS),
                "patients_per_cell": N_PATIENTS,
                "duration_days": DURATION_DAYS,
                "simulator_profile_id": "balanced_synthetic_core_v4",
                "error_injection_probability": ERROR_INJECTION_PROBABILITY,
                "configuration_count": len(configuration_results),
            },
            "strata": [
                {key: value for key, value in stratum.items() if key != "cases"}
                for stratum in strata
            ],
            "configurations": configuration_results,
        }
        RESULTS_PATH.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        report = render_report(results)
        REPORT_PATH.write_text(report, encoding="utf-8")
        if render_report(json.loads(RESULTS_PATH.read_text(encoding="utf-8"))) != report:
            raise RuntimeError(f"{STUDY_ID} report does not reproduce from saved results.json")
        access["completed"] = True
        access["results_sha256"] = sha256(RESULTS_PATH)
        access["report_sha256"] = sha256(REPORT_PATH)
        ACCESS_PATH.write_text(json.dumps(access, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        access["error_type"] = type(exc).__name__
        access["error_message"] = str(exc)
        ACCESS_PATH.write_text(json.dumps(access, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    print(f"Wrote registered synthetic sensitivity artifacts under {EXP_DIR}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
