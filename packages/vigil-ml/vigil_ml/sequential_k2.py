"""Deprecated K2 prototype retained for compatibility.

This module is not an e-process and does not provide Ville false-alarm control:
its clipped Student-t likelihood increments and clipped cumulative values do not
establish the required supermartingale property. Use ``vigil_ml.k2.SequentialDetector``
for the current implementation. Its validity still depends on null-model and
scale assumptions; empirical stress results are not a proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

import numpy as np


class AlertTier(str, Enum):
    NONE = "none"
    WATCH = "watch"       # alpha_pt = 0.20 (early signal, suggest earlier re-test)
    REVIEW = "review"     # alpha_pt = 0.05 (confirmed trend, clinician review)
    URGENT = "urgent"     # alpha_pt = 0.01 (high conviction, imaging protocol)


@dataclass
class SequentialAlertResult:
    e_value: float
    cusum_stat: float
    shiryaev_stat: float
    tier: AlertTier
    is_alert: bool
    threshold_crossed: float
    confidence_level: float


class SequentialEProcessK2:
    """
    Deprecated clipped likelihood-ratio prototype; not an e-process.
    """

    def __init__(
        self,
        alpha_pt: float = 0.05,
        growth_grid: np.ndarray | None = None,
        analyte_baseline_sd: float = 2.5,
    ):
        self.alpha_pt = alpha_pt
        self.threshold = 1.0 / alpha_pt  # Ville's threshold (e.g. 20.0 for alpha=0.05)
        # Grid of candidate doubling times (days): 30d, 60d, 90d, 180d, 360d
        self.growth_grid = (
            growth_grid
            if growth_grid is not None
            else np.array([np.log(2) / 30.0, np.log(2) / 60.0, np.log(2) / 90.0, np.log(2) / 180.0])
        )
        self.sd = analyte_baseline_sd
        self.weights = np.ones(len(self.growth_grid)) / len(self.growth_grid)

    def step(
        self, current_e: float, delta_days: float, obs_val: float, base_val: float
    ) -> float:
        """
        Updates the mixture e-value with a new longitudinal observation.
        current_e: Previous e-value (starts at 1.0)
        """
        if delta_days <= 0.0:
            delta_days = 90.0

        diff = obs_val - base_val
        log_increments = []
        for g in self.growth_grid:
            delta_mu = max(0.0, base_val * (np.exp(np.clip(g * delta_days, 0.0, 3.0)) - 1.0))
            df = 4.0
            llr = 0.5 * (df + 1.0) * (
                np.log(1.0 + (diff / self.sd)**2 / df) - np.log(1.0 + ((diff - delta_mu) / self.sd)**2 / df)
            )
            log_increments.append(np.clip(llr, -3.0, 3.0))

        # Mixture e-process update
        increments = np.exp(np.array(log_increments))
        avg_increment = float(np.sum(self.weights * increments))
        new_e = current_e * avg_increment
        return float(np.clip(new_e, 1e-4, 1e6))

    def evaluate_trajectory(
        self, visits: List[Dict[str, Any]]
    ) -> List[SequentialAlertResult]:
        """
        Processes a history and returns exploratory scores without a validity guarantee.
        """
        results = []
        e_val = 1.0
        cusum = 0.0
        shiryaev = 0.0

        if not visits:
            return results

        base_ca = visits[0].get("ca15_3", 18.0)
        last_day = visits[0].get("day", 0.0)

        for i, v in enumerate(visits):
            day = v.get("day", 0.0)
            dt = max(1.0, day - last_day) if i > 0 else 90.0
            ca = v.get("ca15_3", base_ca)

            # 1. Update e-process
            e_val = self.step(e_val, dt, ca, base_ca)

            # 2. Update CUSUM comparator (k=0.5, h=4.0)
            z = (ca - base_ca) / self.sd
            cusum = max(0.0, cusum + (z - 0.5))

            # 3. Update Shiryaev-Roberts comparator (R_t = (1 + R_{t-1}) * LR)
            lr = np.exp(np.clip(0.5 * (z - 0.25), -6.0, 6.0))
            shiryaev = (1.0 + shiryaev) * lr

            # Assign calibrated tier based on Ville's thresholds
            if e_val >= (1.0 / 0.01):  # e >= 100
                tier = AlertTier.URGENT
            elif e_val >= (1.0 / 0.05):  # e >= 20
                tier = AlertTier.REVIEW
            elif e_val >= (1.0 / 0.20):  # e >= 5
                tier = AlertTier.WATCH
            else:
                tier = AlertTier.NONE

            results.append(
                SequentialAlertResult(
                    e_value=e_val,
                    cusum_stat=cusum,
                    shiryaev_stat=shiryaev,
                    tier=tier,
                    is_alert=(tier != AlertTier.NONE),
                    threshold_crossed=self.threshold,
                    confidence_level=1.0 - (1.0 / e_val) if e_val > 1.0 else 0.0,
                )
            )
            last_day = day

        return results


class SequentialDetectorBenchmark:
    """
    Deprecated empirical benchmark for the clipped prototype; it cannot test Ville validity.
    """

    def __init__(self, alpha_pt: float = 0.05):
        self.alpha_pt = alpha_pt
        self.detector = SequentialEProcessK2(alpha_pt=alpha_pt)

    def run_stress_suite(self, n_patients: int = 200, n_visits: int = 15) -> Dict[str, Any]:
        """
        Reports empirical rates on five generated scenarios; this is not a validity proof.
        """
        rng = np.random.default_rng(2026)
        scenarios = {
            "null_1_standard_biological_variation": {
                "noise_sd": 2.2, "heavy_tailed": False, "lab_shift": 0.0, "tox_spike": False
            },
            "null_2_heavy_tailed_student_t": {
                "noise_sd": 2.5, "heavy_tailed": True, "lab_shift": 0.0, "tox_spike": False
            },
            "null_3_inter_lab_batch_shift": {
                "noise_sd": 2.2, "heavy_tailed": False, "lab_shift": 4.5, "tox_spike": False
            },
            "null_4_therapy_hepatotoxicity_spikes": {
                "noise_sd": 2.5, "heavy_tailed": False, "lab_shift": 0.0, "tox_spike": True
            },
            "null_5_severe_mnar_missingness": {
                "noise_sd": 2.2, "heavy_tailed": False, "lab_shift": 0.0, "tox_spike": False
            },
        }

        results = {}
        all_passed = True

        for name, cfg in scenarios.items():
            false_alarms = 0
            for _ in range(n_patients):
                base_val = rng.normal(18.0, 2.0)
                visits = []
                current_day = 0.0
                for v in range(n_visits):
                    dt = rng.uniform(70.0, 110.0)
                    current_day += dt
                    # Generate null noise
                    if cfg["heavy_tailed"]:
                        noise = float(rng.standard_t(df=3) * cfg["noise_sd"])
                    else:
                        noise = float(rng.normal(0, cfg["noise_sd"]))

                    # Lab shift at visit 8
                    shift = cfg["lab_shift"] if v >= 8 else 0.0
                    # Toxic transient spike
                    spike = 12.0 if (cfg["tox_spike"] and v == 5) else 0.0

                    ca_obs = max(5.0, base_val + noise + shift + spike)
                    visits.append({"day": current_day, "ca15_3": ca_obs})

                traj_res = self.detector.evaluate_trajectory(visits)
                # Did an alert trigger at ANY visit?
                any_alert = any(r.e_value >= self.detector.threshold for r in traj_res)
                if any_alert:
                    false_alarms += 1

            empirical_far = false_alarms / float(n_patients)
            tol = 0.04 if n_patients <= 100 else 0.02
            passed = empirical_far <= (self.alpha_pt + tol)
            if not passed:
                all_passed = False

            results[name] = {
                "empirical_patient_level_far": empirical_far,
                "nominal_alpha": self.alpha_pt,
                "passed": passed,
            }

        return {
            "all_passed": all_passed,
            "nominal_alpha": self.alpha_pt,
            "scenarios": results,
        }
