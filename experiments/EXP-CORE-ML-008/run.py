#!/usr/bin/env python3
"""Run the preregistered cross-generator B3/B4 evaluation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[2]
for package in ("vigil-sim", "vigil-eval", "vigil-ml", "vigil-core"):
    sys.path.insert(0, str(ROOT / "packages" / package))

from vigil_eval.audit import FrozenTestAccessLogger  # noqa: E402
from vigil_eval.leakage import (  # noqa: E402
    check_outcome_derived_features,
    run_latent_column_canary,
    run_shuffled_label_canary,
    run_unobserved_value_canary,
)
from vigil_eval.metrics import (  # noqa: E402
    compute_ipcw_calibration_curve,
    compute_ipcw_weights,
    ipcw_brier_score,
    ipcw_time_dependent_roc_auc,
    patient_landmark_ipcw_weights,
)
from vigil_ml.baselines import (  # noqa: E402
    GradientBoostingBaseline,
    PrevalenceBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)
from vigil_ml.features import WindowedFeatureExtractor  # noqa: E402
from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402

HORIZON_DAYS = 365.0
COHORT_SIZE = 1000
REPLICATES = range(5)
SPLIT_OFFSETS = {"train": 100, "calibration": 200, "validation": 300, "test": 400}
GENERATOR_OFFSETS = {"G1": 10, "G2": 20, "G3": 30}
GENERATORS = {
    "G1": GeneratorType.G1_SMOOTH,
    "G2": GeneratorType.G2_BURST,
    "G3": GeneratorType.G3_NOISE,
}
FIT_SEED = 64001
BOOTSTRAP_SEED = 64500
BOOTSTRAPS = 1000
PROFILE_PATH = ROOT / "packages/vigil-sim/vigil_sim/config/synthetic_population_v1.json"


@dataclass
class Cohort:
    X: pd.DataFrame
    y: pd.Series
    times: np.ndarray
    events: np.ndarray
    observations: pd.DataFrame
    generator: str
    replicate: int


def seed_for(split: str, generator: str, replicate: int) -> int:
    return 64_000 + SPLIT_OFFSETS[split] + GENERATOR_OFFSETS[generator] + replicate


def generate_cohort(
    split: str, generator_name: str, replicate: int, profile: dict[str, Any]
) -> Cohort:
    seed = seed_for(split, generator_name, replicate)
    cohort = get_generator(
        GENERATORS[generator_name], seed=seed, population_config=profile
    ).generate_cohort(num_patients=COHORT_SIZE, duration_days=730.0)
    prefix = f"{split}:{generator_name}:r{replicate}"
    patient_ids = {p.patient_id: f"{prefix}:{p.patient_id}" for p in cohort.patients}
    for patient in cohort.patients:
        patient.patient_id = patient_ids[patient.patient_id]
    for obs in cohort.observations:
        obs.patient_id = patient_ids[obs.patient_id]
        obs.observation_id = f"{prefix}:{obs.observation_id}"
    for state in cohort.latent_states:
        state.patient_id = patient_ids[state.patient_id]
    X, y, times, events = WindowedFeatureExtractor().transform_cohort(
        cohort.to_patients_dataframe(),
        cohort.to_observations_dataframe(),
        horizon_days=HORIZON_DAYS,
    )
    return Cohort(
        X=X.reset_index(drop=True),
        y=y.reset_index(drop=True),
        times=np.asarray(times, dtype=float),
        events=np.asarray(events, dtype=int),
        observations=cohort.to_observations_dataframe(),
        generator=generator_name,
        replicate=replicate,
    )


def sample_weights(cohort: Cohort) -> np.ndarray:
    return patient_landmark_ipcw_weights(
        cohort.times,
        cohort.events,
        HORIZON_DAYS,
        cohort.X["patient_id"].to_numpy(),
    )


def combined_training_data(cohorts: list[Cohort]) -> tuple[pd.DataFrame, pd.Series, np.ndarray]:
    X = pd.concat([c.X for c in cohorts], ignore_index=True, sort=False)
    y = pd.concat([c.y for c in cohorts], ignore_index=True).astype(float)
    weights = np.concatenate([sample_weights(c) for c in cohorts])
    if len(X) != len(y) or len(y) != len(weights):
        raise RuntimeError("Combined training arrays do not align")
    return X, y, weights


def model_grid() -> dict[str, list[tuple[str, Callable[[], Any]]]]:
    return {
        "B3_regularized_logistic_horizon": [
            (
                f"C={c:g}",
                lambda c=c: RegularizedCoxHazardBaseline(C=c, random_state=FIT_SEED),
            )
            for c in (0.05, 0.5, 5.0)
        ],
        "B4_xgboost_horizon": [
            (
                f"depth={depth},estimators={estimators},learning_rate={learning_rate:g}",
                lambda depth=depth, estimators=estimators, learning_rate=learning_rate: (
                    GradientBoostingBaseline(
                        max_depth=depth,
                        n_estimators=estimators,
                        learning_rate=learning_rate,
                        random_state=FIT_SEED,
                        n_jobs=1,
                    )
                ),
            )
            for depth in (2, 3)
            for estimators in (50, 150)
            for learning_rate in (0.03, 0.05)
        ],
    }


def validation_brier(model: Any, cohorts: list[Cohort]) -> float:
    scores: list[float] = []
    for cohort in cohorts:
        pred = model.predict_risk(cohort.X)
        scores.append(ipcw_brier_score(pred, cohort.times, cohort.events, HORIZON_DAYS))
    if not scores or not np.isfinite(scores).all():
        raise RuntimeError("Validation IPCW Brier score is undefined")
    return float(np.mean(scores))


def fit_calibrator(
    scores: np.ndarray, labels: np.ndarray, weights: np.ndarray
) -> LogisticRegression:
    valid = np.isfinite(labels) & (weights > 0)
    if np.unique(labels[valid]).size != 2:
        raise RuntimeError("Calibration cohort lacks both weighted outcome classes")
    calibrator = LogisticRegression(C=1.0, max_iter=2000, random_state=FIT_SEED, solver="lbfgs")
    calibrator.fit(scores[valid, None], labels[valid].astype(int), sample_weight=weights[valid])
    return calibrator


def make_prediction_frame(
    cohorts: list[Cohort], models: dict[str, Any], calibrators: dict[str, LogisticRegression]
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for cohort in cohorts:
        frame = pd.DataFrame(
            {
                "patient_id": cohort.X["patient_id"].to_numpy(),
                "replicate": cohort.replicate,
                "follow_up_days": cohort.times,
                "event_code": cohort.events,
            }
        )
        for name, model in models.items():
            scores = model.predict_risk(cohort.X)
            frame[name] = (
                calibrators[name].predict_proba(scores[:, None])[:, 1]
                if name in calibrators
                else scores
            )
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def metrics_for_replicate(frame: pd.DataFrame, names: list[str]) -> dict[str, float]:
    times = frame["follow_up_days"].to_numpy(dtype=float)
    events = frame["event_code"].to_numpy(dtype=int)
    weights = compute_ipcw_weights(times, events, HORIZON_DAYS)
    known = weights > 0
    outcome = ((times <= HORIZON_DAYS) & (events == 1)).astype(int)
    metrics: dict[str, float] = {}
    for name in names:
        pred = frame[name].to_numpy(dtype=float)
        curve = compute_ipcw_calibration_curve(
            pred, times, events, HORIZON_DAYS, n_bins=10, weights=weights
        )
        metrics[f"{name}.auc"] = ipcw_time_dependent_roc_auc(
            pred, times, events, HORIZON_DAYS, weights=weights
        )
        metrics[f"{name}.brier"] = ipcw_brier_score(
            pred, times, events, HORIZON_DAYS, weights=weights
        )
        metrics[f"{name}.ipcw_ece"] = curve.expected_calibration_error
        metrics[f"{name}.average_precision"] = (
            float(
                average_precision_score(outcome[known], pred[known], sample_weight=weights[known])
            )
            if np.unique(outcome[known]).size == 2
            else float("nan")
        )
    comparators = ("B0_prevalence", "B1_single_threshold", "B2_velocity")
    for name in names:
        if name not in comparators:
            for comparator in comparators:
                for metric in ("auc", "brier", "ipcw_ece", "average_precision"):
                    metrics[f"{name}.delta_{metric}_vs_{comparator}"] = (
                        metrics[f"{name}.{metric}"] - metrics[f"{comparator}.{metric}"]
                    )
    return metrics


def mean_metrics_by_replicate(frame: pd.DataFrame, names: list[str]) -> dict[str, float]:
    values = [
        metrics_for_replicate(group, names)
        for _replicate, group in frame.groupby("replicate", sort=True)
    ]
    keys = values[0].keys()
    return {
        key: float(np.mean([row[key] for row in values]))
        if all(np.isfinite(row[key]) for row in values)
        else float("nan")
        for key in keys
    }


def bootstrap_by_patient_and_replicate(
    frame: pd.DataFrame, names: list[str]
) -> dict[str, dict[str, float | int]]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    grouped = {
        replicate: {
            patient: patient_rows
            for patient, patient_rows in replicate_rows.groupby("patient_id", sort=False)
        }
        for replicate, replicate_rows in frame.groupby("replicate", sort=True)
    }
    point = mean_metrics_by_replicate(frame, names)
    samples: dict[str, list[float]] = {metric: [] for metric in point}
    for _ in range(BOOTSTRAPS):
        replicas = []
        for replicate, patients in grouped.items():
            patient_ids = np.array(list(patients))
            sampled_ids = rng.choice(patient_ids, size=len(patient_ids), replace=True)
            for draw, patient_id in enumerate(sampled_ids):
                copy = patients[patient_id].copy()
                copy["patient_id"] = f"boot:{replicate}:{draw}"
                replicas.append(copy)
        try:
            metrics = mean_metrics_by_replicate(pd.concat(replicas, ignore_index=True), names)
        except (ValueError, RuntimeError, ZeroDivisionError):
            continue
        for key, value in metrics.items():
            if np.isfinite(value):
                samples[key].append(value)
    out: dict[str, dict[str, float | int]] = {}
    for key, values in samples.items():
        if not np.isfinite(point[key]):
            out[key] = {"ci_95": None, "valid_replicates": 0, "standard_error": None}
            continue
        if len(values) < 400:
            raise RuntimeError(
                f"Only {len(values)} valid bootstrap draws for {key}; minimum is 400"
            )
        out[key] = {
            "ci_95": [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))],
            "valid_replicates": len(values),
            "standard_error": float(np.std(values, ddof=1)),
        }
    return out


def assert_no_prior_run() -> None:
    output_paths = (
        ROOT / "experiments/EXP-CORE-ML-008/results.json",
        ROOT / "experiments/EXP-CORE-ML-008/REPORT.md",
    )
    if any(path.exists() for path in output_paths):
        raise RuntimeError("EXP-CORE-ML-008 output already exists; frozen test access cannot be repeated")
    access_log = ROOT / "data/audit/frozen_test_access.jsonl"
    if access_log.exists():
        prefix = "SYNTHETIC-CORE-ML-008-"
        for line in access_log.read_text(encoding="utf-8").splitlines():
            if line:
                record = json.loads(line)
                if record.get("dataset_name", "").startswith(prefix) or record.get(
                    "caller"
                ) == "experiments/EXP-CORE-ML-008/run.py":
                    raise RuntimeError("EXP-CORE-ML-008 frozen test access is already logged")


def assert_clean_checkout() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    if status:
        raise RuntimeError("Refusing frozen-test access from a dirty checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> None:
    assert_no_prior_run()
    profile_sha256 = hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()
    expected_profile_sha256 = "70cfed8bfe8c28c668434b5e409d2350b276784461f54a56e3ecd69ae98469b3"
    if profile_sha256 != expected_profile_sha256:
        raise RuntimeError("The preregistered synthetic profile hash changed")
    with PROFILE_PATH.open(encoding="utf-8") as stream:
        profile = json.load(stream)
    if profile.get("profile_id") != "balanced_synthetic_v1":
        raise RuntimeError("The preregistered synthetic stress profile changed")

    train = [generate_cohort("train", g, r, profile) for g in ("G1", "G2") for r in REPLICATES]
    calibration = [
        generate_cohort("calibration", g, r, profile) for g in ("G1", "G2") for r in REPLICATES
    ]
    validation = [
        generate_cohort("validation", g, r, profile) for g in ("G1", "G2") for r in REPLICATES
    ]
    ids_by_split = {
        name: set(pd.concat([c.X["patient_id"] for c in cohorts], ignore_index=True))
        for name, cohorts in (
            ("train", train),
            ("calibration", calibration),
            ("validation", validation),
        )
    }
    for left, right in (
        ("train", "calibration"),
        ("train", "validation"),
        ("calibration", "validation"),
    ):
        if ids_by_split[left] & ids_by_split[right]:
            raise RuntimeError(f"Patient identifiers overlap across {left} and {right}")

    X_train, y_train, train_weights = combined_training_data(train)
    X_cal, y_cal, cal_weights = combined_training_data(calibration)
    if not np.isfinite(train_weights).all() or np.any(train_weights < 0):
        raise RuntimeError("Training weights must be finite and nonnegative")
    if np.any(train_weights[~np.isfinite(y_train)] != 0):
        raise RuntimeError("Censored training labels must have zero fit weight")
    if not y_train.dropna().isin([0.0, 1.0]).all():
        raise RuntimeError("Training outcomes must be binary or missing")

    obs_frame = pd.concat([c.observations for c in train], ignore_index=True, sort=False)
    canary_counts = run_unobserved_value_canary(obs_frame)
    if not canary_counts.get("ca_15_3", 0):
        raise RuntimeError("Unobserved-value canary found no masked CA 15-3 values")
    run_latent_column_canary(X_train)
    check_outcome_derived_features(X_train)
    canary_specs = {
        "B0_prevalence": (PrevalenceBaseline, 64002),
        "B1_single_threshold": (SingleThresholdBaseline, 64003),
        "B2_velocity": (VelocityBaseline, 64004),
        "B3_regularized_logistic_horizon": (
            lambda: RegularizedCoxHazardBaseline(C=0.5, random_state=FIT_SEED),
            64005,
        ),
        "B4_xgboost_horizon": (
            lambda: GradientBoostingBaseline(
                max_depth=2,
                n_estimators=50,
                learning_rate=0.03,
                random_state=FIT_SEED,
                n_jobs=1,
            ),
            64006,
        ),
    }
    canaries = {
        f"{name}_shuffled_label_auc": run_shuffled_label_canary(
            X_train, y_train, model_factory=factory, seed=seed
        )
        for name, (factory, seed) in canary_specs.items()
    }
    if any(value > 0.60 for value in canaries.values()):
        raise RuntimeError("A shuffled-label canary exceeded the frozen 0.60 AUC threshold")
    canaries["unobserved_ca_15_3_count"] = int(canary_counts["ca_15_3"])

    selected: dict[str, dict[str, Any]] = {}
    factories_by_name: dict[str, Callable[[], Any]] = {}
    for family, candidates in model_grid().items():
        candidate_scores = []
        for parameter_id, factory in candidates:
            candidate = factory().fit(X_train, y_train, sample_weight=train_weights)
            score = validation_brier(candidate, validation)
            candidate_scores.append((score, parameter_id, factory))
        best = min(score for score, _parameter_id, _factory in candidate_scores)
        tied = [entry for entry in candidate_scores if entry[0] <= best + 1e-12]
        score, parameter_id, factory = min(tied, key=lambda item: item[1])
        selected[family] = {
            "parameter_id": parameter_id,
            "validation_ipcw_brier": float(score),
            "candidate_validation_ipcw_brier": {
                item[1]: float(item[0]) for item in candidate_scores
            },
        }
        factories_by_name[family] = factory

    baselines: dict[str, Any] = {
        "B0_prevalence": PrevalenceBaseline().fit(X_train, y_train, sample_weight=train_weights),
        "B1_single_threshold": SingleThresholdBaseline().fit(
            X_train, y_train, sample_weight=train_weights
        ),
        "B2_velocity": VelocityBaseline().fit(X_train, y_train, sample_weight=train_weights),
    }
    models = {
        **baselines,
        **{
            family: factory().fit(X_train, y_train, sample_weight=train_weights)
            for family, factory in factories_by_name.items()
        },
    }
    calibrators: dict[str, LogisticRegression] = {}
    for name, model in models.items():
        if name == "B0_prevalence":
            continue
        raw = np.concatenate([model.predict_risk(c.X) for c in calibration])
        calibrators[name] = fit_calibrator(raw, y_cal.to_numpy(dtype=float), cal_weights)

    # The frozen test data is first generated only after model selection and calibration freeze.
    code_sha = assert_clean_checkout()
    logger = FrozenTestAccessLogger()
    for generator in ("G1", "G2", "G3"):
        logger.log_access(
            dataset_name=f"SYNTHETIC-CORE-ML-008-{generator}-TEST",
            access_type="benchmark_evaluation",
            caller="experiments/EXP-CORE-ML-008/run.py",
            purpose=f"One-time cross-generator evaluation from clean code SHA {code_sha}",
            num_samples=COHORT_SIZE * len(REPLICATES),
        )
    test_by_generator = {
        generator: [
            generate_cohort("test", generator, replicate, profile) for replicate in REPLICATES
        ]
        for generator in ("G1", "G2", "G3")
    }

    model_names = list(models)
    results: dict[str, Any] = {
        "experiment_id": "EXP-CORE-ML-008",
        "code_sha": code_sha,
        "status": "synthetic research evaluation; not clinical validation",
        "preregistration": "experiments/EXP-CORE-ML-008/PREREG.md",
        "profile": profile,
        "profile_sha256": profile_sha256,
        "generator_roles": {
            "train_calibration_validation": ["G1", "G2"],
            "test": ["G1", "G2", "G3"],
        },
        "horizon_days": HORIZON_DAYS,
        "cohort_size_per_generator_replicate": COHORT_SIZE,
        "seeds": {
            split: {
                generator: [seed_for(split, generator, r) for r in REPLICATES]
                for generator in (("G1", "G2") if split != "test" else ("G1", "G2", "G3"))
            }
            for split in SPLIT_OFFSETS
        },
        "bootstrap": {
            "method": "paired patient-cluster, within replicate",
            "replicates": BOOTSTRAPS,
            "seed": BOOTSTRAP_SEED,
        },
        "counts": {
            split: {
                generator: {
                    "patients": int(sum(c.X["patient_id"].nunique() for c in cohorts)),
                    "landmarks": int(sum(len(c.X) for c in cohorts)),
                }
                for generator, cohorts in (
                    (
                        "G1",
                        [
                            c
                            for c in (
                                train
                                if split == "train"
                                else calibration
                                if split == "calibration"
                                else validation
                            )
                            if c.generator == "G1"
                        ],
                    ),
                    (
                        "G2",
                        [
                            c
                            for c in (
                                train
                                if split == "train"
                                else calibration
                                if split == "calibration"
                                else validation
                            )
                            if c.generator == "G2"
                        ],
                    ),
                )
            }
            for split in ("train", "calibration", "validation")
        },
        "canaries": canaries,
        "selected_models": selected,
        "test_metrics": {},
        "test_replicate_metrics": {},
        "paired_differences_vs_baselines": {},
    }
    for generator, cohorts in test_by_generator.items():
        prediction_frame = make_prediction_frame(cohorts, models, calibrators)
        point = mean_metrics_by_replicate(prediction_frame, model_names)
        intervals = bootstrap_by_patient_and_replicate(prediction_frame, model_names)
        results["test_metrics"][generator] = {
            name: {
                metric: {
                    "estimate": point[f"{name}.{metric}"],
                    **intervals[f"{name}.{metric}"],
                }
                for metric in ("auc", "brier", "ipcw_ece", "average_precision")
            }
            for name in model_names
        }
        results["paired_differences_vs_baselines"][generator] = {
            name: {
                comparator: {
                    metric: {
                        "estimate": point[f"{name}.delta_{metric}_vs_{comparator}"],
                        **intervals[f"{name}.delta_{metric}_vs_{comparator}"],
                    }
                    for metric in ("auc", "brier", "ipcw_ece", "average_precision")
                }
                for comparator in ("B0_prevalence", "B1_single_threshold", "B2_velocity")
            }
            for name in ("B3_regularized_logistic_horizon", "B4_xgboost_horizon")
        }
        results["test_replicate_metrics"][generator] = {
            str(replicate): metrics_for_replicate(
                prediction_frame[prediction_frame["replicate"] == replicate], model_names
            )
            for replicate in REPLICATES
        }
        results["counts"].setdefault("test", {})[generator] = {
            "patients": int(sum(c.X["patient_id"].nunique() for c in cohorts)),
            "landmarks": int(sum(len(c.X) for c in cohorts)),
            "determinable_landmarks": int(
                sum(np.count_nonzero(sample_weights(c)) for c in cohorts)
            ),
        }

    output = ROOT / "experiments/EXP-CORE-ML-008/results.json"
    output.write_text(
        json.dumps(json_safe(results), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    render_report(results, output.with_name("REPORT.md"))
    print(f"Wrote {output.relative_to(ROOT)}")


def render_report(results: dict[str, Any], path: Path) -> None:
    lines = [
        "# EXP-CORE-ML-008 — cross-generator core baseline evaluation",
        "",
        "> Synthetic research evaluation only; not clinical validation, a deployment recommendation, or a population estimate.",
        "",
        f"Profile: `{results['profile']['profile_id']}`. Horizon: {results['horizon_days']:g} days. Five independent cohorts per test generator, with {COHORT_SIZE} patients each.",
        "",
        "## Validation-selected configurations",
        "",
        "| Model | Configuration | Pooled validation IPCW Brier |",
        "|---|---|---:|",
    ]
    for name, selection in results["selected_models"].items():
        lines.append(
            f"| {name} | {selection['parameter_id']} | {selection['validation_ipcw_brier']:.6f} |"
        )
    for generator, metrics in results["test_metrics"].items():
        lines.extend(
            [
                "",
                f"## Test results: {generator}",
                "",
                "| Model | IPCW AUC | IPCW Brier | IPCW ECE | IPCW average precision |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for name, model_metrics in metrics.items():
            cells = []
            for metric in ("auc", "brier", "ipcw_ece", "average_precision"):
                item = model_metrics[metric]
                if item["ci_95"] is None or item["estimate"] is None:
                    cells.append("undefined")
                else:
                    lo, hi = item["ci_95"]
                    cells.append(f"{item['estimate']:.4f} [{lo:.4f}, {hi:.4f}]")
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines.extend([
            "", "### Paired learned-model differences versus B0/B1/B2", "",
            "| Model | Comparator | Metric | Difference [95% patient-cluster CI] | Valid resamples |",
            "|---|---|---|---:|---:|",
        ])
        for model, comparator_results in results["paired_differences_vs_baselines"][generator].items():
            for comparator, metrics in comparator_results.items():
                for metric, item in metrics.items():
                    if item["ci_95"] is None or item["estimate"] is None:
                        summary = "undefined"
                    else:
                        lo, hi = item["ci_95"]
                        summary = f"{item['estimate']:.4f} [{lo:.4f}, {hi:.4f}]"
                    lines.append(
                        f"| {model} | {comparator} | {metric} | {summary} | {item['valid_replicates']} |"
                    )
    lines.extend(
        [
            "",
            "## Integrity checks and scope",
            "",
            "- Shuffled-label AUC canaries: "
            + "; ".join(
                f"{name.removesuffix('_shuffled_label_auc')}={value:.4f}"
                for name, value in results["canaries"].items()
                if name.endswith("_shuffled_label_auc")
            )
            + ".",
            f"- The unobserved CA 15-3 canary found {results['canaries']['unobserved_ca_15_3_count']} masked values in training observations.",
            "- Test patients are namespaced by split, generator, and replicate. Test metrics are generated by `run.py` and retain each test replicate in `results.json`.",
            "- Evaluation is for the simulator's observed recurrence outcome. Partial verification, new real sites/laboratories, clinical benefit, and real cohort calibration remain unvalidated.",
            "- A synthetic G3 result is a stress test of these simulator assumptions, not evidence of transport to a clinical population.",
            "",
            "Reproduce with `make reproduce-ml-core-complete-rerun`. Machine-readable results: [`results.json`](results.json). Frozen test access: [`data/audit/frozen_test_access.jsonl`](../../data/audit/frozen_test_access.jsonl).",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def json_safe(value: Any) -> Any:
    """Represent undefined numerical metrics as JSON null, never nonstandard NaN."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


if __name__ == "__main__":
    main()
