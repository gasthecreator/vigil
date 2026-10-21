"""Quarantined legacy M1 organ susceptibility API.

The former implementation returned unsupported subtype priors and interval claims.
It remains importable for source compatibility, but cannot produce predictions.
See ADR-0051 and S-020.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd

TARGET_ORGANS = ["bone", "liver", "lung", "brain"]


@dataclass
class OrganSusceptibilityPrediction:
    """Compatibility type; no current M1 inference path returns this value."""

    probabilities: Dict[str, float]
    credible_intervals_95: Dict[str, Tuple[float, float]]
    evidence_badge: str
    primary_citation: str
    confidence_level: str


class BaselineOrganSusceptibilityModelM1:
    """Legacy import name whose prediction methods fail closed while M1 is quarantined."""

    def predict_susceptibility(
        self,
        subtype: str,
        stage: str = "Stage II",
        age: float = 48.0,
        has_hypertension: bool = False,
        renal_history: bool = False,
    ) -> OrganSusceptibilityPrediction:
        del subtype, stage, age, has_hypertension, renal_history
        raise RuntimeError(
            "M1 organ-susceptibility inference is quarantined; no supported model is available."
        )

    def predict_cohort_dataframe(self, patients_df: pd.DataFrame) -> pd.DataFrame:
        del patients_df
        raise RuntimeError(
            "M1 cohort inference is quarantined; no supported model is available."
        )
