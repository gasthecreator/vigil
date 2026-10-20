"""
Tests for vigil_ml.features: Windowed feature extraction and longitudinal pipelining.
"""

import numpy as np
import pandas as pd
import pytest
from vigil_ml.features import WindowedFeatureExtractor, build_landmark_features


def test_feature_extractor_no_future_leakage():
    """
    Verifies that feature extraction at day t strictly excludes any observations where day > t.
    """
    extractor = WindowedFeatureExtractor()
    patient_row = {"patient_id": "PT-01", "age": 45.0, "subtype": "TNBC", "stage": "Stage II"}

    history = [
        {"day": 0.0, "analytes": {"ca_15_3": 18.0}, "symptoms": {"bone_pain": 0}},
        {"day": 90.0, "analytes": {"ca_15_3": 22.0}, "symptoms": {"bone_pain": 1}},
        {"day": 180.0, "analytes": {"ca_15_3": 38.0}, "symptoms": {"bone_pain": 2}},
        {"day": 270.0, "analytes": {"ca_15_3": 85.0}, "symptoms": {"bone_pain": 3}},  # Future visit
    ]

    feat_at_180 = extractor.extract_features_at_visit(patient_row, history, current_day=180.0)

    assert feat_at_180["eval_day"] == 180.0
    assert feat_at_180["history_length"] == 3
    # CA 15-3 current level must equal 38.0, NOT 85.0 (which occurred at day 270)
    assert feat_at_180["ca_15_3_curr"] == 38.0
    # Symptom bone pain must equal 2, NOT 3
    assert feat_at_180["symptom_bone_pain"] == 2.0


def test_unknown_receptor_statuses_remain_missing_and_unclassified():
    features = WindowedFeatureExtractor().extract_features_at_visit(
        {
            "patient_id": "PT-UNKNOWN",
            "er_status": np.nan,
            "pr_status": 0.0,
            "her2_status": np.nan,
            "subtype": "UNCLASSIFIED",
        },
        [{"day": 0.0, "analytes": {"ca_15_3": 20.0}, "symptoms": {}}],
        current_day=0.0,
    )
    assert np.isnan(features["is_er_pos"])
    assert features["er_status_missing"] == 1.0
    assert features["is_pr_pos"] == 0.0
    assert features["pr_status_missing"] == 0.0
    assert np.isnan(features["is_her2_pos"])
    assert features["her2_status_missing"] == 1.0
    assert features["subtype_unclassified"] == 1.0
    assert features["subtype_missing"] == 0.0


def test_simulator_truth_fields_cannot_change_observed_features_or_labels():
    from vigil_sim.generators import GeneratorType, get_generator

    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=302).generate_cohort(
        num_patients=20, duration_days=365.0
    )
    patients = cohort.to_patients_dataframe()
    observations = cohort.to_observations_dataframe()
    extractor = WindowedFeatureExtractor()
    baseline = extractor.transform_cohort(patients, observations, horizon_days=180.0)

    counterfactual = patients.copy()
    counterfactual["true_recurrence_event"] = ~counterfactual["true_recurrence_event"]
    counterfactual["true_recurrence_day"] = 0.0
    counterfactual["true_recurrence_site"] = "adversarially_changed"
    changed = extractor.transform_cohort(counterfactual, observations, horizon_days=180.0)

    pd.testing.assert_frame_equal(baseline[0], changed[0])
    pd.testing.assert_series_equal(baseline[1], changed[1])
    assert np.array_equal(baseline[2], changed[2])
    assert np.array_equal(baseline[3], changed[3])


def test_velocity_and_acceleration_computation():
    """Verifies that 90-day slope and acceleration match analytic mathematical formulas."""
    extractor = WindowedFeatureExtractor()
    patient_row = {"patient_id": "PT-02", "age": 52.0, "subtype": "HR+/HER2-", "stage": "Stage III"}

    # Constant velocity: dy/dt = 10 U/mL per 90 days = 0.1111 U/mL/day
    history = [
        {"day": 0.0, "analytes": {"ca_15_3": 20.0}, "symptoms": {}},
        {"day": 90.0, "analytes": {"ca_15_3": 30.0}, "symptoms": {}},
        {"day": 180.0, "analytes": {"ca_15_3": 40.0}, "symptoms": {}},
    ]

    feat = extractor.extract_features_at_visit(patient_row, history, current_day=180.0)

    # Slope between day 90 and 180: (40 - 30) / 90 = 1/9 = 0.1111...
    assert np.isclose(feat["ca_15_3_slope_90d"], 10.0 / 90.0, atol=1e-3)
    # Constant velocity -> acceleration = (40 - 30) - (30 - 20) = 0.0
    assert np.isclose(feat["ca_15_3_accel"], 0.0, atol=1e-4)


