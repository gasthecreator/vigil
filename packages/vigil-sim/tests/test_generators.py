"""
Tests for vigil_sim.generators: Mechanistic cohort generators G1, G2, G3 and anti-leakage invariants.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from vigil_sim.generators import (
    GeneratorType,
    get_generator,
)


def test_generator_instantiation():
    for gen_type in [GeneratorType.G1_SMOOTH, GeneratorType.G2_BURST, GeneratorType.G3_NOISE]:
        gen = get_generator(gen_type, seed=42)
        assert gen.get_generator_type() == gen_type


def test_deterministic_seed_reproducibility():
    gen1 = get_generator(GeneratorType.G1_SMOOTH, seed=123)
    cohort1 = gen1.generate_cohort(num_patients=20, duration_days=365.0)

    gen2 = get_generator(GeneratorType.G1_SMOOTH, seed=123)
    cohort2 = gen2.generate_cohort(num_patients=20, duration_days=365.0)

    assert len(cohort1.patients) == len(cohort2.patients)
    for p1, p2 in zip(cohort1.patients, cohort2.patients):
        assert p1.patient_id == p2.patient_id
        assert p1.age == pytest.approx(p2.age)
        assert p1.stage == p2.stage
        assert p1.subtype == p2.subtype
        assert p1.true_recurrence_event == p2.true_recurrence_event

    df1 = cohort1.to_observations_dataframe()
    df2 = cohort2.to_observations_dataframe()
    pd.testing.assert_frame_equal(df1, df2)


def test_observation_export_excludes_latent_truth_columns():
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=81).generate_cohort(
        num_patients=20, duration_days=365.0
    )

    observations = cohort.to_observations_dataframe()

    assert not any(column.startswith("latent_") for column in observations.columns)
    with pytest.raises(TypeError, match="legacy_leaky"):
        cohort.to_observations_dataframe(legacy_leaky=True)
    for analyte in cohort.observations[0].analytes:
        unobserved = ~observations[f"observed_{analyte}"]
        assert observations.loc[unobserved, analyte].isna().all()


def test_legacy_synthetic_profile_is_explicit_and_matches_its_assumptions():
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=999)
    cohort = gen.generate_cohort(num_patients=300, duration_days=365.0)
    pts_df = cohort.to_patients_dataframe()

    cfg = gen.population_config
    assert cfg["profile_id"] == "legacy_synthetic_v0"
    assert "not sourced Nigerian population estimates" in cfg["interpretation"]
    assert pts_df["age"].between(cfg["age_years"]["minimum"], cfg["age_years"]["maximum"]).all()
    expected_stage = cfg["stage_probabilities"]
    observed_stage = pts_df["stage"].value_counts(normalize=True)
    for stage, probability in zip(("Stage I", "Stage II", "Stage III", "Stage IV"), expected_stage):
        tolerance = 4 * np.sqrt(probability * (1 - probability) / len(pts_df))
        assert abs(observed_stage.get(stage, 0.0) - probability) <= tolerance

    expected_subtypes = cfg["subtype_probabilities"]
    observed_subtype = pts_df["subtype"].value_counts(normalize=True)
    for subtype, probability in zip(("TNBC", "HR+HER2-", "HER2+"), expected_subtypes):
        tolerance = 4 * np.sqrt(probability * (1 - probability) / len(pts_df))
        assert abs(observed_subtype.get(subtype, 0.0) - probability) <= tolerance


def test_profile_override_is_seeded_and_rejects_invalid_probabilities():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_v1.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    first = get_generator(GeneratorType.G1_SMOOTH, seed=77, population_config=profile)
    second = get_generator(GeneratorType.G1_SMOOTH, seed=77, population_config=profile)
    assert [first.sample_baseline(i).stage for i in range(1, 20)] == [
        second.sample_baseline(i).stage for i in range(1, 20)
    ]

    invalid = {**profile, "stage_probabilities": [0.5, 0.5, 0.5, 0.5]}
    with pytest.raises(ValueError, match="stage_probabilities"):
        get_generator(GeneratorType.G1_SMOOTH, seed=77, population_config=invalid)

    invalid = {**profile, "recurrence_day_cap": float("nan")}
    with pytest.raises(ValueError, match="recurrence_day_cap"):
        get_generator(GeneratorType.G1_SMOOTH, seed=77, population_config=invalid)


def test_k3_profile_shares_lab_effects_within_facility_and_records_verification():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_k3_v2.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=48101, population_config=profile).generate_cohort(
        num_patients=500, duration_days=730.0
    )

    facilities = {}
    for patient in cohort.patients:
        effect = (patient.lab_offsets["ca_15_3"], patient.lab_scales["ca_15_3"])
        previous = facilities.setdefault(patient.facility_id, effect)
        assert effect == previous
    assert len(set(facilities.values())) > 1

    observed = cohort.to_observations_dataframe()
    assert observed["facility_id"].notna().all()
    assert observed["treatment_active"].dropna().eq("chemotherapy").all()
    assert observed["treatment_active"].notna().any()
    assert observed["imaging_probability"].between(0.0, 1.0).all()
    assert observed.loc[observed["imaging_performed"], "imaging_result"].notna().all()
    assert observed.loc[~observed["imaging_performed"], "imaging_result"].isna().all()
    imaged = observed[observed["imaging_performed"]]
    assert imaged["imaging_result"].notna().all()
    assert set(imaged["imaging_result"].unique()) == {True, False}
    assert imaged["imaging_result"].isin([True, False]).all()

    patients = cohort.to_patients_dataframe().set_index("patient_id")
    positives = imaged[imaged["imaging_result"]]
    assert all(bool(patients.loc[row.patient_id, "observed_recurrence_event"])
               and bool(patients.loc[row.patient_id, "true_recurrence_event"])
               for row in positives.itertuples())

    generator = get_generator(GeneratorType.G1_SMOOTH, seed=48102, population_config=profile)
    patient = generator.sample_baseline(1)
    missingness = profile["measurement_missingness"]
    assert generator.measurement_skip_probability(patient, "ca_15_3", 1.0) == pytest.approx(
        min(1.0, missingness["high_cost_skip_probability_per_cost_factor"]
            * patient.out_of_pocket_delay_factor)
    )
    assert generator.measurement_skip_probability(patient, "alt", 1.0) == pytest.approx(
        missingness["base_skip_probability_by_generator"][GeneratorType.G1_SMOOTH.value]
    )


def test_core_v3_versions_generator_assumptions_and_shared_facility_effects():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v3.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    assert profile["profile_id"] == "balanced_synthetic_core_v3"
    for key in (
        "facility_lab_effects", "verification", "measurement_missingness",
        "baseline_symptom_probabilities", "out_of_pocket_delay_factor_range",
        "visit_interval_gamma", "generator_mechanics",
    ):
        assert key in profile
    assert "legacy generator code" in profile["generator_mechanics"]["provenance"]
    assert set(profile["generator_mechanics"]) >= {"g1", "g2", "g3", "provenance"}

    generator = get_generator(GeneratorType.G1_SMOOTH, seed=48105, population_config=profile)
    patients = [generator.sample_baseline(i) for i in range(1, 100)]
    effects_by_facility = {}
    for patient in patients:
        effect = (patient.lab_offsets["ca_15_3"], patient.lab_scales["ca_15_3"])
        assert effects_by_facility.setdefault(patient.facility_id, effect) == effect
        assert profile["out_of_pocket_delay_factor_range"][0] <= patient.out_of_pocket_delay_factor
        assert patient.out_of_pocket_delay_factor <= profile["out_of_pocket_delay_factor_range"][1]
    assert len(effects_by_facility) > 1


def test_core_v3_rejects_incomplete_generator_mechanics():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v3.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    del profile["generator_mechanics"]["g2"]["ca153_per_burden"]
    with pytest.raises(ValueError, match="g2.ca153_per_burden"):
        get_generator(GeneratorType.G2_BURST, seed=42, population_config=profile)


def test_core_v4_requires_explicit_clearance_and_shot_noise_parameters():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v4.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    assert profile["profile_id"] == "balanced_synthetic_core_v4"
    assert "not calibrated for clinical prediction" in profile["interpretation"]
    assert "ca153_per_burden" not in profile["generator_mechanics"]["g1"]["marker_coupling"]
    assert "burst_count_exclusive_range" not in profile["generator_mechanics"]["g2"]
    get_generator(GeneratorType.G1_SMOOTH, seed=42, population_config=profile)
    del profile["generator_mechanics"]["g2"]["shot_noise"]["event_rate_per_day"]
    with pytest.raises(ValueError, match="event_rate_per_day"):
        get_generator(GeneratorType.G2_BURST, seed=42, population_config=profile)

    profile = json.loads(config_path.read_text(encoding="utf-8"))
    profile["generator_mechanics"]["g1"]["marker_kinetics"]["ca153_clearance_rate_per_day"] = 0.0
    with pytest.raises(ValueError, match="ca153_clearance_rate_per_day"):
        get_generator(GeneratorType.G1_SMOOTH, seed=42, population_config=profile)


def test_core_v4_g1_marker_state_is_independent_of_observation_visit_density():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v4.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    first = get_generator(GeneratorType.G1_SMOOTH, seed=9001, population_config=profile)
    second = get_generator(GeneratorType.G1_SMOOTH, seed=9001, population_config=profile)
    patient_a = first.sample_baseline(1)
    patient_b = second.sample_baseline(1)
    for patient in (patient_a, patient_b):
        patient.true_recurrence_event = True
        patient.true_recurrence_day = 500.0
        patient.true_recurrence_site = "liver"
    days_sparse = [0.0, 90.0, 180.0, 365.0, 540.0, 730.0]
    days_dense = sorted(set(days_sparse + [45.0, 135.0, 270.0, 450.0, 650.0]))
    _values_a, _masks_a, latent_a = first.simulate_longitudinal_trajectory(patient_a, days_sparse)
    _values_b, _masks_b, latent_b = second.simulate_longitudinal_trajectory(patient_b, days_dense)
    dense_at = {state.day: state for state in latent_b}
    for state in latent_a:
        assert state.m_ca153 == pytest.approx(dense_at[state.day].m_ca153, abs=1e-10)
        assert state.m_cea == pytest.approx(dense_at[state.day].m_cea, abs=1e-10)


def test_core_v4_g2_uses_stable_patient_scoped_shot_noise_and_visit_invariance():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v4.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    first = get_generator(GeneratorType.G2_BURST, seed=9002, population_config=profile)
    second = get_generator(GeneratorType.G2_BURST, seed=9002, population_config=profile)
    patient_a = first.sample_baseline(1)
    patient_b = second.sample_baseline(1)
    for patient in (patient_a, patient_b):
        patient.true_recurrence_event = True
        patient.true_recurrence_day = 700.0
        patient.true_recurrence_site = "liver"
    days_sparse = [0.0, 90.0, 180.0, 365.0, 540.0, 730.0]
    days_dense = sorted(set(days_sparse + [45.0, 135.0, 270.0, 450.0, 650.0]))
    _values_a, _masks_a, latent_a = first.simulate_longitudinal_trajectory(patient_a, days_sparse)
    _values_b, _masks_b, latent_b = second.simulate_longitudinal_trajectory(patient_b, days_dense)
    dense_at = {state.day: state for state in latent_b}
    for state in latent_a:
        assert state.m_ca153 == pytest.approx(dense_at[state.day].m_ca153, abs=1e-10)
        assert state.m_cea == pytest.approx(dense_at[state.day].m_cea, abs=1e-10)
        assert state.mechanism_event_count == dense_at[state.day].mechanism_event_count
    assert latent_a[-1].mechanism_event_count > 0
    assert np.all(np.diff([state.mechanism_event_count for state in latent_a]) >= 0)


def test_core_v4_g2_does_not_generate_events_without_recurrence():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v4.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    generator = get_generator(GeneratorType.G2_BURST, seed=9003, population_config=profile)
    patient = generator.sample_baseline(1)
    patient.true_recurrence_event = False
    patient.true_recurrence_day = None
    _values, _masks, latent = generator.simulate_longitudinal_trajectory(
        patient, [0.0, 90.0, 365.0, 730.0]
    )
    assert all(state.mechanism_event_count == 0 for state in latent)
    assert all(state.m_ca153 == 0.0 and state.m_cea == 0.0 for state in latent)


def test_g3_signal_saturates_after_recurrence_instead_of_exceeding_registered_mass():
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v3.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    generator = get_generator(GeneratorType.G3_NOISE, seed=48107, population_config=profile)
    patient = generator.sample_baseline(1)
    patient.true_recurrence_event = True
    patient.true_recurrence_day = 0.0
    patient.true_recurrence_site = "liver"

    _observations, _masks, latent = generator.simulate_longitudinal_trajectory(patient, [1000.0])

    mechanics = profile["generator_mechanics"]["g3"]
    assert latent[0].m_ca153 == pytest.approx(
        mechanics["burden_at_full_signal"] * mechanics["ca153_per_burden"]
    )


def test_legacy_g3_profile_keeps_frozen_replay_signal_semantics():
    generator = get_generator(GeneratorType.G3_NOISE, seed=48109)
    patient = generator.sample_baseline(1)
    patient.true_recurrence_event = True
    patient.true_recurrence_day = 0.0
    patient.true_recurrence_site = "liver"

    _observations, _masks, latent = generator.simulate_longitudinal_trajectory(patient, [1000.0])

    # This assertion preserves historical-profile replay only; it does not endorse the extrapolation.
    assert latent[0].m_ca153 > 50.0 * 3.0


@pytest.mark.parametrize("generator_type", [GeneratorType.G2_BURST, GeneratorType.G3_NOISE])
def test_core_v3_g2_g3_apply_registered_facility_scale(generator_type):
    config_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_core_v3.json"
    profile = json.loads(config_path.read_text(encoding="utf-8"))
    first_generator = get_generator(generator_type, seed=48108, population_config=profile)
    second_generator = get_generator(generator_type, seed=48108, population_config=profile)
    first_patient = first_generator.sample_baseline(1)
    second_patient = second_generator.sample_baseline(1)
    second_patient.lab_scales["alt"] = first_patient.lab_scales["alt"] * 2.0

    first_values, _, _ = first_generator.simulate_longitudinal_trajectory(first_patient, [0.0])
    second_values, _, _ = second_generator.simulate_longitudinal_trajectory(second_patient, [0.0])

    assert first_values[0]["alt"] != pytest.approx(second_values[0]["alt"])


def test_positive_imaging_below_visibility_threshold_is_not_confirmed_recurrence():
    profile_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_k3_v2.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    generator = get_generator(GeneratorType.G1_SMOOTH, seed=48103, population_config=profile)
    patient = generator.sample_baseline(1)
    patient.true_recurrence_event = True
    patient.true_recurrence_day = 100.0
    patient.true_recurrence_site = "bone"
    patient.observed_recurrence_event = False
    patient.observed_recurrence_day = None

    class AlwaysZeroRng:
        @staticmethod
        def random() -> float:
            return 0.0

    generator.rng = AlwaysZeroRng()
    state = type("State", (), {
        "b_loc": 0.0,
        "b_bone": 0.0,
        "b_liver": 0.0,
        "b_lung": 0.0,
        "b_brain": 0.0,
    })()
    performed, result, _probability = generator.evaluate_verification_mechanism(
        patient, 10.0, {}, {}, state
    )
    assert performed and result is True
    assert patient.observed_recurrence_event is False
    assert patient.observed_recurrence_day is None


def test_surveillance_visits_stop_after_confirmed_recurrence_transition():
    profile_path = Path(__file__).parents[1] / "vigil_sim" / "config" / "synthetic_population_k3_v2.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    generator = get_generator(GeneratorType.G1_SMOOTH, seed=48104, population_config=profile)

    def confirm_when_recurrence_has_started(patient, day, _symptoms, _analytes, _state):
        if (
            patient.true_recurrence_event
            and patient.true_recurrence_day is not None
            and day >= patient.true_recurrence_day
            and not patient.observed_recurrence_event
        ):
            patient.observed_recurrence_event = True
            patient.observed_recurrence_day = day
            patient.observed_recurrence_site = patient.true_recurrence_site
        return True, True, 1.0

    generator.evaluate_verification_mechanism = confirm_when_recurrence_has_started
    cohort = generator.generate_cohort(num_patients=80, duration_days=730.0)
    observations = cohort.to_observations_dataframe()
    patients = cohort.to_patients_dataframe().set_index("patient_id")
    diagnosed = patients[patients["observed_recurrence_event"]]
    assert len(diagnosed) > 0
    for patient_id, patient in diagnosed.iterrows():
        observed_days = observations.loc[
            observations["patient_id"] == patient_id, "day"
        ]
        assert observed_days.max() <= patient["observed_recurrence_day"] + 90.0


def test_latent_states_export_for_recovery_studies():
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=42)
    cohort = gen.generate_cohort(num_patients=10, duration_days=365.0)
    latent_df = cohort.to_latent_states_dataframe()

    assert not latent_df.empty
    expected_cols = [
        "patient_id",
        "day",
        "b_loc",
        "b_bone",
        "b_liver",
        "b_lung",
        "b_brain",
        "total_burden",
        "m_ca153",
        "m_cea",
        "o_liver",
        "o_bone",
        "o_renal",
    ]
    for col in expected_cols:
        assert col in latent_df.columns
        assert not latent_df[col].isna().any()


def test_unleaked_training_examples_contract():
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=42)
    cohort = gen.generate_cohort(num_patients=25, duration_days=730.0)
    X, y = cohort.get_unleaked_training_examples(
        horizon_days=180.0, use_observed_labels=True
    )

    assert len(X) == len(y)
    assert set(y.dropna().unique()).issubset({0, 1})

    # Strict anti-leakage checks on feature columns
    forbidden_tokens = [
        "recurrence",
        "event",
        "is_anomaly",
        "anomaly",
        "label",
        "outcome",
        "target",
    ]
    for col in X.columns:
        col_lower = col.lower()
        for tok in forbidden_tokens:
            assert tok not in col_lower, f"Leaky token '{tok}' found in feature column '{col}'"

    # Missing measurements stay missing; the helper must not impute or expose
    # simulator-side values for tests that were not observed.
    assert X.filter(regex=r"^lab_.*_observed$").isin([0.0, 1.0]).all().all()
    assert X.filter(regex=r"^lab_.*_observed$").shape[1] > 0
    assert X.filter(regex=r"^lab_(?!.*_observed$)").isna().any().any()


def test_unobserved_simulator_value_cannot_change_training_features():
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=81).generate_cohort(
        num_patients=20, duration_days=365.0
    )
    observation = next(
        obs
        for obs in cohort.observations
        if any(not measured for measured in obs.observed_mask.values())
    )
    analyte = next(
        key for key, measured in observation.observed_mask.items() if not measured
    )
    before_X, before_y = cohort.get_unleaked_training_examples(use_observed_labels=True)
    row = before_X.index[before_X["patient_id"] == observation.patient_id]
    row = row[before_X.loc[row, "day"] == observation.day][0]
    observation.analytes[analyte] += 1_000_000.0
    after_X, after_y = cohort.get_unleaked_training_examples(use_observed_labels=True)
    pd.testing.assert_series_equal(before_X.loc[row], after_X.loc[row])
    assert before_y.loc[row] == after_y.loc[row]


def test_training_labels_are_unknown_when_loss_to_follow_up_precedes_horizon():
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=82).generate_cohort(
        num_patients=10, duration_days=365.0
    )
    patient = cohort.patients[0]
    first_observation = min(
        (obs for obs in cohort.observations if obs.patient_id == patient.patient_id),
        key=lambda obs: obs.day,
    )
    patient.observed_recurrence_event = False
    patient.observed_recurrence_day = None
    patient.competing_event = "lost_to_follow_up"
    patient.competing_event_day = first_observation.day + 10.0
    patient.administrative_censor_day = first_observation.day + 365.0

    X, y, times, event_codes = cohort.get_survival_training_examples(
        horizon_days=180.0, use_observed_labels=True
    )
    assert y.name == "observed_diagnosis_within_180d"
    assert y.attrs["target_estimand"] == "observed_diagnosis"
    assert y.attrs["horizon_days"] == 180.0
    assert y.attrs["synthetic_only"] is True
    row = X.index[(X["patient_id"] == patient.patient_id) & (X["day"] == first_observation.day)][0]
    assert np.isnan(y.iloc[row])
    assert times[row] == pytest.approx(10.0)
    assert event_codes[row] == 0


def test_oracle_training_labels_censor_recurrence_after_loss_to_follow_up():
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=83).generate_cohort(
        num_patients=10, duration_days=365.0
    )
    patient = cohort.patients[0]
    first_observation = min(
        (obs for obs in cohort.observations if obs.patient_id == patient.patient_id),
        key=lambda obs: obs.day,
    )
    patient.true_recurrence_event = True
    patient.true_recurrence_day = first_observation.day + 100.0
    patient.competing_event = "lost_to_follow_up"
    patient.competing_event_day = first_observation.day + 10.0
    patient.administrative_censor_day = first_observation.day + 365.0

    X, y, times, event_codes = cohort.get_survival_training_examples(
        horizon_days=180.0, use_observed_labels=False
    )
    assert y.name == "oracle_true_recurrence_within_180d"
    assert y.attrs["target_estimand"] == "oracle_true_recurrence"
    assert y.attrs["horizon_days"] == 180.0
    assert y.attrs["synthetic_only"] is True
    row = X.index[(X["patient_id"] == patient.patient_id) & (X["day"] == first_observation.day)][0]
    assert np.isnan(y.iloc[row])
    assert times[row] == pytest.approx(10.0)
    assert event_codes[row] == 0


def test_training_helper_requires_an_explicit_observed_or_oracle_estimand():
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=84).generate_cohort(
        num_patients=4, duration_days=180.0
    )
    with pytest.raises(ValueError, match="must be explicitly set"):
        cohort.get_unleaked_training_examples()
    with pytest.raises(ValueError, match="must be explicitly set"):
        cohort.get_survival_training_examples()
