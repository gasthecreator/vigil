"""Cross-package contracts for simulator labels and shared feature extraction."""

import numpy as np
import pytest
from vigil_ml.features import WindowedFeatureExtractor
from vigil_sim.generators import GeneratorType, get_generator


@pytest.mark.parametrize("generator_type", list(GeneratorType))
def test_direct_simulator_labels_match_shared_extractor(generator_type):
    cohort = get_generator(generator_type, seed=2401).generate_cohort(
        num_patients=80, duration_days=730.0
    )
    direct_features, direct_labels, direct_times, direct_events = (
        cohort.get_survival_training_examples(
            horizon_days=180.0, use_observed_labels=True
        )
    )
    shared_features, shared_labels, shared_times, shared_events = (
        WindowedFeatureExtractor().transform_cohort(
            cohort.to_patients_dataframe(),
            cohort.to_observations_dataframe(),
            horizon_days=180.0,
            synthetic_only=True,
        )
    )

    assert direct_features["patient_id"].reset_index(drop=True).equals(
        shared_features["patient_id"].reset_index(drop=True)
    )
    assert np.array_equal(
        direct_labels.to_numpy(), shared_labels.to_numpy(), equal_nan=True
    )
    np.testing.assert_allclose(direct_times, shared_times)
    np.testing.assert_array_equal(direct_events, shared_events)