def test_horizon_label_is_unknown_when_followup_is_censored_early():
    patients = pd.DataFrame(
        [{
            "patient_id": "CENSORED",
            "observed_recurrence_event": False,
            "observed_recurrence_day": np.nan,
            "competing_event": "lost_to_follow_up",
            "competing_event_day": 200.0,
            "administrative_censor_day": 365.0,
        }]
    )
    observations = pd.DataFrame(
        {"patient_id": ["CENSORED", "CENSORED"], "day": [0.0, 100.0], "ca_15_3": [18.0, 20.0]}
    )
    _X, y, times, events = WindowedFeatureExtractor().transform_cohort(
        patients, observations, horizon_days=365.0
    )
    assert y.isna().all()
    assert np.array_equal(events, [0, 0])
    assert np.array_equal(times, [200.0, 100.0])


def test_competing_event_is_a_known_non_recurrence_outcome():
    patients = pd.DataFrame(
        [{
            "patient_id": "COMPETING",
            "observed_recurrence_event": False,
            "observed_recurrence_day": np.nan,
            "competing_event": "cardiovascular_event",
            "competing_event_day": 150.0,
            "administrative_censor_day": 365.0,
        }]
    )
    observations = pd.DataFrame(
        {"patient_id": ["COMPETING", "COMPETING"], "day": [0.0, 100.0], "ca_15_3": [18.0, 20.0]}
    )
    _X, y, times, events = WindowedFeatureExtractor().transform_cohort(
        patients, observations, horizon_days=365.0
    )
    assert y.name == "observed_diagnosis_within_365d"
    assert y.attrs["target_estimand"] == "observed_diagnosis"
    assert y.attrs["horizon_days"] == 365.0
    assert np.array_equal(y.to_numpy(), [0.0, 0.0])
    assert np.array_equal(events, [2, 2])
    assert np.array_equal(times, [150.0, 50.0])


def test_loss_to_follow_up_before_later_recurrence_censors_it():
    patients = pd.DataFrame([{
        "patient_id": "LOST",
        "observed_recurrence_event": True,
        "observed_recurrence_day": 300.0,
        "competing_event": "lost_to_follow_up",
        "competing_event_day": 150.0,
        "administrative_censor_day": 365.0,
    }])
    observations = pd.DataFrame({
        "patient_id": ["LOST", "LOST"], "day": [0.0, 100.0], "ca_15_3": [18.0, 20.0]
    })
    _X, y, times, events = WindowedFeatureExtractor().transform_cohort(
        patients, observations, horizon_days=365.0
    )
    assert y.isna().all()
    assert np.array_equal(events, [0, 0])
    assert np.array_equal(times, [150.0, 50.0])


def test_velocity_window_matches_its_90_day_feature_name():
    history = [
        {"day": 0.0, "analytes": {"ca_15_3": 10.0}, "symptoms": {}},
        {"day": 100.0, "analytes": {"ca_15_3": 30.0}, "symptoms": {}},
        {"day": 110.0, "analytes": {"ca_15_3": 40.0}, "symptoms": {}},
        {"day": 200.0, "analytes": {"ca_15_3": 50.0}, "symptoms": {}},
    ]
    features = WindowedFeatureExtractor().extract_features_at_visit(
        {"patient_id": "WINDOW"}, history, current_day=200.0
    )
    assert np.isclose(features["ca_15_3_slope_90d"], 10.0 / 90.0)


def test_acceleration_is_time_normalized_for_irregular_visits():
    history = [
        {"day": 0.0, "analytes": {"ca_15_3": 10.0}, "symptoms": {}},
        {"day": 20.0, "analytes": {"ca_15_3": 30.0}, "symptoms": {}},
        {"day": 100.0, "analytes": {"ca_15_3": 110.0}, "symptoms": {}},
    ]
    features = WindowedFeatureExtractor().extract_features_at_visit(
        {"patient_id": "IRREGULAR"}, history, current_day=100.0
    )
    assert np.isclose(features["ca_15_3_accel"], 0.0)


def test_same_day_observations_are_rejected_as_temporally_ambiguous():
    history = [
        {"day": 10.0, "analytes": {"ca_15_3": 20.0}, "symptoms": {}},
        {"day": 10.0, "analytes": {"ca_15_3": 80.0}, "symptoms": {}},
    ]
    with pytest.raises(ValueError, match="at most one observation per day"):
        WindowedFeatureExtractor().extract_features_at_visit(
            {"patient_id": "TIED"}, history, current_day=10.0
        )


