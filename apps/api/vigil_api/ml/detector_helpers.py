"""Helper utilities for persisting and restoring Model K2 SequentialDetector state."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
from vigil_ml.k2 import SequentialDetector


def detector_to_dict(detector: SequentialDetector) -> Dict[str, Any]:
    """Serialize SequentialDetector state to a JSON-compatible dictionary."""
    return {
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
    }


def detector_from_dict(data: Optional[Dict[str, Any]]) -> SequentialDetector:
    """Reconstruct SequentialDetector from serialized state."""
    if not data:
        return SequentialDetector(alpha_pt=0.05, sigma_log=0.12, burn_in=3)

    detector = SequentialDetector(
        alpha_pt=data.get("alpha_pt", 0.05),
        sigma_log=data.get("sigma_log", 0.12),
        burn_in=data.get("burn_in", 3),
    )
    detector.history = [float(x) for x in data.get("history", [])]
    detector.days = [float(d) for d in data.get("days", [])]
    detector._log_e = float(data.get("log_e", 0.0))
    detector._alert = bool(data.get("alert", False))

    if "log_e_components" in data:
        comps = np.array(data["log_e_components"], dtype=float)
        if len(comps) == len(detector.lambdas):
            detector.log_e_components = comps

    return detector
