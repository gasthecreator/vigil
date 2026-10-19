#!/usr/bin/env python3
"""Execute the frozen synthetic core-model tuning protocol in PREREG.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for package in ("vigil-sim", "vigil-eval", "vigil-ml", "vigil-core"):
    sys.path.insert(0, str(ROOT / "packages" / package))

from vigil_eval.audit import FrozenTestAccessLogger  # noqa: E402
from vigil_eval.bootstrap import patient_cluster_bootstrap  # noqa: E402
from vigil_eval.leakage import (  # noqa: E402
    check_outcome_derived_features,
    run_latent_column_canary,
    run_shuffled_label_canary,
    run_unobserved_value_canary,
)  # noqa: E402
from vigil_eval.metrics import (  # noqa: E402
    compute_ipcw_calibration_curve,
    compute_ipcw_weights,
    ipcw_brier_score,
    ipcw_time_dependent_roc_auc,
    patient_landmark_ipcw_weights,
)  # noqa: E402
from vigil_ml.baselines import (  # noqa: E402
    GradientBoostingBaseline,
    PrevalenceBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)  # noqa: E402
from vigil_ml.features import WindowedFeatureExtractor  # noqa: E402
from vigil_ml.joint_model import FastLandmarkJointModel  # noqa: E402
from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402

HORIZON_DAYS = 365.0
COHORT_SIZE = 1000
SEEDS = {"train": 41001, "validation": 41002, "test": 41003}
BOOTSTRAP_SEED = 41004
BOOTSTRAPS = 500
PROFILE_PATH = ROOT / "packages/vigil-sim/vigil_sim/config/synthetic_population_v1.json"


def namespace_cohort(cohort: Any, split: str) -> None:
    """Give independently generated patients globally distinct identifiers."""
    patient_ids = {patient.patient_id: f"{split}:{patient.patient_id}" for patient in cohort.patients}
    for patient in cohort.patients:
        patient.patient_id = patient_ids[patient.patient_id]
    for observation in cohort.observations:
        observation.patient_id = patient_ids[observation.patient_id]
        observation.observation_id = f"{split}:{observation.observation_id}"
    for latent in cohort.latent_states:
        latent.patient_id = patient_ids[latent.patient_id]


def make_split(name: str, seed: int, config: dict[str, Any]) -> tuple[pd.DataFrame, ...]:
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=seed, population_config=config).generate_cohort(
        num_patients=COHORT_SIZE, duration_days=730.0
    )
    namespace_cohort(cohort, name)
    X, y, times, events = WindowedFeatureExtractor().transform_cohort(
        cohort.to_patients_dataframe(), cohort.to_observations_dataframe(), horizon_days=HORIZON_DAYS
    )
    return X, y, times, events, cohort.to_observations_dataframe()


def sample_weights(X: pd.DataFrame, times: np.ndarray, events: np.ndarray) -> np.ndarray:
    return patient_landmark_ipcw_weights(
        times, events, HORIZON_DAYS, X["patient_id"].to_numpy()
    )


def model_grid() -> dict[str, list[tuple[str, Any]]]:
    return {
        "B3_regularized_hazard": [
            (f"C={c}", lambda c=c: RegularizedCoxHazardBaseline(C=c, random_state=41001))
            for c in (0.05, 0.5, 5.0)
        ],
        "B4_gradient_boosting": [
            (
                f"depth={depth},estimators={estimators}",
                lambda depth=depth, estimators=estimators: GradientBoostingBaseline(
                    max_depth=depth, n_estimators=estimators, random_state=41001
                ),
            )
            for depth in (2, 3)
            for estimators in (50, 150)
        ],
        "K3_fast_landmark_approximation": [
            (f"C={c}", lambda c=c: FastLandmarkJointModel(
                horizon_days=HORIZON_DAYS, C=c, random_state=41001
            ))
            for c in (0.1, 1.0, 10.0)
        ],
    }


def validate_metric_domain(times: np.ndarray, events: np.ndarray) -> None:
    w = compute_ipcw_weights(times, events, HORIZON_DAYS)
    cases = (times <= HORIZON_DAYS) & (events == 1) & (w > 0)
    controls = ((times > HORIZON_DAYS) | (events == 2)) & (w > 0)
    if not cases.any() or not controls.any():
        raise RuntimeError("IPCW AUC is undefined: test split lacks determinable cases or controls")
    if not np.isfinite(w).all():
        raise RuntimeError("IPCW weights are not finite")


def metric_values(frame: pd.DataFrame, model_names: list[str]) -> dict[str, float]:
    times = frame["follow_up_days"].to_numpy(float)
    events = frame["event_code"].to_numpy(int)
    validate_metric_domain(times, events)
    values: dict[str, float] = {}
    for model_name in model_names:
        predictions = frame[model_name].to_numpy(float)
        calibration = compute_ipcw_calibration_curve(
            predictions, times, events, HORIZON_DAYS, n_bins=10
        )
        if not np.isfinite(calibration.expected_calibration_error):
            raise RuntimeError(f"IPCW calibration is undefined for {model_name}")
        values[f"{model_name}.auc"] = ipcw_time_dependent_roc_auc(
            predictions, times, events, HORIZON_DAYS
        )
        values[f"{model_name}.brier"] = ipcw_brier_score(
            predictions, times, events, HORIZON_DAYS
        )
        values[f"{model_name}.ipcw_ece"] = calibration.expected_calibration_error
    for metric in ("auc", "brier", "ipcw_ece"):
        values[f"B1_single_threshold.delta_{metric}"] = (
            values[f"B1_single_threshold.{metric}"]
            - values[f"B1_single_threshold.{metric}"]
        )
        for model_name in model_names:
            if model_name != "B1_single_threshold":
                values[f"{model_name}.delta_{metric}_vs_B1"] = (
                    values[f"{model_name}.{metric}"] - values[f"B1_single_threshold.{metric}"]
                )
    return values


def main() -> None:
    with PROFILE_PATH.open(encoding="utf-8") as stream:
        profile = json.load(stream)
    if profile["profile_id"] != "balanced_synthetic_v1":
        raise RuntimeError("The preregistered synthetic profile identifier changed")

    train = make_split("train", SEEDS["train"], profile)
    validation = make_split("validation", SEEDS["validation"], profile)
    test = make_split("test", SEEDS["test"], profile)
    X_train, y_train, t_train, d_train, train_obs = train
    X_val, y_val, t_val, d_val, val_obs = validation
    X_test, y_test, t_test, d_test, test_obs = test

    patient_sets = [set(X["patient_id"]) for X in (X_train, X_val, X_test)]
    if any(patient_sets[i] & patient_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise RuntimeError("Patient identifiers overlap across train/validation/test")
    if not y_train.dropna().isin([0.0, 1.0]).all():
        raise RuntimeError("Training labels must be observed binary values or NaN")
    canary_counts = run_unobserved_value_canary(train_obs)
    if not canary_counts.get("ca_15_3", 0):
        raise RuntimeError("Unobserved-value canary did not find expected masked CA 15-3 values")
    run_latent_column_canary(X_train)
    check_outcome_derived_features(X_train)
    canaries = {
        "B3_shuffled_label_auc": run_shuffled_label_canary(
            X_train, y_train, model_factory=lambda: RegularizedCoxHazardBaseline(C=0.5), seed=41005
        ),
        "B4_shuffled_label_auc": run_shuffled_label_canary(
            X_train, y_train,
            model_factory=lambda: GradientBoostingBaseline(max_depth=2, n_estimators=50, random_state=41001),
            seed=41006,
        ),
        "unobserved_ca_15_3_count": canary_counts["ca_15_3"],
    }

    train_weights = sample_weights(X_train, t_train, d_train)
    selected: dict[str, dict[str, Any]] = {}
    for family, candidates in model_grid().items():
        candidate_scores = []
        for parameter_id, factory in candidates:
            model = factory().fit(X_train, y_train, sample_weight=train_weights)
            predictions = model.predict_risk(X_val)
            score = ipcw_brier_score(predictions, t_val, d_val, HORIZON_DAYS)
            if not np.isfinite(score):
                raise RuntimeError(f"Validation Brier score is undefined for {family}/{parameter_id}")
            candidate_scores.append((score, parameter_id, factory))
        _, parameter_id, factory = min(candidate_scores, key=lambda candidate: (candidate[0], candidate[1]))
        selected_model = factory().fit(X_train, y_train, sample_weight=train_weights)
        # Materialize the selected validation predictions before any test access.
        validation_predictions = selected_model.predict_risk(X_val)
        if len(validation_predictions) != len(X_val):
            raise RuntimeError(f"Prediction count mismatch for {family}")
        selected[family] = {
            "parameter_id": parameter_id,
            "validation_ipcw_brier": min(candidate_scores)[0],
            "candidate_validation_ipcw_brier": {
                item[1]: float(item[0]) for item in candidate_scores
            },
        }

    # Validation was used only for the preregistered grid selection; test labels are first used here.
    test_weights = sample_weights(X_test, t_test, d_test)
    baselines = {
        "B0_prevalence": PrevalenceBaseline().fit(X_train, y_train, sample_weight=train_weights),
        "B1_single_threshold": SingleThresholdBaseline().fit(X_train, y_train),
        "B2_velocity": VelocityBaseline().fit(X_train, y_train),
    }
    final_models: dict[str, Any] = dict(baselines)
    for family, candidates in model_grid().items():
        parameter_id = selected[family]["parameter_id"]
        factory = next(candidate_factory for label, candidate_factory in candidates if label == parameter_id)
        final_models[family] = factory().fit(X_train, y_train, sample_weight=train_weights)

    FrozenTestAccessLogger().log_access(
        dataset_name="SYNTHETIC-CORE-ML-001-TEST",
        access_type="benchmark_evaluation",
        caller="experiments/EXP-CORE-ML-001/run.py",
        purpose="One-time evaluation after validation-only hyperparameter selection",
        num_samples=COHORT_SIZE,
    )

    test_frame = pd.DataFrame({
        "patient_id": X_test["patient_id"].to_numpy(),
        "follow_up_days": t_test,
        "event_code": d_test,
    })
    for model_name, model in final_models.items():
        test_frame[model_name] = model.predict_risk(X_test)
    model_names = list(final_models)
    bootstrap = patient_cluster_bootstrap(
        test_frame, "patient_id", lambda frame: metric_values(frame, model_names),
        n_bootstraps=BOOTSTRAPS, seed=BOOTSTRAP_SEED,
    )
    point = metric_values(test_frame, model_names)

    results = {
        "experiment_id": "EXP-CORE-ML-001",
        "status": "synthetic research evaluation; not clinical validation",
        "preregistration": "experiments/EXP-CORE-ML-001/PREREG.md",
        "profile": profile,
        "generator": "G1 smooth kinetics",
        "horizon_days": HORIZON_DAYS,
        "cohort_size_per_split": COHORT_SIZE,
        "seeds": SEEDS,
        "bootstrap": {"method": "patient-cluster percentile", "replicates": BOOTSTRAPS, "seed": BOOTSTRAP_SEED},
        "counts": {
            "landmarks": {"train": len(X_train), "validation": len(X_val), "test": len(X_test)},
            "patients": {"train": len(patient_sets[0]), "validation": len(patient_sets[1]), "test": len(patient_sets[2])},
            "test_determinable_landmarks": int(np.count_nonzero(test_weights > 0)),
            "test_recurrence_cases_by_horizon": int(np.count_nonzero((t_test <= HORIZON_DAYS) & (d_test == 1))),
            "test_competing_events": int(np.count_nonzero(d_test == 2)),
        },
        "canaries": canaries,
        "selected_models": selected,
        "test_metrics": {
            model_name: {
                metric: {
                    "estimate": point[f"{model_name}.{metric}"],
                    "ci_95": [bootstrap[f"{model_name}.{metric}"].ci_lower,
                              bootstrap[f"{model_name}.{metric}"].ci_upper],
                }
                for metric in ("auc", "brier", "ipcw_ece")
            }
            for model_name in model_names
        },
        "paired_differences_vs_B1": {
            model_name: {
                metric: {
                    "estimate": point[f"{model_name}.delta_{metric}_vs_B1"],
                    "ci_95": [bootstrap[f"{model_name}.delta_{metric}_vs_B1"].ci_lower,
                              bootstrap[f"{model_name}.delta_{metric}_vs_B1"].ci_upper],
                }
                for metric in ("auc", "brier", "ipcw_ece")
            }
            for model_name in model_names if model_name != "B1_single_threshold"
        },
    }
    output = ROOT / "experiments/EXP-CORE-ML-001/results.json"
    output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# EXP-CORE-ML-001 — synthetic core model tuning",
        "",
        "> Synthetic research evaluation only; not clinical validation, a deployment recommendation, or a Nigerian population estimate.",
        "",
        f"Profile: `{profile['profile_id']}`. Horizon: {HORIZON_DAYS:g} days. Test patients: {results['counts']['patients']['test']}; determinable test landmarks: {results['counts']['test_determinable_landmarks']}.",
        "",
        "## Validation-selected configurations",
        "",
        "| Model | Configuration | Validation IPCW Brier |",
        "|---|---|---:|",
    ]
    for name, chosen in selected.items():
        lines.append(f"| {name} | {chosen['parameter_id']} | {chosen['validation_ipcw_brier']:.6f} |")
    lines.extend([
        "",
        "## Untouched test results",
        "",
        "| Model | IPCW AUC (95% patient bootstrap CI) | IPCW Brier (95% CI) | IPCW calibration error (95% CI) |",
        "|---|---:|---:|---:|",
    ])
    for name in model_names:
        cells = []
        for metric in ("auc", "brier", "ipcw_ece"):
            result = results["test_metrics"][name][metric]
            cells.append(f"{result['estimate']:.4f} [{result['ci_95'][0]:.4f}, {result['ci_95'][1]:.4f}]")
        lines.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} |")
    lines.extend([
        "",
        "## Data checks",
        "",
        f"- Shuffled-label AUC canaries: B3={canaries['B3_shuffled_label_auc']:.4f}; B4={canaries['B4_shuffled_label_auc']:.4f}.",
        f"- Masked CA 15-3 values found by the unobserved-value canary: {canaries['unobserved_ca_15_3_count']}.",
        "- Train/validation/test cohorts use disjoint namespaced patient identifiers; all result rows and intervals are generated by `run.py` from `results.json` inputs.",
        "- Event definition is observed clinical recurrence in the simulator; partial verification remains an unresolved limitation.",
        "",
        "## Limits",
        "",
        "The test cohort is one synthetic G1 draw. The study does not establish performance under G2/G3, new sites or laboratories, real data, clinical benefit, or biological recurrence under partial verification. No clinical threshold or model deployment decision follows from these results.",
        "",
        "Reproduce with `python experiments/EXP-CORE-ML-001/run.py`. Machine-readable results: [`results.json`](results.json). Test access: [`data/audit/frozen_test_access.jsonl`](../../data/audit/frozen_test_access.jsonl).",
        "",
    ])
    (ROOT / "experiments/EXP-CORE-ML-001/REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")
    print(json.dumps(results["counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
