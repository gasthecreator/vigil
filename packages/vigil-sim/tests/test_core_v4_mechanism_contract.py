"""Production-path checks for the preregistered core-v4 mechanism study."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import vigil_sim.generators as generators
from vigil_eval.leakage import run_latent_column_canary
from vigil_sim.generators import GeneratorType, get_generator
from vigil_sim.mechanisms import (
    draw_lognormal_event_amplitudes,
    draw_patient_shot_noise_trace,
    evaluate_first_order_on_fixed_grid,
    patient_rng,
    shot_noise_at_times,
)

PROFILE_PATH = (
    Path(__file__).parents[1]
    / "vigil_sim"
    / "config"
    / "synthetic_population_core_v4.json"
)


def _profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def _rk4_fixed_grid(
    burden_at_day, observation_days, step, secretion, clearance, subdivisions=16
):
    """Independent RK4 implementation with production's frozen left-edge ZOH."""
    result = []
    state = 0.0
    grid_day = 0.0
    for target in observation_days:
        while grid_day + step <= target:
            burden = float(burden_at_day(grid_day))
            h = step / subdivisions

            def derivative(value):
                return secretion * burden - clearance * value

            for _ in range(subdivisions):
                k1 = derivative(state)
                k2 = derivative(state + h * k1 / 2.0)
                k3 = derivative(state + h * k2 / 2.0)
                k4 = derivative(state + h * k3)
                state += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
            grid_day += step
        if target > grid_day:
            h_total = target - grid_day
            burden = float(burden_at_day(grid_day))
            h = h_total / subdivisions

            def derivative(value):
                return secretion * burden - clearance * value

            for _ in range(subdivisions):
                k1 = derivative(state)
                k2 = derivative(state + h * k1 / 2.0)
                k3 = derivative(state + h * k2 / 2.0)
                k4 = derivative(state + h * k3)
                state += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
            grid_day = target
        result.append(state)
    return np.asarray(result)


@pytest.mark.parametrize(
    "analyte,secretion_key,clearance_key,latent_key",
    [
        ("ca153", "ca153_secretion_per_burden_day", "ca153_clearance_rate_per_day", "m_ca153"),
        ("cea", "cea_secretion_per_burden_day", "cea_clearance_rate_per_day", "m_cea"),
    ],
)
def test_g1_generator_path_matches_independent_rk4(
    monkeypatch, analyte, secretion_key, clearance_key, latent_key
):
    profile = _profile()
    kinetics = profile["generator_mechanics"]["g1"]["marker_kinetics"]
    generator = get_generator(GeneratorType.G1_SMOOTH, seed=12012, population_config=profile)
    patient = generator.sample_baseline(1)
    patient.true_recurrence_event = True
    patient.true_recurrence_day = 600.0
    patient.true_recurrence_site = "liver"
    days = [0.0, 365.0, 730.0]

    captured = []
    production_helper = generators.evaluate_first_order_on_fixed_grid

    def capture(*args, **kwargs):
        captured.append((args, kwargs))
        return production_helper(*args, **kwargs)

    monkeypatch.setattr(generators, "evaluate_first_order_on_fixed_grid", capture)
    _observations, _masks, latent = generator.simulate_longitudinal_trajectory(patient, days)

    call_index = 0 if analyte == "ca153" else 1
    args, kwargs = captured[call_index]
    burden_at_day = kwargs.get("burden_at_day", args[1])
    secretion = kwargs.get("secretion_per_burden_day", args[2])
    clearance = kwargs.get("clearance_rate_per_day", args[3])
    step = kwargs.get("integration_step_days", args[4])
    assert secretion == kinetics[secretion_key]
    assert clearance == kinetics[clearance_key]
    assert step == kinetics["integration_step_days"]
    expected = _rk4_fixed_grid(burden_at_day, days, step, secretion, clearance)
    observed = [getattr(state, latent_key) for state in latent]
    np.testing.assert_allclose(observed, expected, rtol=0.0, atol=1e-6)