def test_feature_labels_require_observed_outcome_metadata():
    observations = pd.DataFrame({"patient_id": ["NO-LABEL"], "day": [0.0], "ca_15_3": [18.0]})
    with pytest.raises(ValueError, match="required columns"):
        WindowedFeatureExtractor().transform_cohort(pd.DataFrame({"patient_id": ["NO-LABEL"]}), observations)
    with pytest.raises(ValueError, match="patients_df with observed outcome metadata"):
        build_landmark_features(observations)


def test_invalid_observation_outcome_boundaries_fail_closed():
    patients = pd.DataFrame([{
        "patient_id": "BAD-BOUNDARY",
        "observed_recurrence_event": False,
        "observed_recurrence_day": np.nan,
        "competing_event": None,
        "competing_event_day": np.nan,
        "administrative_censor_day": 5.0,
    }])
    observations = pd.DataFrame({"patient_id": ["BAD-BOUNDARY"], "day": [10.0], "ca_15_3": [20.0]})
    with pytest.raises(ValueError, match="extend beyond administrative follow-up"):
        WindowedFeatureExtractor().transform_cohort(patients, observations)


def test_observation_rows_must_map_to_one_patient_record():
    patients = pd.DataFrame([{
        "patient_id": "KNOWN",
        "observed_recurrence_event": False,
    }])
    observations = pd.DataFrame({"patient_id": ["UNKNOWN"], "day": [0.0], "ca_15_3": [18.0]})
    with pytest.raises(ValueError, match="unknown patient_ids"):
        WindowedFeatureExtractor().transform_cohort(patients, observations)


def test_zero_mean_biomarker_cv_is_unavailable_not_zero():
    history = [
        {"day": 0.0, "analytes": {"ca_15_3": 0.0}, "symptoms": {}},
        {"day": 10.0, "analytes": {"ca_15_3": 0.0}, "symptoms": {}},
    ]
    features = WindowedFeatureExtractor().extract_features_at_visit(
        {"patient_id": "ZERO"}, history, current_day=10.0
    )
    assert np.isnan(features["ca_15_3_cv"])
    assert features["ca_15_3_cv_available"] == 0.0


def test_zero_followup_at_landmark_is_not_invented_as_one_day():
    patients = pd.DataFrame([{
        "patient_id": "ZERO-FOLLOWUP",
        "observed_recurrence_event": False,
        "observed_recurrence_day": np.nan,
        "competing_event": None,
        "competing_event_day": np.nan,
        "administrative_censor_day": 0.0,
    }])
    observations = pd.DataFrame({"patient_id": ["ZERO-FOLLOWUP"], "day": [0.0], "ca_15_3": [18.0]})
    _features, labels, times, events = WindowedFeatureExtractor().transform_cohort(
        patients, observations, horizon_days=365.0
    )
    assert labels.isna().all()
    assert np.array_equal(times, [0.0])
    assert np.array_equal(events, [0])


def test_non_finite_future_observation_day_is_not_silently_filtered():
    history = [
        {"day": 0.0, "analytes": {"ca_15_3": 18.0}, "symptoms": {}},
        {"day": np.inf, "analytes": {"ca_15_3": 20.0}, "symptoms": {}},
    ]
    with pytest.raises(ValueError, match="observation days must be finite"):
        WindowedFeatureExtractor().extract_features_at_visit(
            {"patient_id": "NON-FINITE"}, history, current_day=0.0
        )


def test_missing_current_measurement_is_not_reported_as_observed_zero():
    history = [
        {"day": 0.0, "analytes": {"ca_15_3": 18.0}, "symptoms": {}},
        {"day": 10.0, "analytes": {"ca_15_3": np.nan}, "symptoms": {}},
    ]
    features = WindowedFeatureExtractor().extract_features_at_visit(
        {"patient_id": "MISSING"}, history, current_day=10.0
    )
    assert np.isnan(features["ca_15_3_curr"])
    assert features["ca_15_3_missing"] == 1.0


def test_recurrence_metadata_must_match_event_flag_and_followup():
    observations = pd.DataFrame({"patient_id": ["CONFLICT"], "day": [0.0], "ca_15_3": [18.0]})
    no_event_with_day = pd.DataFrame([{
        "patient_id": "CONFLICT",
        "observed_recurrence_event": False,
        "observed_recurrence_day": 10.0,
        "administrative_censor_day": 20.0,
    }])
    with pytest.raises(ValueError, match="without an observed event"):
        WindowedFeatureExtractor().transform_cohort(no_event_with_day, observations)

    event_after_followup = pd.DataFrame([{
        "patient_id": "CONFLICT",
        "observed_recurrence_event": True,
        "observed_recurrence_day": 30.0,
        "administrative_censor_day": 20.0,
    }])
    with pytest.raises(ValueError, match="after administrative follow-up"):
        WindowedFeatureExtractor().transform_cohort(event_after_followup, observations)
