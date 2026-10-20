"""Compatibility imports for the retired, invalid K2 prototype.

The former implementation clipped likelihood increments and cumulative scores,
mislabelled the result as an e-process, and reported an uncalibrated quantity as
confidence. Study S2 using that prototype is retracted. Executable entry points
fail closed; use ``vigil_ml.k2.SequentialDetector`` only as an unvalidated
research score.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AlertTier(str, Enum):
    """Legacy score labels retained for import compatibility only."""

    NONE = "none"
    WATCH = "watch"
    REVIEW = "review"
    URGENT = "urgent"


@dataclass
class SequentialAlertResult:
    """Legacy result shape retained for deserialization/import compatibility."""

    e_value: float
    cusum_stat: float
    shiryaev_stat: float
    tier: AlertTier
    is_alert: bool
    threshold_crossed: float
    confidence_level: float


class SequentialEProcessK2:
    """Retired invalid prototype; construction fails to prevent score use."""

    def __init__(self, *_: Any, **__: Any) -> None:
        raise RuntimeError(
            "SequentialEProcessK2 is retired: its clipped score and S2 validity claims were withdrawn"
        )


class SequentialDetectorBenchmark:
    """Retired benchmark; its synthetic stress output is not validity evidence."""

    def __init__(self, *_: Any, **__: Any) -> None:
        raise RuntimeError(
            "SequentialDetectorBenchmark is retired: the legacy K2 implementation is invalid"
        )
