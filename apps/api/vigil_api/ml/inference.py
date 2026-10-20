"""Quarantined legacy inference entry points.

Historical prototypes and derived outputs remain in storage for auditability,
but no recurrence-risk or organ-tropism prediction is exposed by this engine.
"""

from typing import Any


class VigilEngine:
    """Unified inference engine for multimodal oncology surveillance.

    Thread-safe compatibility object. Prediction methods fail closed because no
    validated model is available for these legacy output contracts.
    """

    _instance = None

    def __init__(self, artifacts_dir: str | None = None):
        self.artifacts_dir = artifacts_dir
        self.is_loaded = False
        self.is_quarantined = True
        self.model_version = "0.1.0-alpha-quarantined"
        self.status = "quarantined_no_validated_model"

    @classmethod
    def get_instance(cls, artifacts_dir: str | None = None) -> "VigilEngine":
        if cls._instance is None:
            cls._instance = cls(artifacts_dir=artifacts_dir)
        return cls._instance

    def predict_baseline_susceptibility(self, patient_data: dict[str, Any]) -> dict[str, float]:
        """Fail closed: the historical E12-derived M1 prior is retracted."""
        raise RuntimeError(
            "The legacy M1 organ-susceptibility prior is quarantined; no validated model is available."
        )

    def predict_risk(
        self,
        patient_id: str,
        new_lab_result: dict[str, Any],
        historical_labs: list[dict[str, Any]] | None = None,
        baseline_profile: dict[str, Any] | None = None,
    ) -> tuple[float, bool, str]:
        """Fail closed: this legacy heuristic is quarantined and cannot predict recurrence risk."""
        raise RuntimeError(
            "The legacy recurrence-risk heuristic is quarantined; no validated model is available."
        )


# Backwards compatibility alias for legacy prototype references
SentinelEngine = VigilEngine
