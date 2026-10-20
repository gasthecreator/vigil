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


def test_feature_extractor_rejects_unregistered_analytes_and_duplicates():
    with pytest.raises(ValueError, match="unregistered analytes"):
        WindowedFeatureExtractor(tracked_analytes=["true_recurrence_event"])
    with pytest.raises(ValueError, match="must not contain duplicates"):
        WindowedFeatureExtractor(tracked_analytes=["ca_15_3", "ca_15_3"])


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


@pytest.mark.parametrize(
    ("stage", "expected"),
    [("Stage I", 0.0), ("IIA", 0.0), ("Stage III", 1.0), ("Stage IV", 1.0)],
)
def test_stage_feature_accepts_declared_groups_only(stage, expected):
    features = WindowedFeatureExtractor().extract_features_at_visit(
        {"stage": stage}, [{"day": 0.0}], current_day=0.0
    )
    assert features["is_stage_3_or_4"] == expected


def test_feature_extractor_rejects_unrecognized_stage_and_subtype():
    extractor = WindowedFeatureExtractor()
    history = [{"day": 0.0}]
    with pytest.raises(ValueError, match="unsupported stage value"):
        extractor.extract_features_at_visit(
            {"stage": "STAGE FIVE"}, history, current_day=0.0
        )
    with pytest.raises(ValueError, match="unsupported subtype value"):
        extractor.extract_features_at_visit(
            {"subtype": "SOMETHING ELSE"}, history, current_day=0.0
        )


def test_feature_extractor_rejects_nonfinite_demographics_and_nonbinary_receptors():
    extractor = WindowedFeatureExtractor()
    history = [{"day": 0.0}]
    with pytest.raises(ValueError, match="present numeric patient features must be finite"):
        extractor.extract_features_at_visit(
            {"age": np.inf}, history, current_day=0.0
        )
    with pytest.raises(ValueError, match="present receptor status features must be binary"):
        extractor.extract_features_at_visit(
            {"er_status": 2}, history, current_day=0.0
        )


def test_direct_feature_api_rejects_boolean_days_demographics_and_analytes():
    extractor = WindowedFeatureExtractor()
    clean_history = [{"day": 0.0, "analytes": {"ca_15_3": 20.0}}]
    with pytest.raises(ValueError, match="current_day must be numeric"):
        extractor.extract_features_at_visit({}, clean_history, current_day=True)
    with pytest.raises(ValueError, match="observation days must be numeric"):
        extractor.extract_features_at_visit(
            {}, [{"day": True, "analytes": {"ca_15_3": 20.0}}], current_day=1.0
        )
    with pytest.raises(ValueError, match="patient features must not be boolean"):
        extractor.extract_features_at_visit(
            {"age": True}, clean_history, current_day=0.0
        )
    with pytest.raises(ValueError, match="ca_15_3 measurements must be numeric"):
        extractor.extract_features_at_visit(
            {}, [{"day": 0.0, "analytes": {"ca_15_3": True}}], current_day=0.0
        )
    patients = pd.DataFrame(
        [{"patient_id": "BOOL-DAY", "observed_recurrence_event": False}]
    )
    observations = pd.DataFrame(
        {"patient_id": ["BOOL-DAY"], "day": [True], "ca_15_3": [20.0]}
    )
    with pytest.raises(ValueError, match="observation day must be numeric, not boolean"):
        extractor.transform_cohort(patients, observations, horizon_days=365.0)


