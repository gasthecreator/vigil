"""Helper utilities for persisting and restoring Model K2 SequentialDetector state."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
from vigil_ml.k2 import SequentialDetector


def detector_to_dict(detector: SequentialDetector) -> Dict[str, Any]:
    """Serialize SequentialDetector state to a JSON-compatible dictionary."""
    return {
        "config_id": detector.config_id,
        "config_source_sha256": detector.config_source_sha256,
        "effective_config_sha256": detector.effective_config_sha256,
        "alpha_pt": float(detector.alpha_pt),
        "sigma_log": float(detector.sigma_log),
        "burn_in": int(detector.burn_in),
        "log_threshold": float(detector.log_threshold),
        "history": [float(x) for x in detector.history],
        "days": [float(d) for d in detector.days],
        "log_e": float(detector.log_e),
        "alert": bool(detector.alert),
        "log_e_components": [float(c) for c in detector.log_e_components],
        "lambdas": [float(lam) for lam in detector.lambdas],
        "tier_score_thresholds": dict(detector.tier_score_thresholds),
    }


def detector_from_dict(data: Optional[Dict[str, Any]]) -> SequentialDetector:
    """Reconstruct SequentialDetector from serialized state."""
    if not data:
        return SequentialDetector()

    detector = SequentialDetector(
        alpha_pt=data.get("alpha_pt"),
        sigma_log=data.get("sigma_log"),
        burn_in=data.get("burn_in"),
        growth_grid=data.get("lambdas"),
    )
    if data.get("config_id") not in (None, detector.config_id):
        raise ValueError("Persisted K2 config id does not match its settings")
    if data.get("config_source_sha256") not in (None, detector.config_source_sha256):
        raise ValueError("Persisted K2 source config hash does not match the available config")
    if data.get("effective_config_sha256") not in (None, detector.effective_config_sha256):
        raise ValueError("Persisted K2 effective config hash does not match its settings")
    if data.get("tier_score_thresholds") not in (None, detector.tier_score_thresholds):
        raise ValueError("Persisted K2 tier thresholds do not match the available config")
    detector.history = [float(x) for x in data.get("history", [])]
    detector.days = [float(d) for d in data.get("days", [])]
    detector._log_e = float(data.get("log_e", 0.0))
    detector._alert = bool(data.get("alert", False))

    if "log_e_components" in data:
        comps = np.array(data["log_e_components"], dtype=float)
        if len(comps) == len(detector.lambdas):
            detector.log_e_components = comps

    return detector


def detector_states_by_analyte(
    current: Optional[Dict[str, Any]], analyte_code: str, detector: SequentialDetector
) -> Dict[str, Any]:
    """Store isolated K2 snapshots; legacy patient-wide state cannot be migrated safely."""
    states = (
        dict(current.get("analytes", {}))
        if current and current.get("schema_version") == 2
        and isinstance(current.get("analytes"), dict)
        else {}
    )
    states[analyte_code] = detector_to_dict(detector)
    return {"schema_version": 2, "analytes": states}
