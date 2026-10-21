"""Vigil Evaluation and Governance Backbone.

Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.1) and docs/ML_PROGRAM.md §5, §9.
"""

from vigil_eval.audit import FrozenTestAccessLogger, TestAccessRecord
from vigil_eval.bootstrap import (
    BootstrapMetricSummary,
    patient_cluster_bootstrap,
)
from vigil_eval.lead_time import (
    LeadTimeOverdetectionReport,
    evaluate_lead_time_and_overdetection,
)
from vigil_eval.leakage import (
    CanaryTestFailedError,
    LeakageError,
    OutcomeDerivedFeatureError,
    PatientSplitLeakageError,
    PreprocessingLeakageError,
    TemporalLeakageError,
    UnobservedValueLeakageError,
    check_outcome_derived_features,
    check_patient_split_leakage,
    check_scaler_fit_leakage,
    check_temporal_future_leakage,
    run_latent_column_canary,
    run_shuffled_label_canary,
    run_unobserved_value_canary,
)
from vigil_eval.metrics import (
    CalibrationReport,
    DecisionCurveResult,
    KaplanMeierEstimate,
    compute_calibration_curve,
    compute_ipcw_calibration_curve,
    compute_ipcw_weights,
    compute_kaplan_meier,
    ipcw_brier_score,
    ipcw_time_dependent_roc_auc,
    patient_landmark_ipcw_weights,
    survival_decision_curve_analysis,
)
from vigil_eval.regression_gate import (
    GateCheckResult,
    ModelRegressionGate,
    render_benchmark_table_markdown,
)
from vigil_eval.subgroups import (
    SubgroupEstimate,
    empirical_bayes_shrinkage,
    evaluate_subgroups_with_shrinkage,
)
from vigil_eval.verification_bias import (
    VerificationBiasReport,
    evaluate_complete_case,
    evaluate_ipw_verification,
    evaluate_latent_class_em,
)

__all__ = [
    # Leakage
    "LeakageError",
    "PatientSplitLeakageError",
    "TemporalLeakageError",
    "OutcomeDerivedFeatureError",
    "PreprocessingLeakageError",
    "CanaryTestFailedError",
    "UnobservedValueLeakageError",
    "check_patient_split_leakage",
    "check_temporal_future_leakage",
    "check_outcome_derived_features",
    "check_scaler_fit_leakage",
    "run_shuffled_label_canary",
    "run_unobserved_value_canary",
    "run_latent_column_canary",
    # Metrics
    "KaplanMeierEstimate",
    "compute_kaplan_meier",
    "compute_ipcw_weights",
    "ipcw_time_dependent_roc_auc",
    "ipcw_brier_score",
    "DecisionCurveResult",
    "survival_decision_curve_analysis",
    "CalibrationReport",
    "compute_calibration_curve",
    "compute_ipcw_calibration_curve",
    "patient_landmark_ipcw_weights",
    # Bootstrap
    "BootstrapMetricSummary",
    "patient_cluster_bootstrap",
    # Subgroups
    "SubgroupEstimate",
    "empirical_bayes_shrinkage",
    "evaluate_subgroups_with_shrinkage",
    # Verification Bias
    "VerificationBiasReport",
    "evaluate_complete_case",
    "evaluate_ipw_verification",
    "evaluate_latent_class_em",
    # Lead Time & Overdetection
    "LeadTimeOverdetectionReport",
    "evaluate_lead_time_and_overdetection",
    # Audit & Gates
    "FrozenTestAccessLogger",
    "TestAccessRecord",
    "ModelRegressionGate",
    "GateCheckResult",
    "render_benchmark_table_markdown",
]

__version__ = "0.1.0-alpha"
