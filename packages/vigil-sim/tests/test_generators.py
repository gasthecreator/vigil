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
    X, y = cohort.get_unleaked_training_examples(horizon_days=180.0)

    assert len(X) == len(y)
    assert set(y.unique()).issubset({0, 1})

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

    # Verify no NaNs in feature matrix
    assert not X.isna().any().any()
