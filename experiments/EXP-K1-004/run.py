#!/usr/bin/env python3
"""Run the registered K1 own-world and synthetic marker-transfer evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import logsumexp
from scipy.stats import kstest
from vigil_ml import k1
from vigil_sim.generators import GeneratorType, get_generator

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "packages" / "vigil-ml" / "vigil_ml" / "models"
TRAINING_RESULTS = EXPERIMENT / "training_results.json"
CONFIG_PATH = EXPERIMENT / "config.json"
RESULT_PATH = EXPERIMENT / "results.json"
REPORT_PATH = EXPERIMENT / "REPORT.md"
ACCESS_LOG_PATH = EXPERIMENT / "ACCESS_LOG.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def git_dirty_paths() -> set[str]:
    output = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def verify_artifacts(config: dict[str, Any], training: dict[str, Any]) -> None:
    generated_paths = {
        "experiments/EXP-K1-004/training_results.json",
        "experiments/EXP-K1-004/results.json",
        "experiments/EXP-K1-004/REPORT.md",
        "experiments/EXP-K1-004/ACCESS_LOG.json",
        "packages/vigil-ml/vigil_ml/models/k1_amortized_weights.safetensors",
        "packages/vigil-ml/vigil_ml/models/k1_npe_weights.safetensors",
    }
    dirty_paths = git_dirty_paths()
    unexpected_dirty = dirty_paths - generated_paths
    if unexpected_dirty:
        raise RuntimeError(
            "refusing EXP-K1-004 with modified source files: "
            + ", ".join(sorted(unexpected_dirty))
        )
    if training["source_commit"] != git_output("rev-parse", "HEAD"):
        raise RuntimeError("training result was generated from a different source commit")
    if training["source_sha256"] != sha256(Path(k1.__file__)):
        raise RuntimeError("K1 source changed after neural estimators were trained")
    if training["runner_source_sha256"] != sha256(Path(__file__)):
        raise RuntimeError("experiment runner changed after registered estimator training")
    if training["reproduction_script_sha256"] != sha256(ROOT / "scripts" / "reproduce_k1_exp004.sh"):
        raise RuntimeError("reproduction entrypoint changed after registered estimator training")
    if training["assumptions_sha256"] != sha256(MODEL_DIR / "k1_assumptions.json"):
        raise RuntimeError("K1 assumptions changed after neural estimators were trained")
    if training["experiment_config_sha256"] != sha256(CONFIG_PATH):
        raise RuntimeError("EXP-K1-004 config changed after neural estimators were trained")
    if training["environment_lock_sha256"] != sha256(ROOT / "uv.lock"):
        raise RuntimeError("dependency lock changed after registered estimator training")
    simulator = ROOT / "packages" / "vigil-sim" / "vigil_sim" / "generators.py"
    if training["simulator_source_sha256"] != sha256(simulator):
        raise RuntimeError("simulator source changed after registered estimator training")
    for route in ("amortized", "npe"):
        artifact = MODEL_DIR / training["estimators"][route]["artifact"]
        if sha256(artifact) != training["estimators"][route]["artifact_sha256"]:
            raise RuntimeError(f"{route} weights do not match registered training output")
    if config["protocol_version"] != training["protocol_version"]:
        raise RuntimeError("protocol version differs between config and training record")


def write_access_log(payload: dict[str, Any]) -> None:
    temp = ACCESS_LOG_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(ACCESS_LOG_PATH)


def make_own_world_observation(
    rng: np.random.Generator,
    setting: str,
    setting_config: dict[str, Any],
) -> tuple[k1.K1Params, k1.K1Observations]:
    params = k1.sample_prior(rng)
    schedule = k1.SCHEDULE + rng.uniform(
        -setting_config["schedule_jitter_days"],
        setting_config["schedule_jitter_days"],
        size=len(k1.SCHEDULE),
    )
    schedule[0] = 0.0
    if setting == "declared_model_sparse_visits_and_missing_analytes":
        retain = rng.random(len(schedule)) < setting_config["visit_retention_probability"]
        retain[0] = True
        schedule = schedule[retain]
    obs = k1.simulate_patient(
        params,
        schedule,
        rng,
        measurement_noise_sd=setting_config["measurement_noise_sd"],
    )
    missing = rng.random(len(schedule)) < setting_config["measurement_missing_probability"]
    if setting == "declared_model_sparse_visits_and_missing_analytes":
        # The registered 25% measurement mask is additional to visit thinning.
        pass
    values = obs.values["ca153"].copy()
    values[missing] = np.nan
    return params, k1.K1Observations(days=schedule, values={"ca153": values})


def summarize_posterior(
    truth: k1.K1Params,
    posterior: dict[str, Any],
    observed: k1.K1Observations,
    rng: np.random.Generator,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    parameter_result: dict[str, Any] = {}
    ranks: dict[str, list[float]] = {}
    for name in k1.PARAM_NAMES:
        draws = np.asarray(posterior[name], dtype=np.float64)
        value = float(getattr(truth, name))
        parameter_result[name] = {
            "truth": value,
            "mean": float(np.mean(draws)),
            "bias": float(np.mean(draws) - value),
            "rmse": float(np.sqrt(np.mean((draws - value) ** 2))),
            "coverage": {
                str(level): bool(
                    np.quantile(draws, (1.0 - level) / 2.0)
                    <= value
                    <= np.quantile(draws, 1.0 - (1.0 - level) / 2.0)
                )
                for level in (0.5, 0.8, 0.9, 0.95)
            },
            "interval_width_90": float(np.quantile(draws, 0.95) - np.quantile(draws, 0.05)),
        }
        below = int(np.sum(draws < value))
        ties = int(np.sum(draws == value))
        randomized_rank = below + int(rng.integers(ties + 1)) + rng.random()
        ranks[name] = [float(randomized_rank / (len(draws) + 1))]

    days, values = k1._observed_ca153(observed)
    if len(days):
        predictive_means = k1._expected_ca153_samples(posterior, days)
        predictive_draws = predictive_means + rng.normal(
            0.0, k1.OBSERVATION_SD, size=predictive_means.shape
        )
        predictive_log_density = logsumexp(
            -0.5 * ((values[None, :] - predictive_means) / k1.OBSERVATION_SD) ** 2
            - np.log(k1.OBSERVATION_SD)
            - 0.5 * np.log(2.0 * np.pi),
            axis=0,
        ) - np.log(len(predictive_means))
        ppc = {
            "n_observations": int(len(days)),
            "mae": float(np.mean(np.abs(values - predictive_means.mean(axis=0)))),
            "mean_log_predictive_density": float(np.mean(predictive_log_density)),
            "coverage_90": float(
                np.mean(
                    (values >= np.quantile(predictive_draws, 0.05, axis=0))
                    & (values <= np.quantile(predictive_draws, 0.95, axis=0))
                )
            ),
        }
    else:
        ppc = {"n_observations": 0, "mae": None, "mean_log_predictive_density": None, "coverage_90": None}
    return {"parameters": parameter_result, "posterior_predictive": ppc}, ranks


def aggregate_own_world(records: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {"n_patients": len(records), "parameters": {}, "posterior_predictive": {}}
    for name in k1.PARAM_NAMES:
        truth = np.array([row["parameters"][name]["truth"] for row in records])
        estimates = np.array([row["parameters"][name]["mean"] for row in records])
        parameter_rows = [row["parameters"][name] for row in records]
        output["parameters"][name] = {
            "bias": float(np.mean(estimates - truth)),
            "rmse": float(np.sqrt(np.mean((estimates - truth) ** 2))),
            "correlation": (
                float(np.corrcoef(truth, estimates)[0, 1])
                if len(records) > 1 and np.std(truth) > 0 and np.std(estimates) > 0
                else None
            ),
            "coverage": {
                level: float(np.mean([row["coverage"][level] for row in parameter_rows]))
                for level in ("0.5", "0.8", "0.9", "0.95")
            },
            "mean_interval_width_90": float(np.mean([row["interval_width_90"] for row in parameter_rows])),
        }
    for metric in ("mae", "mean_log_predictive_density", "coverage_90"):
        vals = [row["posterior_predictive"][metric] for row in records]
        vals = [value for value in vals if value is not None]
        output["posterior_predictive"][metric] = float(np.mean(vals)) if vals else None
    return output


def bootstrap_patient_metrics(
    patient_values: list[dict[str, float | None]],
    n_replicates: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    metric_names = sorted({key for row in patient_values for key, value in row.items() if value is not None})
    result: dict[str, Any] = {"n_patients": len(patient_values), "metrics": {}}
    for name in metric_names:
        values = np.array([row[name] for row in patient_values if row[name] is not None], dtype=float)
        boot = np.empty(n_replicates, dtype=float)
        for index in range(n_replicates):
            boot[index] = float(np.mean(rng.choice(values, size=len(values), replace=True)))
        result["metrics"][name] = {
            "estimate": float(np.mean(values)),
            "ci95_patient_bootstrap": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
        }
    return result


def evaluate_product_cohort(
    generator: GeneratorType,
    seed: int,
    n_patients: int,
    config: dict[str, Any],
    posterior_draws: int,
    max_inference_seconds: float,
) -> dict[str, Any]:
    cohort = get_generator(generator, seed=seed).generate_cohort(
        num_patients=n_patients,
        duration_days=float(config["horizon_days"]),
    )
    observations = cohort.to_observations_dataframe(legacy_leaky=False)
    patient_frame = cohort.to_patients_dataframe()
    observations_by_patient = {
        patient_id: rows
        for patient_id, rows in observations.groupby("patient_id", sort=False)
    }
    landmark = float(config["landmark_day"])
    horizon = float(config["horizon_days"])
    low_data_cutoff = int(config["low_data_max_pre_landmark_visits"])
    low_data_stratum = f"low_data_{low_data_cutoff}_or_fewer_pre_landmark_visits"
    rng_root = np.random.SeedSequence([seed, list(GeneratorType).index(generator)])
    child_seeds = rng_root.spawn(len(patient_frame))
    model_names = ("k1", "last_observation_carry_forward", "pre_landmark_linear_trend")
    records_by_stratum: dict[str, dict[str, list[dict[str, float | None]]]] = {
        name: {model: [] for model in model_names}
        for name in ("all_eligible", low_data_stratum)
    }
    excluded = {"no_pre_landmark_history": 0, "no_post_landmark_measurement": 0}
    model_seconds: list[float] = []
    for patient_index, (_, patient) in enumerate(patient_frame.iterrows()):
        pid = patient["patient_id"]
        rows = observations_by_patient[pid]
        rows = rows[
            rows[config["measurement_mask_column"]].astype(bool)
            & rows[config["marker_value_column"]].notna()
        ]
        pre = rows[rows["day"] <= landmark].sort_values("day")
        future = rows[(rows["day"] > landmark) & (rows["day"] <= horizon)].sort_values("day")
        if len(pre) < 2:
            excluded["no_pre_landmark_history"] += 1
            continue
        if len(future) == 0:
            excluded["no_post_landmark_measurement"] += 1
            continue
        days = pre["day"].to_numpy(dtype=np.float64)
        values = pre[config["marker_value_column"]].to_numpy(dtype=np.float64)
        target_days = future["day"].to_numpy(dtype=np.float64)
        target = future[config["marker_value_column"]].to_numpy(dtype=np.float64)
        if not np.all(np.isfinite(values)) or not np.all(np.isfinite(target)):
            raise ValueError("measured CA 15-3 values must be finite")
        obs = k1.K1Observations(days=days, values={"ca153": values})
        route_rng = np.random.default_rng(child_seeds[patient_index])
        started = time.perf_counter()
        posterior = k1.ROUTES["amortized"](obs, route_rng, posterior_draws)
        model_seconds.append(time.perf_counter() - started)
        if model_seconds[-1] > max_inference_seconds:
            raise RuntimeError(
                f"amortized marker forecast exceeded registered per-patient budget: "
                f"{model_seconds[-1]:.3f}s > {max_inference_seconds:.3f}s"
            )
        means = k1._expected_ca153_samples(posterior, target_days)
        noise_sd = k1.OBSERVATION_SD
        predictive = means + route_rng.normal(0.0, noise_sd, size=means.shape)
        log_density = logsumexp(
            -0.5 * ((target[None, :] - means) / noise_sd) ** 2
            - np.log(noise_sd)
            - 0.5 * np.log(2.0 * np.pi),
            axis=0,
        ) - np.log(len(means))
        low, high = np.quantile(predictive, [0.05, 0.95], axis=0)
        pred_mean = np.mean(means, axis=0)
        patient_metrics = {
            "k1": {
                "mae": float(np.mean(np.abs(target - pred_mean))),
                "rmse": float(np.sqrt(np.mean((target - pred_mean) ** 2))),
                "mean_log_predictive_density": float(np.mean(log_density)),
                "predictive_interval_coverage_90": float(np.mean((target >= low) & (target <= high))),
                "predictive_interval_width_90": float(np.mean(high - low)),
                "runtime_seconds": float(model_seconds[-1]),
            },
        }

        last = float(values[-1])
        patient_metrics["last_observation_carry_forward"] = {
            "mae": float(np.mean(np.abs(target - last))),
            "rmse": float(np.sqrt(np.mean((target - last) ** 2))),
        }
        centered = days - np.mean(days)
        design = np.column_stack((np.ones(len(days)), centered))
        coefficients = np.linalg.lstsq(design, values, rcond=None)[0]
        linear = coefficients[0] + (target_days - np.mean(days)) * coefficients[1]
        patient_metrics["pre_landmark_linear_trend"] = {
            "mae": float(np.mean(np.abs(target - linear))),
            "rmse": float(np.sqrt(np.mean((target - linear) ** 2))),
        }
        for model_name, metrics in patient_metrics.items():
            records_by_stratum["all_eligible"][model_name].append(metrics)
            if len(pre) <= low_data_cutoff:
                records_by_stratum[low_data_stratum][model_name].append(metrics)

    bootstrap = int(config["bootstrap_replicates"])
    result: dict[str, Any] = {
        "generator": generator.value,
        "seed": seed,
        "patients_generated": len(patient_frame),
        "patients_excluded": excluded,
        "low_data_max_pre_landmark_visits": low_data_cutoff,
        "strata": {},
    }
    for stratum_index, (stratum, model_rows) in enumerate(records_by_stratum.items()):
        result["strata"][stratum] = {"models": {}}
        for model_index, (name, rows) in enumerate(model_rows.items()):
            result["strata"][stratum]["models"][name] = bootstrap_patient_metrics(
                rows, bootstrap, seed + stratum_index * len(model_names) + model_index
            )
    result["strata"]["all_eligible"]["models"]["k1"]["runtime_p50_seconds"] = (
        float(np.median(model_seconds)) if model_seconds else None
    )
    result["strata"]["all_eligible"]["models"]["k1"]["runtime_p95_seconds"] = (
        float(np.quantile(model_seconds, 0.95)) if model_seconds else None
    )
    return result


def smoke(config: dict[str, Any]) -> None:
    seed = int(config["seed_plan"]["engineering_smoke"])
    rng = np.random.default_rng(seed)
    params = k1.sample_prior(rng)
    observation = k1.simulate_patient(params, k1.SCHEDULE, rng)
    for route_name in ("amortized", "ukf", "npe"):
        posterior = k1.ROUTES[route_name](observation, np.random.default_rng(seed), 32)
        if any(len(posterior[name]) != 32 or not np.isfinite(posterior[name]).all() for name in k1.PARAM_NAMES):
            raise AssertionError(f"{route_name} returned malformed smoke draws")
    print("K1 route smoke check passed; no study cohort was accessed.")


def render_report(results: dict[str, Any]) -> str:
    lines = [
        "# EXP-K1-004 Report — canonical inference and marker transfer",
        "",
        "> All results are synthetic. K1 recurrence-risk use is disabled; marker forecasting is not recurrence prediction.",
        "",
        f"Protocol: {results['protocol_version']}  ",
        f"Evaluation source commit: `{results['evaluation_source_commit']}`  ",
        f"Training source commit: `{results['training']['source_commit']}`  ",
        "",
        "## Own-world parameter inference",
        "",
        "Per-setting/seed parameter bias, RMSE, coverage and predictive checks are recorded in `results.json`. NUTS is limited to the preregistered common 30-patient subset per setting/seed and reports chain diagnostics. The immutable acceptance-suite result is a separate gate and is not used for tuning.",
        "",
        "## Product-simulator marker forecasting",
        "",
        f"Forecasts use measured CA 15-3 values only. The measurement flag selects rows; it is never passed as a value. No recurrence labels or latent outcome fields are read by the forecasting evaluation. G1/G2/G3 results are reported separately by seed, for all eligible patients and for the at-most-{results['product_world'][0]['low_data_max_pre_landmark_visits']}-pre-landmark-visit subgroup, with patient-cluster bootstrap intervals.",
        "",
        "| Stratum | Generator | Seed | Eligible patients | K1 MAE | Carry-forward MAE | Linear-trend MAE | K1 90% interval coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results["product_world"]:
        for stratum, content in row["strata"].items():
            models = content["models"]
            k1_mae = models["k1"]["metrics"].get("mae", {}).get("estimate")
            carry_mae = models["last_observation_carry_forward"]["metrics"].get("mae", {}).get("estimate")
            linear_mae = models["pre_landmark_linear_trend"]["metrics"].get("mae", {}).get("estimate")
            coverage = models["k1"]["metrics"].get("predictive_interval_coverage_90", {}).get("estimate")
            lines.append(
                f"| {stratum} | {row['generator']} | {row['seed']} | {models['k1']['n_patients']} | "
                f"{f'{k1_mae:.4f}' if k1_mae is not None else 'NA'} | "
                f"{f'{carry_mae:.4f}' if carry_mae is not None else 'NA'} | "
                f"{f'{linear_mae:.4f}' if linear_mae is not None else 'NA'} | "
                f"{f'{coverage:.4f}' if coverage is not None else 'NA'} |"
            )
    lines.extend(
        [
            "",
            "## Limits and decision",
            "",
            "Own-world recovery establishes behavior only under the declared synthetic likelihood. Product-world CA 15-3 forecasts test transfer of that measurement model and do not validate recurrence prediction. The simulator does not expose K1's four latent parameters, and its recurrence process is separate. K1 remains research-only; see `PROP-K1-EVENT-SEMANTICS.md` and the model card.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="check trained routes without generating study cohorts")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    training = json.loads(TRAINING_RESULTS.read_text(encoding="utf-8"))
    verify_artifacts(config, training)
    if args.smoke:
        smoke(config)
        return

    source_commit = git_output("rev-parse", "HEAD")
    access = {
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "source_commit": source_commit,
        "config_sha256": sha256(CONFIG_PATH),
        "training_results_sha256": sha256(TRAINING_RESULTS),
        "environment_lock_sha256": sha256(ROOT / "uv.lock"),
        "started_utc_epoch": time.time(),
        "g3_frozen_transfer_accessed": False,
        "completed": False,
        "seed_plan": config["seed_plan"],
    }
    if ACCESS_LOG_PATH.exists():
        raise RuntimeError("EXP-K1-004 access log exists; frozen evaluation cannot be repeated")
    write_access_log(access)

    own_results: dict[str, Any] = {}
    routes = ("amortized", "ukf", "nuts", "npe")
    own_config = config["own_world"]
    final_seeds = config["seed_plan"]["own_world_final"]
    for setting_index, setting in enumerate(own_config["settings"]):
        own_results[setting] = {}
        for seed in final_seeds:
            print(f"Own-world {setting}, seed={seed}", flush=True)
            aggregates: dict[str, list[dict[str, Any]]] = {name: [] for name in routes}
            route_ranks: dict[str, dict[str, list[float]]] = {
                route: {param: [] for param in k1.PARAM_NAMES} for route in routes
            }
            route_diagnostics: dict[str, list[dict[str, Any]]] = {name: [] for name in routes}
            agreement: dict[str, list[float]] = {name: [] for name in routes if name != "nuts"}
            route_runtime: dict[str, list[float]] = {name: [] for name in routes}
            route_prior_only: dict[str, int] = {name: 0 for name in routes}
            particle_diagnostics: list[dict[str, Any]] = []
            for patient_index in range(own_config["patients_per_final_setting_seed"]):
                rng = np.random.default_rng(np.random.SeedSequence([seed, setting_index, patient_index]))
                truth, obs = make_own_world_observation(
                    rng, setting, own_config["setting_parameters"][setting]
                )
                use_nuts = patient_index < own_config["nuts_patients_per_setting_seed"]
                draws: dict[str, dict[str, Any]] = {}
                for route in routes:
                    if route == "nuts" and not use_nuts:
                        continue
                    n_draws = (
                        config["resource_budgets"]["nuts_route_total_draws"]
                        if route == "nuts"
                        else own_config["posterior_draws"]
                    )
                    route_seed = int(rng.integers(0, 2**32 - 1))
                    route_started = time.perf_counter()
                    posterior = k1.ROUTES[route](obs, np.random.default_rng(route_seed), n_draws)
                    route_runtime[route].append(time.perf_counter() - route_started)
                    route_prior_only[route] += int(posterior.get("prior_only", False))
                    summary, rank = summarize_posterior(
                        truth, posterior, obs, np.random.default_rng(route_seed + 1)
                    )
                    draws[route] = posterior
                    aggregates[route].append(summary)
                    for param in k1.PARAM_NAMES:
                        route_ranks[route][param].extend(rank[param])
                    if route == "nuts" and "diagnostics" in posterior:
                        route_diagnostics[route].append(posterior["diagnostics"])
                    if route == "ukf" and "diagnostics" in posterior:
                        particle_diagnostics.append(posterior["diagnostics"])
                if use_nuts:
                    reference = np.mean(draws["nuts"]["doubling_time_days"])
                    for route in agreement:
                        interval = np.quantile(draws[route]["doubling_time_days"], [0.025, 0.975])
                        agreement[route].append(
                            float(abs(np.mean(draws[route]["doubling_time_days"]) - reference))
                        )
                        route_diagnostics.setdefault(f"{route}_reference_coverage", []).append(
                            {"nuts_mean_in_route_95_interval": bool(interval[0] <= reference <= interval[1])}
                        )
            route_metrics = {}
            for route in routes:
                if not aggregates[route]:
                    route_metrics[route] = {"n_patients": 0, "not_run": "outside registered NUTS reference subset"}
                    continue
                route_metrics[route] = aggregate_own_world(aggregates[route])
                route_metrics[route]["prior_only_patients"] = route_prior_only[route]
                route_metrics[route]["runtime_seconds"] = {
                    "median": float(np.median(route_runtime[route])),
                    "p95": float(np.quantile(route_runtime[route], 0.95)),
                    "maximum": float(np.max(route_runtime[route])),
                }
                route_metrics[route]["sbc_ks_pvalues"] = {
                    param: float(kstest(route_ranks[route][param], "uniform").pvalue)
                    for param in k1.PARAM_NAMES
                }
                if route == "nuts" and route_diagnostics[route]:
                    route_metrics[route]["diagnostics"] = {
                        "r_hat_max": {
                            param: float(max(d["r_hat"][param] for d in route_diagnostics[route]))
                            for param in k1.PARAM_NAMES
                        },
                        "effective_sample_size_min": {
                            param: float(min(d["effective_sample_size"][param] for d in route_diagnostics[route]))
                            for param in k1.PARAM_NAMES
                        },
                        "divergences_total": int(sum(d["divergences"] for d in route_diagnostics[route])),
                    }
                if route == "ukf":
                    observed_particle_diagnostics = [
                        item for item in particle_diagnostics if item["ess_fraction_min"] is not None
                    ]
                    route_metrics[route]["particle_filter_diagnostics"] = {
                        "patients_with_observations": len(observed_particle_diagnostics),
                        "minimum_ess_fraction": (
                            float(min(item["ess_fraction_min"] for item in observed_particle_diagnostics))
                            if observed_particle_diagnostics
                            else None
                        ),
                        "median_patient_ess_fraction": (
                            float(np.median([item["ess_fraction_median"] for item in observed_particle_diagnostics]))
                            if observed_particle_diagnostics
                            else None
                        ),
                        "mean_resampling_count": (
                            float(np.mean([item["resampling_count"] for item in observed_particle_diagnostics]))
                            if observed_particle_diagnostics
                            else None
                        ),
                        "median_unique_particles_final": (
                            float(np.median([item["unique_particles_final"] for item in observed_particle_diagnostics]))
                            if observed_particle_diagnostics
                            else None
                        ),
                    }
                if route in agreement:
                    route_metrics[route]["agreement_with_nuts"] = {
                        "mean_absolute_difference_doubling_time_days": float(np.mean(agreement[route])),
                        "reference_mean_in_route_95_interval_fraction": float(
                            np.mean(
                                [
                                    row["nuts_mean_in_route_95_interval"]
                                    for row in route_diagnostics[f"{route}_reference_coverage"]
                                ]
                            )
                        ),
                    }
            own_results[setting][str(seed)] = route_metrics

    product_results = []
    product_config = config["product_world"]
    for generator_name in ("G1", "G2", "G3"):
        generator = {
            "G1": GeneratorType.G1_SMOOTH,
            "G2": GeneratorType.G2_BURST,
            "G3": GeneratorType.G3_NOISE,
        }[generator_name]
        seeds = (
            config["seed_plan"]["product_world_frozen_transfer"]
            if generator_name == "G3"
            else config["seed_plan"]["product_world_development"]
        )
        for seed in seeds:
            if generator_name == "G3":
                access["g3_frozen_transfer_accessed"] = True
                access["g3_first_access_utc_epoch"] = time.time()
                write_access_log(access)
            print(f"Marker transfer {generator_name}, seed={seed}", flush=True)
            product_results.append(
                evaluate_product_cohort(
                    generator,
                    seed,
                    product_config["patients_per_generator_seed"],
                    product_config,
                    own_config["posterior_draws"],
                    config["resource_budgets"]["maximum_product_route_inference_seconds_per_patient"],
                )
            )

    results = {
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "generated_utc_epoch": time.time(),
        "evaluation_source_commit": source_commit,
        "training": training,
        "runtime_environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dependency_lock_sha256": sha256(ROOT / "uv.lock"),
        },
        "own_world": own_results,
        "product_world": product_results,
        "identifiability": k1.HybridKineticModelK1().identifiability_analysis(),
        "recurrence_risk_status": "DISABLED; current synthetic one-doubling event is not the vigil-sim recurrence estimand",
    }
    RESULT_PATH.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(results), encoding="utf-8")
    access["completed"] = True
    access["completed_utc_epoch"] = time.time()
    access["results_sha256"] = sha256(RESULT_PATH)
    write_access_log(access)
    print(f"Wrote {RESULT_PATH.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
