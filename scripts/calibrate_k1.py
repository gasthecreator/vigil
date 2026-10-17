#!/usr/bin/env python3
"""
scripts/calibrate_k1.py

Committed calibration script for Model K1 (RR11, RR13, Condition B-3).
Fits the empirical residual standard deviations for Model K1's four latent kinetic parameters:
  0: doubling_time_days (days)
  1: shedding_ca153 (U/mL per unit tumor burden per day)
  2: clearance_ca153 (day^-1)
  3: onset_day (days post-surgery)
on an independent calibration cohort (seed 999, N=500) completely disjoint from test seeds.
Outputs results to packages/vigil-ml/vigil_ml/models/k1_calibration.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from vigil_ml.k1 import (
    AMORTIZED_CENTER,
    AMORTIZED_SCALE,
    SCHEDULE,
    _get_or_load_amortized_model,
    sample_prior,
    simulate_patient,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "packages" / "vigil-ml" / "vigil_ml" / "models" / "k1_calibration.json"


def calibrate_k1(seed: int = 999, n_patients: int = 500) -> dict:
    print(f"🔬 Calibrating Model K1 on independent cohort (seed={seed}, N={n_patients})...")
    rng = np.random.default_rng(seed)
    net = _get_or_load_amortized_model()
    net.eval()

    y_obs_list = []
    true_params_list = []

    for _ in range(n_patients):
        p = sample_prior(rng)
        obs = simulate_patient(p, SCHEDULE, rng)
        vals = obs.values["ca153"]
        y_obs_list.append(vals)
        true_params_list.append([
            p.doubling_time_days,
            p.shedding_ca153,
            p.clearance_ca153,
            p.onset_day,
        ])

    y_arr = np.array(y_obs_list, dtype=np.float32)
    true_arr = np.array(true_params_list, dtype=np.float64)

    # Standardized network input
    x_in = torch.tensor((y_arr - 18.0) / 5.0, dtype=torch.float32)

    with torch.no_grad():
        mu_norm, _ = net(x_in)
        pred_arr = mu_norm.numpy() * AMORTIZED_SCALE + AMORTIZED_CENTER

    residuals = pred_arr - true_arr
    sd_residuals = np.std(residuals, axis=0)

    # Elevation signal-to-noise floor: 3 * sigma_obs = 3 * 1.5 = 4.5 U/mL
    # Above this elevation, biomarker signal emerges from analytical noise.
    signal_snr_threshold = 4.5

    result = {
        "calibration_seed": seed,
        "n_patients": n_patients,
        "parameter_names": [
            "doubling_time_days",
            "shedding_ca153",
            "clearance_ca153",
            "onset_day",
        ],
        "parameter_descriptions": {
            "doubling_time_days": "Tumor doubling time in days",
            "shedding_ca153": "Biomarker shedding rate into circulation per unit tumor burden per day",
            "clearance_ca153": "First-order hepatic/renal clearance rate in 1/days",
            "onset_day": "Day of microscopic recurrence onset post-surgery",
        },
        "residual_sd": [round(float(s), 4) for s in sd_residuals],
        "signal_snr_threshold_u_ml": signal_snr_threshold,
        "clearance_prior_weight": 0.70,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2))
    print(f"✅ Calibrated residual standard deviations: {result['residual_sd']}")
    print(f"✅ Saved calibration metadata to {OUTPUT_PATH}")
    return result


def main() -> None:
    calibrate_k1()


if __name__ == "__main__":
    main()