def test_symptom_features_distinguish_absent_assessment_from_reported_zero():
    extractor = WindowedFeatureExtractor()
    history = [{"day": 0.0, "symptoms": None}]
    absent = extractor.extract_features_at_visit({}, history, current_day=0.0)
    assert absent["symptoms_missing"] == 1.0
    assert np.isnan(absent["symptom_bone_pain"])
    assert absent["symptom_bone_pain_missing"] == 1.0
    assert np.isnan(absent["max_symptom_grade"])

    reported = {
        name: 0
        for name in (
            "bone_pain",
            "jaundice",
            "ruq_pain",
            "cough_dyspnea",
            "headache_neuro",
            "fatigue_weight_loss",
        )
    }
    present = extractor.extract_features_at_visit(
        {}, [{"day": 0.0, "symptoms": reported}], current_day=0.0
    )
    assert present["symptoms_missing"] == 0.0
    assert present["symptom_bone_pain"] == 0.0
    assert present["symptom_bone_pain_missing"] == 0.0
    assert present["max_symptom_grade"] == 0.0

    partial = extractor.extract_features_at_visit(
        {}, [{"day": 0.0, "symptoms": {"bone_pain": 2}}], current_day=0.0
    )
    assert partial["symptoms_missing"] == 1.0
    assert partial["symptom_bone_pain"] == 2.0
    assert partial["symptom_bone_pain_missing"] == 0.0
    assert np.isnan(partial["symptom_ruq_pain"])
    assert partial["symptom_ruq_pain_missing"] == 1.0
    assert np.isnan(partial["max_symptom_grade"])
    assert partial["symptom_fatigue_weight_loss_missing"] == 1.0


@pytest.mark.parametrize(
    ("symptoms", "message"),
    [({"unregistered_symptom": 1}, "unsupported symptom names"),
     ({"bone_pain": 5}, "finite grade from 0 to 4"),
     ({"bone_pain": True}, "not boolean")],
)
def test_symptom_features_reject_unregistered_or_invalid_values(symptoms, message):
    with pytest.raises(ValueError, match=message):
        WindowedFeatureExtractor().extract_features_at_visit(
            {}, [{"day": 0.0, "symptoms": symptoms}], current_day=0.0
        )


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
    X, y, times, events = WindowedFeatureExtractor().transform_cohort(
        patients, observations, horizon_days=365.0
    )
    assert y.isna().all()
    assert X["symptoms_missing"].eq(1.0).all()
    assert X["symptom_bone_pain_missing"].eq(1.0).all()
    assert X["symptom_bone_pain"].isna().all()
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
        WindowedFeatureExtractor().transform_cohort(
            pd.DataFrame({"patient_id": ["NO-LABEL"]}), observations, horizon_days=365.0
        )
    with pytest.raises(ValueError, match="patients_df with observed outcome metadata"):
        build_landmark_features(observations, horizon_days=365.0)
    with pytest.raises(TypeError, match="horizon_days"):
        WindowedFeatureExtractor().transform_cohort(pd.DataFrame(), observations)
    with pytest.raises(TypeError, match="horizon_days"):
        build_landmark_features(observations)


@pytest.mark.parametrize("horizon_days", [True, np.bool_(False)])
def test_feature_labels_reject_boolean_horizon(horizon_days):
    with pytest.raises(ValueError, match="horizon_days.*boolean"):
        WindowedFeatureExtractor().transform_cohort(
            pd.DataFrame(), pd.DataFrame(columns=["patient_id", "day"]), horizon_days
        )


@pytest.mark.parametrize("horizon_days", [90.0, 180.0, 365.0])
def test_feature_label_contract_records_explicit_target_horizon(horizon_days):
    patients = pd.DataFrame(
        [{
            "patient_id": "HORIZON",
            "observed_recurrence_event": False,
            "observed_recurrence_day": np.nan,
            "administrative_censor_day": 730.0,
        }]
    )
    observations = pd.DataFrame(
        {"patient_id": ["HORIZON"], "day": [0.0], "ca_15_3": [18.0]}
    )
    _X, labels, _times, _events = WindowedFeatureExtractor().transform_cohort(
        patients, observations, horizon_days=horizon_days
    )
    assert labels.name == f"observed_diagnosis_within_{int(horizon_days)}d"
    assert labels.attrs["horizon_days"] == horizon_days


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
        WindowedFeatureExtractor().transform_cohort(patients, observations, horizon_days=365.0)


