"""
packages/vigil-ml/vigil_ml/harmonisation_k5.py

LEGACY (superseded by `vigil_ml/k5.py`, ADR-0024). Kept only because an older test and the public import
surface use it. Its offsets shrink a laboratory's *mean value*, which also reflects case mix, and it has no
validation: its former study was retracted (reports/ml/RETRACTED/README.md). Do not use it in new code.

K5 — Hierarchical Pooling and Laboratory Harmonisation (legacy design).
Problem H-G: Multi-lab, multi-assay heterogeneity where analyzer shifts mimic recurrence.

Components:
1. Hierarchical Bayesian partial pooling for lab-specific analyte baselines and scale factors.
2. Online Analytical Changepoint Detector: CUSUM on residuals across concurrent patients at the same lab
   to distinguish systemic analytical shifts from individual patient recurrences.
3. Out-of-Distribution new-site adaptation (M12 foundation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np


@dataclass
class LabHarmonisationProfile:
    lab_id: str
    analyte_offsets: Dict[str, float]
    analyte_scales: Dict[str, float]
    sample_count: int
    is_outlier_lab: bool = False


class HierarchicalLabHarmoniserK5:
    """
    Hierarchical partial pooling across clinical testing sites.
    Shares strength globally while estimating empirical Bayes site-specific offsets.
    """

    def __init__(self, shrinkage_strength: float = 15.0):
        self.shrinkage_strength = shrinkage_strength
        # Global reference population analyte medians (U/mL, IU/L, etc.)
        self.global_priors = {
            "ca15_3": 18.0,
            "cea": 2.2,
            "alt": 22.0,
            "ast": 24.0,
            "alp": 65.0,
            "creatinine": 0.85,
            "bilirubin": 0.60,
        }
        self.site_profiles: Dict[str, LabHarmonisationProfile] = {}
        # Residual tracking buffer for changepoint detection per lab
        self.lab_residual_buffers: Dict[str, List[float]] = {}
        self.lab_cusum_state: Dict[str, float] = {}

    def fit_sites(self, site_data: Dict[str, List[Dict[str, float]]]) -> "HierarchicalLabHarmoniserK5":
        """
        Fits empirical Bayes shrinkage parameters across participating laboratories.
        """
        for site_id, visits in site_data.items():
            n_obs = len(visits)
            offsets = {}
            scales = {}

            for analyte, global_val in self.global_priors.items():
                vals = [v[analyte] for v in visits if analyte in v]
                if vals:
                    site_mean = float(np.mean(vals))
                    # Empirical Bayes shrinkage: theta = w * site_mean + (1 - w) * global_prior
                    weight = n_obs / (n_obs + self.shrinkage_strength)
                    shrunk_mean = weight * site_mean + (1.0 - weight) * global_val
                    offsets[analyte] = shrunk_mean - global_val
                    scales[analyte] = float(np.std(vals)) / max(1.0, float(np.std(vals)))
                else:
                    offsets[analyte] = 0.0
                    scales[analyte] = 1.0

            self.site_profiles[site_id] = LabHarmonisationProfile(
                lab_id=site_id,
                analyte_offsets=offsets,
                analyte_scales=scales,
                sample_count=n_obs,
            )
            self.lab_residual_buffers[site_id] = []
            self.lab_cusum_state[site_id] = 0.0

        return self

    def harmonise_observation(self, site_id: str, analyte: str, raw_value: float) -> float:
        """
        Adjusts raw measured analyte value for site-specific offset and scale factor.
        """
        profile = self.site_profiles.get(site_id)
        if profile and analyte in profile.analyte_offsets:
            offset = profile.analyte_offsets[analyte]
            scale = profile.analyte_scales.get(analyte, 1.0)
            return (raw_value - offset) / max(0.2, scale)
        return raw_value

    def ingest_and_check_lab_shift(
        self, site_id: str, analyte: str, raw_value: float, expected_val: float
    ) -> Tuple[float, bool]:
        """
        Ingests a new test from a lab, checks if concurrent residuals indicate an analyzer shift.
        Returns: (harmonised_value, is_systemic_lab_shift)
        """
        harm_val = self.harmonise_observation(site_id, analyte, raw_value)
        residual = raw_value - expected_val

        if site_id not in self.lab_cusum_state:
            self.lab_cusum_state[site_id] = 0.0
            self.lab_residual_buffers[site_id] = []

        buf = self.lab_residual_buffers[site_id]
        buf.append(residual)
        if len(buf) > 50:
            buf.pop(0)

        # CUSUM on standardized lab residuals
        # Normal reference SD for CA 15-3 is ~2.5
        z = (residual) / 2.5
        c_state = max(0.0, self.lab_cusum_state[site_id] + (z - 0.5))
        self.lab_cusum_state[site_id] = c_state

        is_shift = c_state > 5.0
        return harm_val, is_shift

    def run_study_s5(self) -> Dict[str, Any]:
        """Retracted. The study body subtracted the injected offset by hand and returned a literal 34.2.

        See reports/ml/RETRACTED/README.md. The replacement is experiments/EXP-K5-001/run.py using vigil_ml.k5.
        """
        raise NotImplementedError(
            "Old S5 retracted (hand-subtracted offset, literal 34.2). Use experiments/EXP-K5-001/run.py."
        )
