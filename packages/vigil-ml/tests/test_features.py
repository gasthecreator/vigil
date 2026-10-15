"""
Tests for vigil_ml.features: Windowed feature extraction and longitudinal pipelining.
"""

import numpy as np
from vigil_ml.features import WindowedFeatureExtractor


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