@pytest.mark.parametrize("competing_event", ["cardiovascular_typo", "", "0"])
def test_unknown_competing_event_types_cannot_create_negative_labels(competing_event):
    patients = pd.DataFrame([{
        "patient_id": "UNKNOWN-EVENT",
        "observed_recurrence_event": False,
        "observed_recurrence_day": np.nan,
        "competing_event": competing_event,
        "competing_event_day": 100.0,
        "administrative_censor_day": 365.0,
    }])
    observations = pd.DataFrame(
        {"patient_id": ["UNKNOWN-EVENT"], "day": [0.0], "ca_15_3": [20.0]}
    )
    with pytest.raises(ValueError, match="unsupported competing event type"):
        WindowedFeatureExtractor().transform_cohort(patients, observations, horizon_days=365.0)


@pytest.mark.parametrize(
    ("value", "mask", "expected"),
    [(np.nan, False, np.nan), (20.0, True, 20.0)],
)
def test_observation_mask_and_numeric_value_are_consistent(value, mask, expected):
    patients = pd.DataFrame([{
        "patient_id": "MASKED",
        "observed_recurrence_event": False,
        "observed_recurrence_day": np.nan,
        "administrative_censor_day": 365.0,
    }])
    observations = pd.DataFrame(
        {
            "patient_id": ["MASKED"],
            "day": [0.0],
            "ca_15_3": [value],
            "observed_ca_15_3": [mask],
        }
    )
    features, _labels, _times, _events = WindowedFeatureExtractor().transform_cohort(
        patients, observations, horizon_days=365.0
    )
    if np.isnan(expected):
        assert features["ca_15_3_curr"].isna().all()
        assert features["ca_15_3_missing"].eq(1.0).all()
    else:
        assert features["ca_15_3_curr"].eq(expected).all()
        assert features["ca_15_3_missing"].eq(0.0).all()


def test_finite_unobserved_lab_value_is_rejected():
    patients = pd.DataFrame([{
        "patient_id": "MASK-CONFLICT",
        "observed_recurrence_event": False,
        "observed_recurrence_day": np.nan,
    }])
    observations = pd.DataFrame(
        {
            "patient_id": ["MASK-CONFLICT"],
            "day": [0.0],
            "ca_15_3": [99.0],
            "observed_ca_15_3": [False],
        }
    )
    with pytest.raises(ValueError, match="disagrees with ca_15_3 value presence"):
        WindowedFeatureExtractor().transform_cohort(patients, observations, horizon_days=365.0)


def test_observation_mask_rejects_nonbinary_values():
    patients = pd.DataFrame([{
        "patient_id": "BAD-MASK",
        "observed_recurrence_event": False,
    }])
    observations = pd.DataFrame(
        {
            "patient_id": ["BAD-MASK"],
            "day": [0.0],
            "ca_15_3": [20.0],
            "observed_ca_15_3": [2],
        }
    )
    with pytest.raises(ValueError, match="must be a non-null boolean or 0/1"):
        WindowedFeatureExtractor().transform_cohort(patients, observations, horizon_days=365.0)


def test_observation_rows_must_map_to_one_patient_record():
    patients = pd.DataFrame([{
        "patient_id": "KNOWN",
        "observed_recurrence_event": False,
    }])
    observations = pd.DataFrame({"patient_id": ["UNKNOWN"], "day": [0.0], "ca_15_3": [18.0]})
    with pytest.raises(ValueError, match="unknown patient_ids"):
        WindowedFeatureExtractor().transform_cohort(patients, observations, horizon_days=365.0)


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
        WindowedFeatureExtractor().transform_cohort(
            no_event_with_day, observations, horizon_days=365.0
        )

    event_after_followup = pd.DataFrame([{
        "patient_id": "CONFLICT",
        "observed_recurrence_event": True,
        "observed_recurrence_day": 30.0,
        "administrative_censor_day": 20.0,
    }])
    with pytest.raises(ValueError, match="after administrative follow-up"):
        WindowedFeatureExtractor().transform_cohort(
            event_after_followup, observations, horizon_days=365.0
        )
