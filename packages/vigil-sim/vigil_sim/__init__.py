"""Vigil Mechanistic Cohort Simulation Laboratory and Digital Twin.

Complies with docs/MASTER_PLAN.md §6.13 and docs/ML_PROGRAM.md §9.
"""

from vigil_sim.calibration import (
    CalibrationReport,
    evaluate_cohort_calibration,
    run_full_calibration_check,
)
from vigil_sim.generators import (
    BaseCohortGenerator,
    BreastCancerSubtype,
    BurstSheddingGenerator,
    CohortDataset,
    ContinuousSecretionGenerator,
    GeneratorType,
    HeavyTailedNoiseGenerator,
    LatentCompartmentState,
    LongitudinalObservation,
    PatientBaseline,
    PresentationStage,
    get_generator,
)

__version__ = "0.1.0-alpha"

__all__ = [
    "GeneratorType",
    "BreastCancerSubtype",
    "PresentationStage",
    "LatentCompartmentState",
    "PatientBaseline",
    "LongitudinalObservation",
    "CohortDataset",
    "BaseCohortGenerator",
    "ContinuousSecretionGenerator",
    "BurstSheddingGenerator",
    "HeavyTailedNoiseGenerator",
    "get_generator",
    "CalibrationReport",
    "evaluate_cohort_calibration",
    "run_full_calibration_check",
]
