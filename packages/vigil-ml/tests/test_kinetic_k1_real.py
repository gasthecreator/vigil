"""Tests for K1's declared synthetic parameter-inference implementation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from safetensors.torch import save_file
from vigil_ml import k1


def test_observations_reject_misaligned_or_unsorted_data():
    with pytest.raises(ValueError, match="strictly increasing"):
        k1.K1Observations(np.array([0.0, 0.0]), {"ca153": np.array([18.0, 19.0])})
    with pytest.raises(ValueError, match="align with days"):
        k1.K1Observations(np.array([0.0, 30.0]), {"ca153": np.array([18.0])})
    with pytest.raises(ValueError, match="never infinite"):
        k1.K1Observations(np.array([0.0]), {"ca153": np.array([np.inf])})


@pytest.mark.parametrize(
    ("days", "values", "match"),
    [
        ([True], {"ca153": [18.0]}, "days.*boolean"),
        ([0.0], {"ca153": [True]}, "ca153.*boolean"),
        ([0.0, 1.0], {"ca153": [False, 18.0]}, "ca153.*boolean"),
    ],
)
def test_observations_reject_boolean_time_and_mask_values(days, values, match):
    with pytest.raises(ValueError, match=match):
        k1.K1Observations(np.asarray(days), values)


def test_trained_artifact_loader_requires_registered_identity_and_finite_weights(tmp_path):
    path = tmp_path / "weights.safetensors"
    manifest_path = tmp_path / "manifest.json"
    assumptions_path = k1.ASSUMPTIONS_PATH
    old_manifest_path = k1.ARTIFACT_MANIFEST_PATH
    registered = {
        "experiment_id": "EXP-K1-004",
        "estimator": "amortized",
        "selection_metric": "validation_negative_log_likelihood",
        "protocol_version": "1.10",
        "selected_training_seed": "41002",
        "validation_seed": "42002",
    }
    def write_artifact(weights, metadata):
        save_file(weights, str(path), metadata=metadata)
        manifest_path.write_text(json.dumps({
            "assumptions_sha256": hashlib.sha256(assumptions_path.read_bytes()).hexdigest(),
            "artifacts": {path.name: {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "estimator": "amortized",
                "metadata": registered,
            }},
        }), encoding="utf-8")

    k1.ARTIFACT_MANIFEST_PATH = manifest_path
    try:
        write_artifact({"weight": torch.tensor([1.0])}, registered)
        assert torch.equal(k1._load_registered_state_dict(path, "amortized")["weight"], torch.tensor([1.0]))

        write_artifact({"weight": torch.tensor([1.0])}, {**registered, "estimator": "npe"})
        with pytest.raises(ValueError, match="metadata"):
            k1._load_registered_state_dict(path, "amortized")

        write_artifact({"weight": torch.tensor([float("nan")])}, registered)
        with pytest.raises(ValueError, match="finite model weights"):
            k1._load_registered_state_dict(path, "amortized")

        write_artifact({"weight": torch.tensor([1.0])}, registered)
        with pytest.raises(ValueError, match="digest"):
            path.write_bytes(path.read_bytes() + b"tampered")
            k1._load_registered_state_dict(path, "amortized")
    finally:
        k1.ARTIFACT_MANIFEST_PATH = old_manifest_path


def test_frozen_k1_trainer_refuses_to_overwrite_registered_artifacts():
    root = Path(__file__).resolve().parents[3]
    script = root / "scripts" / "train_k1_amortized.py"
    training = root / "experiments" / "EXP-K1-004" / "training_results.json"
    protected_artifacts = (
        training,
        k1.AMORTIZED_WEIGHTS_PATH,
        k1.NPE_WEIGHTS_PATH,
        k1.ARTIFACT_MANIFEST_PATH,
    )
    before = tuple(path.read_bytes() for path in protected_artifacts)
    result = subprocess.run(
        [sys.executable, str(script)], cwd=root, capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert "refusing to overwrite" in result.stderr
    assert tuple(path.read_bytes() for path in protected_artifacts) == before


def test_forward_simulator_and_inference_share_observation_likelihood():
    rng = np.random.default_rng(1701)
    params = k1.sample_prior(rng)
    simulated = k1.simulate_patient(params, [0.0, 47.0, 123.0, 281.0], rng)
    expected = k1._expected_ca153(params, simulated.days)
    on_mean = k1.K1Observations(simulated.days, {"ca153": expected})
    off_mean = k1.K1Observations(
        simulated.days,
        {"ca153": expected + 3.0 * k1.OBSERVATION_SD},
    )
    assert k1._log_likelihood(params, on_mean) > k1._log_likelihood(params, off_mean)
    assert simulated.days.tolist() == [0.0, 47.0, 123.0, 281.0]


def test_particle_filter_returns_finite_prior_and_conditioned_draws():
    rng = np.random.default_rng(33)
    prior = k1.K1Observations(np.array([0.0, 30.0]), {"ca153": np.array([np.nan, np.nan])})
    prior_draws = k1.ROUTES["ukf"](prior, np.random.default_rng(7), 200)
    assert prior_draws["prior_only"] is True
    assert all(np.isfinite(prior_draws[name]).all() for name in k1.PARAM_NAMES)

    params = k1.sample_prior(rng)
    observations = k1.simulate_patient(params, [0.0, 60.0, 150.0, 300.0], rng)
    posterior = k1.ROUTES["ukf"](observations, np.random.default_rng(8), 200)
    assert all(np.isfinite(posterior[name]).all() for name in k1.PARAM_NAMES)
    assert all(len(posterior[name]) == 200 for name in k1.PARAM_NAMES)
    assert posterior["diagnostics"]["resampling_count"] >= 0
    assert 0.0 < posterior["diagnostics"]["ess_fraction_min"] <= 1.0


def test_all_routes_abstain_to_prior_when_no_measurements_exist():
    prior = k1.K1Observations(
        np.asarray([0.0, 60.0, 120.0]),
        {"ca153": np.asarray([np.nan, np.nan, np.nan])},
    )
    for route in ("amortized", "ukf", "nuts", "npe"):
        result = k1.ROUTES[route](prior, np.random.default_rng(814), 64)
        assert result["prior_only"] is True
        assert all(len(result[name]) == 64 for name in k1.PARAM_NAMES)
        assert all(np.isfinite(result[name]).all() for name in k1.PARAM_NAMES)


def test_model_fails_closed_for_unsupported_recurrence_prediction():
    model = k1.HybridKineticModelK1()
    with pytest.raises(RuntimeError, match="recurrence-risk prediction is disabled"):
        model.predict_risk(k1.K1Observations(np.array([0.0]), {"ca153": np.array([18.0])}))


def test_synthetic_one_doubling_event_probability_is_monotone():
    samples = {
        "doubling_time_days": np.array([80.0, 120.0, 150.0]),
        "onset_day": np.array([60.0, 90.0, 120.0]),
    }
    base = k1.risk_from_posterior(samples, 240.0)
    shorter = dict(samples, doubling_time_days=samples["doubling_time_days"] / 2.0)
    assert k1.risk_from_posterior(shorter, 240.0) >= base
    assert k1.risk_from_posterior(samples, 360.0) >= base


def test_identifiability_spectrum_is_data_computed_and_dimensioned():
    result = k1.HybridKineticModelK1().identifiability_analysis()
    eigenvalues = np.asarray(result["eigenvalues"])
    assert len(eigenvalues) == len(k1.PARAM_NAMES)
    assert np.isfinite(eigenvalues).all()
    assert len(result["non_identifiable"]) == result["expected_non_identifiable_count"]
    assert set(result["non_identifiable"]) <= set(k1.PARAM_NAMES)


@pytest.mark.parametrize("family", ["amortized", "npe"])
def test_neural_training_uses_independent_validation_checkpoint(family):
    if family == "amortized":
        result = k1.train_amortized(n_sims=10, seed=912, epochs=2, validation_seed=913)
    else:
        result = k1.train_npe(n_sims=10, seed=912, epochs=2, validation_seed=913)
    history = result.get("val_nll", result["val_loss"])
    expected_epoch = min(range(len(history)), key=lambda index: history[index]) + 1
    assert result["selected_epoch"] == expected_epoch
    assert len(result["train_loss"]) == len(history) == 2
    assert np.isfinite(history).all()
