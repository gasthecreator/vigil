"""Vigil ML Inference, Modeling Runtime, and Classical Science Core.

Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.2, WP2.3) and docs/ML_PROGRAM.md §5, §9.
"""

from vigil_ml.baselines import (
    BaseSurveillanceModel,
    GradientBoostingBaseline,
    PrevalenceBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)
from vigil_ml.conformal_k8 import (
    AbstentionReason,
    ConformalPredictionResult,
    ConformalRiskControllerK8,
    ProductionEnsembleK8,
)
from vigil_ml.export import export_to_onnx, export_to_safetensors, verify_onnx_parity
from vigil_ml.features import TRACKED_ANALYTES, WindowedFeatureExtractor
from vigil_ml.harmonisation_k5 import HierarchicalLabHarmoniserK5, LabHarmonisationProfile
from vigil_ml.joint_model import (
    BayesianJointModelK3,
    FastLandmarkJointModel,
    LandmarkLogisticResearchBaseline,
)
from vigil_ml.k1 import HybridKineticModelK1
from vigil_ml.k2 import SequentialDetector
from vigil_ml.k8 import AdaptiveConformal, ConformalRiskController, OODGate
from vigil_ml.m3 import adjudicate, rcv
from vigil_ml.m5 import (
    compute_flesch_kincaid_grade_level,
    generate_worked_journey,
    render_clinician_note,
    render_plain_language_explainer,
    verify_narrative,
)
from vigil_ml.organ_susceptibility import (
    TARGET_ORGANS,
    BaselineOrganSusceptibilityModelM1,
    OrganSusceptibilityPrediction,
)
from vigil_ml.runtime import VigilProductionRuntime
from vigil_ml.sequential_k2 import (
    AlertTier,
    SequentialAlertResult,
    SequentialDetectorBenchmark,
    SequentialEProcessK2,
)

__all__ = [
    # Feature engineering
    "TRACKED_ANALYTES",
    "WindowedFeatureExtractor",
    # Classical baselines
    "BaseSurveillanceModel",
    "PrevalenceBaseline",
    "SingleThresholdBaseline",
    "VelocityBaseline",
    "RegularizedCoxHazardBaseline",
    "GradientBoostingBaseline",
    # K3 Joint model
    "BayesianJointModelK3",
    "FastLandmarkJointModel",
    "LandmarkLogisticResearchBaseline",
    # M1 Organ susceptibility
    "TARGET_ORGANS",
    "BaselineOrganSusceptibilityModelM1",
    "OrganSusceptibilityPrediction",
    # K1 Kinetic SDE/ODE
    "HybridKineticModelK1",
    # K2 Sequential detection
    "SequentialDetector",
    "SequentialEProcessK2",
    "AlertTier",
    "SequentialAlertResult",
    "SequentialDetectorBenchmark",
    # K5 Harmonisation
    "HierarchicalLabHarmoniserK5",
    "LabHarmonisationProfile",
    # K8 Conformal & Ensemble
    "ConformalRiskController",
    "OODGate",
    "AdaptiveConformal",
    "ConformalRiskControllerK8",
    "ConformalPredictionResult",
    "ProductionEnsembleK8",
    "AbstentionReason",
    # M3 Plausibility Adjudicator
    "rcv",
    "adjudicate",
    # M5 Verified Narrative
    "render_clinician_note",
    "verify_narrative",
    "generate_worked_journey",
    "render_plain_language_explainer",
    "compute_flesch_kincaid_grade_level",
    # Export & Runtime
    "VigilProductionRuntime",
    "export_to_onnx",
    "export_to_safetensors",
    "verify_onnx_parity",
]

__version__ = "0.1.0-alpha"
