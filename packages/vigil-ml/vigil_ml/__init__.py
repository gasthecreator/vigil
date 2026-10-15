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
from vigil_ml.features import TRACKED_ANALYTES, WindowedFeatureExtractor
from vigil_ml.joint_model import (
    BayesianJointModelK3,
    ConvergenceDiagnostics,
    FastLandmarkJointModel,
    PosteriorPredictiveResult,
)
from vigil_ml.organ_susceptibility import (
    TARGET_ORGANS,
    BaselineOrganSusceptibilityModelM1,
    OrganSusceptibilityPrediction,
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
]

__version__ = "0.1.0-alpha"
