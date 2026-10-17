"""Vigil ML Inference, Modeling Runtime, and Classical Science Core.

Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.2, WP2.3) and docs/ML_PROGRAM.md §5, §9.
"""

from vigil_ml.active_sensing_k6 import (
    ActiveSensingEngineK6,
    ActiveSensingRecommendation,
    TestPanelTier,
)
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
from vigil_ml.deep_zoo_k4 import ContinuousTimeTransformer, DeepZooK4, GRUDModel, NeuralCDEModel
from vigil_ml.export import export_to_onnx, export_to_safetensors, verify_onnx_parity
from vigil_ml.features import TRACKED_ANALYTES, WindowedFeatureExtractor
from vigil_ml.harmonisation_k5 import HierarchicalLabHarmoniserK5, LabHarmonisationProfile
from vigil_ml.joint_model import (
    BayesianJointModelK3,
    ConvergenceDiagnostics,
    FastLandmarkJointModel,
    PosteriorPredictiveResult,
)
from vigil_ml.k2 import SequentialDetector
from vigil_ml.k8 import AdaptiveConformal, ConformalRiskController, OODGate
from vigil_ml.kinetic_k1 import HybridKineticModelK1, UnscentedKalmanFilterK1
from vigil_ml.m3 import adjudicate, rcv
from vigil_ml.m5 import generate_worked_journey, render_clinician_note, verify_narrative
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
    "ConvergenceDiagnostics",
    "PosteriorPredictiveResult",
    # M1 Organ susceptibility
    "TARGET_ORGANS",
    "BaselineOrganSusceptibilityModelM1",
    "OrganSusceptibilityPrediction",
    # K1 Kinetic SDE/ODE
    "HybridKineticModelK1",
    "UnscentedKalmanFilterK1",
    # K2 Sequential detection
    "SequentialDetector",
    "SequentialEProcessK2",
    "AlertTier",
    "SequentialAlertResult",
    "SequentialDetectorBenchmark",
    # K4 Deep Zoo
    "DeepZooK4",
    "GRUDModel",
    "ContinuousTimeTransformer",
    "NeuralCDEModel",
    # K5 Harmonisation
    "HierarchicalLabHarmoniserK5",
    "LabHarmonisationProfile",
    # K6 Active Sensing
    "ActiveSensingEngineK6",
    "TestPanelTier",
    "ActiveSensingRecommendation",
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
    # Export & Runtime
    "VigilProductionRuntime",
    "export_to_onnx",
    "export_to_safetensors",
    "verify_onnx_parity",
]

__version__ = "0.1.0-alpha"