def test_g2_generator_uses_shared_patient_trace_and_profile_clearance(monkeypatch):
    profile = _profile()
    shot = profile["generator_mechanics"]["g2"]["shot_noise"]
    generator = get_generator(GeneratorType.G2_BURST, seed=12013, population_config=profile)
    patient = generator.sample_baseline(1)
    patient.true_recurrence_event = True
    patient.true_recurrence_day = 600.0
    patient.true_recurrence_site = "liver"
    patient.competing_event_day = None
    patient.administrative_censor_day = 730.0
    days = [0.0, 90.0, 365.0, 730.0]

    traces = []
    production_trace = generators.draw_patient_shot_noise_trace

    def capture(*args, **kwargs):
        trace = production_trace(*args, **kwargs)
        traces.append((args, kwargs, trace))
        return trace

    monkeypatch.setattr(generators, "draw_patient_shot_noise_trace", capture)
    _observations, _masks, latent = generator.simulate_longitudinal_trajectory(patient, days)
    args, _kwargs, (event_times, amplitudes) = traces[0]
    assert args[0] == generator.seed
    assert args[1] == patient.patient_id
    assert args[2] == 600.0
    assert args[3:] == (
        shot["event_rate_per_day"],
        shot["burden_amplitude_mean"],
        shot["burden_amplitude_coefficient_of_variation"],
    )
    assert event_times.size == latent[-1].mechanism_event_count
    expected_ca = shot_noise_at_times(
        days,
        event_times,
        amplitudes * profile["generator_mechanics"]["g2"]["ca153_per_burden"],
        shot["ca153_clearance_rate_per_day"],
    )
    expected_cea = shot_noise_at_times(
        days,
        event_times,
        amplitudes * profile["generator_mechanics"]["g2"]["cea_per_burden"],
        shot["cea_clearance_rate_per_day"],
    )
    np.testing.assert_allclose([x.m_ca153 for x in latent], expected_ca, rtol=0, atol=1e-12)
    np.testing.assert_allclose([x.m_cea for x in latent], expected_cea, rtol=0, atol=1e-12)


def test_patient_trace_is_stable_and_amplitudes_follow_registered_lognormal_parameters():
    args = (20261201, "VIG-PT-00017", 365.0, 0.02, 15.0, 0.5)
    first = draw_patient_shot_noise_trace(*args)
    second = draw_patient_shot_noise_trace(*args)
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])
    assert np.all(first[1] > 0.0)
    assert np.array_equal(
        draw_lognormal_event_amplitudes(
            3, 15.0, 0.5, patient_rng(9, "patient", "amplitude-test")
        ),
        draw_lognormal_event_amplitudes(
            3, 15.0, 0.5, patient_rng(9, "patient", "amplitude-test")
        ),
    )
    with pytest.raises(ValueError, match="positive"):
        draw_lognormal_event_amplitudes(1, 0.0, 0.5, np.random.default_rng(1))


@pytest.mark.parametrize(
    "burden_at_day",
    [
        lambda day: 3.0 if day < 4.0 else 9.0,
        lambda day: 2.0 + np.sin(day / 10.0),
    ],
    ids=["piecewise-constant", "smooth-burden"],
)
def test_fixed_grid_integration_matches_independent_solver_for_registered_functions(
    burden_at_day,
):
    days = [0.0, 7.0, 18.0]
    production = evaluate_first_order_on_fixed_grid(days, burden_at_day, 0.4, 0.03, 1.0)
    independent = _rk4_fixed_grid(burden_at_day, days, 1.0, 0.4, 0.03)
    np.testing.assert_allclose(production, independent, rtol=0.0, atol=1e-6)


def test_mechanism_trace_stays_out_of_observation_feature_and_label_exports():
    from vigil_ml.features import WindowedFeatureExtractor

    profile = _profile()
    cohort = get_generator(
        GeneratorType.G2_BURST, seed=12014, population_config=profile
    ).generate_cohort(num_patients=30, duration_days=730.0)
    observations = cohort.to_observations_dataframe()
    patients = cohort.to_patients_dataframe()
    forbidden = {"event_times", "event_amplitudes", "mechanism_trace", "future_latent_truth"}
    assert forbidden.isdisjoint(observations.columns)
    assert forbidden.isdisjoint(patients.columns)
    features, labels, _times, _events = WindowedFeatureExtractor().transform_cohort(
        patients_df=patients, observations_df=observations, horizon_days=365.0
    )
    run_latent_column_canary(features)
    assert forbidden.isdisjoint(features.columns)
    assert "true_recurrence" not in str(labels.name)
    assert labels.attrs["target_estimand"] == "observed_diagnosis"
    assert not any("mechanism_event_count" in name for name in features.columns)
