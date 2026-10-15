"""Vigil Evaluation and Governance Backbone."""

from vigil_eval.leakage import (
    CanaryTestFailedError,
    LeakageError,
    OutcomeDerivedFeatureError,
    PatientSplitLeakageError,
    PreprocessingLeakageError,
    TemporalLeakageError,
    check_outcome_derived_features,
    check_patient_split_leakage,
    check_scaler_fit_leakage,
    check_temporal_future_leakage,
    run_shuffled_label_canary,
)

__all__ = [
    "LeakageError",
    "PatientSplitLeakageError",
    "TemporalLeakageError",
    "OutcomeDerivedFeatureError",
    "PreprocessingLeakageError",
    "CanaryTestFailedError",
    "check_patient_split_leakage",
    "check_temporal_future_leakage",
    "check_outcome_derived_features",
    "check_scaler_fit_leakage",
    "run_shuffled_label_canary",
]

__version__ = "0.1.0-alpha"
