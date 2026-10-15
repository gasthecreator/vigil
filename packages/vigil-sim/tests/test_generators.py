"""
Tests for vigil_sim.generators: Mechanistic cohort generators G1, G2, G3 and anti-leakage invariants.
"""

import numpy as np
import pandas as pd
import pytest

from vigil_sim.generators import (
    BreastCancerSubtype,
    GeneratorType,
    PresentationStage,
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


def test_nigerian_presentation_priors():
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=999)
    cohort = gen.generate_cohort(num_patients=300, duration_days=365.0)
    pts_df = cohort.to_patients_dataframe()

    # 1. Age distribution: mean should be between 44 and 53
    mean_age = pts_df["age"].mean()
    assert 44.0 <= mean_age <= 53.0, f"Expected mean age ~48.5, got {mean_age}"

    # 2. Stage distribution: Stage III and IV should constitute > 65% of cohort (E7)
    stage_3_4_pct = (pts_df["stage"].isin(["Stage III", "Stage IV"])).mean()
    assert stage_3_4_pct >= 0.65, f"Expected >= 65% stage III/IV, got {stage_3_4_pct:.1%}"

    # 3. Subtype: TNBC should be substantial (30% - 50%)
    tnbc_pct = (pts_df["subtype"] == "TNBC").mean()
    assert 0.30 <= tnbc_pct <= 0.50, f"Expected 30-50% TNBC, got {tnbc_pct:.1%}"


def test_latent_states_export_for_recovery_studies():
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=42)
    cohort = gen.generate_cohort(num_patients=10, duration_days=365.0)
    latent_df = cohort.to_latent_states_dataframe()

    assert not latent_df.empty
    expected_cols = [
        "patient_id", "day", "b_loc", "b_bone", "b_liver", "b_lung", "b_brain",
        "total_burden", "m_ca153", "m_cea", "o_liver", "o_bone", "o_renal"
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
    forbidden_tokens = ["recurrence", "event", "is_anomaly", "anomaly", "label", "outcome", "target"]
    for col in X.columns:
        col_lower = col.lower()
        for tok in forbidden_tokens:
            assert tok not in col_lower, f"Leaky token '{tok}' found in feature column '{col}'"

    # Verify no NaNs in feature matrix
    assert not X.isna().any().any()
