import pytest
from vigil_api.ml.detector_helpers import (
    detector_from_dict,
    detector_states_by_analyte,
    detector_to_dict,
)
from vigil_ml.k2 import SequentialDetector


def test_detector_state_round_trip_preserves_missing_visit_day_order():
    detector = SequentialDetector()
    detector.update(10.0, None)
    detector.update(20.0, 18.0)

    restored = detector_from_dict(detector_to_dict(detector))

    assert restored.days == [10.0, 20.0]
    assert restored.history == detector.history
    with pytest.raises(ValueError, match="nondecreasing"):
        restored.update(15.0, 19.0)
    restored.update(30.0, 19.0)
    assert restored.days == [10.0, 20.0, 30.0]


def test_patient_state_keeps_analyte_snapshots_separate_and_discards_legacy_mixture():
    ca = SequentialDetector()
    ca.update(10.0, 18.0)
    first = detector_states_by_analyte(None, "ca_15_3", ca)

    cea = SequentialDetector()
    cea.update(10.0, 3.0)
    second = detector_states_by_analyte(first, "cea", cea)
    assert set(second["analytes"]) == {"ca_15_3", "cea"}
    assert second["analytes"]["ca_15_3"]["history"] != second["analytes"]["cea"]["history"]

    reset = detector_states_by_analyte({"history": [99.0], "days": [1.0]}, "ca_15_3", ca)
    assert set(reset["analytes"]) == {"ca_15_3"}


def test_detector_restore_rejects_invalid_persisted_configuration():
    with pytest.raises(ValueError, match="sigma_log"):
        detector_from_dict({"sigma_log": 0.0})
