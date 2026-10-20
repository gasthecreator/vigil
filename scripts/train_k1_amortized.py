#!/usr/bin/env python3
"""Train and select K1 synthetic parameter-inference estimators reproducibly."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file
from vigil_ml import k1

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT = ROOT / "experiments" / "EXP-K1-004"
MODEL_DIR = ROOT / "packages" / "vigil-ml" / "vigil_ml" / "models"
RUNNER = EXPERIMENT / "run.py"
REPRODUCTION_SCRIPT = ROOT / "scripts" / "reproduce_k1_exp004.sh"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def train_family(family: str, config: dict) -> dict:
    candidates = []
    estimator_config = config["neural_estimators"]
    for train_seed, validation_seed in estimator_config["train_validation_seed_pairs"]:
        n_sims = estimator_config["simulations_per_train_seed"]
        if family == "amortized":
            result = k1.train_amortized(
                n_sims=n_sims,
                seed=train_seed,
                epochs=estimator_config["amortized_max_epochs"],
                validation_seed=validation_seed,
            )
        else:
            result = k1.train_npe(
                n_sims=n_sims,
                seed=train_seed,
                epochs=estimator_config["npe_max_epochs"],
                validation_seed=validation_seed,
            )
        validation_history = result.get("val_nll", result["val_loss"])
        selected_epoch = int(result["selected_epoch"]) - 1
        if selected_epoch != min(
            range(len(validation_history)), key=lambda index: validation_history[index]
        ):
            raise RuntimeError("trainer selected a checkpoint inconsistent with validation NLL")
        validation_nll = validation_history[selected_epoch]
        candidates.append(
            {
                "seed": train_seed,
                "validation_seed": validation_seed,
                "validation_nll": validation_nll,
                "selected_epoch": selected_epoch + 1,
                "train_loss": result["train_loss"],
                "validation_loss": result["val_loss"],
                "validation_nll_history": validation_history,
                "model": result["model"],
            }
        )
        print(
            f"{family} seed={train_seed}: validation NLL "
            f"{result.get('val_nll', result['val_loss'])[0]:.6f} -> {validation_nll:.6f}",
            flush=True,
        )
    selected = min(candidates, key=lambda item: (item["validation_nll"], item["seed"]))
    artifact_name = f"k1_{family}_weights.safetensors"
    artifact_path = MODEL_DIR / artifact_name
    save_file(
        {name: tensor.detach().cpu().contiguous() for name, tensor in selected["model"].state_dict().items()},
        str(artifact_path),
        metadata={
            "experiment_id": config["experiment_id"],
            "protocol_version": config["protocol_version"],
            "estimator": family,
            "selected_training_seed": str(selected["seed"]),
            "validation_seed": str(selected["validation_seed"]),
            "selection_metric": "validation_negative_log_likelihood",
        },
    )
    for candidate in candidates:
        del candidate["model"]
    return {
        "selected_seed": selected["seed"],
        "selected_validation_seed": selected["validation_seed"],
        "selected_validation_nll": selected["validation_nll"],
        "candidates": candidates,
        "artifact": artifact_name,
        "artifact_sha256": sha256(artifact_path),
    }


def main() -> None:
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    if dirty:
        raise SystemExit("Refusing registered K1 fitting from a dirty source tree")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    config_path = MODEL_DIR / "k1_assumptions.json"
    source_path = Path(k1.__file__)
    config = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))
    baseline_is_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", config["code_baseline"], commit],
        cwd=ROOT,
        check=False,
    )
    if baseline_is_ancestor.returncode != 0:
        raise SystemExit("EXP-K1-004 source commit does not descend from its registered baseline")
    experiment_training = config["neural_estimators"]
    registered_pairs = experiment_training["train_validation_seed_pairs"]
    if len(registered_pairs) != 3 or any(len(pair) != 2 for pair in registered_pairs):
        raise SystemExit("Training seed plan differs from the registered protocol")
    if experiment_training["minibatch_size"] != k1.TRAINING_CONFIG["batch_size"]:
        raise SystemExit("Minibatch size differs from the registered assumptions")
    if experiment_training["time_bins"] != len(k1.SCHEDULE):
        raise SystemExit("Feature time-bin count differs from the registered assumptions")
    for family, config_key in (("amortized", "amortized_max_epochs"), ("npe", "npe_max_epochs")):
        if experiment_training[config_key] > config["resource_budgets"][f"{family}_training_epochs_max"]:
            raise SystemExit(f"{family} epoch count exceeds the registered resource budget")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    torch.use_deterministic_algorithms(True)
    results = {
        "experiment_id": "EXP-K1-004",
        "protocol_version": config["protocol_version"],
        "source_commit": commit,
        "source_sha256": sha256(source_path),
        "assumptions_sha256": sha256(config_path),
        "experiment_config_sha256": sha256(EXPERIMENT / "config.json"),
        "simulator_source_sha256": sha256(ROOT / "packages" / "vigil-sim" / "vigil_sim" / "generators.py"),
        "runner_source_sha256": sha256(RUNNER),
        "reproduction_script_sha256": sha256(REPRODUCTION_SCRIPT),
        "environment_lock_sha256": sha256(ROOT / "uv.lock"),
        "runtime_environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": importlib.metadata.version("torch"),
            "numpy": importlib.metadata.version("numpy"),
            "jax": importlib.metadata.version("jax"),
            "numpyro": importlib.metadata.version("numpyro"),
        },
        "command": ["python", "scripts/train_k1_amortized.py"],
        "clean_source_tree_at_fit": True,
        "estimators": {},
    }
    for family in ("amortized", "npe"):
        results["estimators"][family] = train_family(family, config)
    artifact_entries = {}
    for family, result in results["estimators"].items():
        with safe_open(str(MODEL_DIR / result["artifact"]), framework="pt", device="cpu") as artifact:
            metadata = artifact.metadata() or {}
        artifact_entries[result["artifact"]] = {
            "sha256": result["artifact_sha256"],
            "estimator": family,
            "metadata": metadata,
        }
    manifest = {
        "schema_version": 1,
        "assumptions_sha256": sha256(config_path),
        "artifacts": artifact_entries,
    }
    (MODEL_DIR / "k1_artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    out = EXPERIMENT / "training_results.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
