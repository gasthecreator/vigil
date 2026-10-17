"""Backward compatibility re-exports for Sentinel prototype patient models."""

from vigil_api.models.v2 import (
    BaselineProfile,
    LabResult,
    Patient,
    RiskInference,
    generate_uuid,
)

__all__ = [
    "Patient",
    "BaselineProfile",
    "LabResult",
    "RiskInference",
    "generate_uuid",
]
