#!/usr/bin/env python3
"""
scripts/compare_leaky_vs_clean.py

Condition P8-A (VERDICT-P5C.md):
- Compares model performance under legacy leaky export vs. clean masked export.
- Identical models, identical seeds, identical cohort splits (G1, S1 V=10 setup).
- Calculates paired bootstrap confidence intervals (1,000 resamples) on deltas.
- Writes outputs strictly to reports/ml/LEAKAGE_DELTA.json.
"""

from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import torch

torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "vigil-sim"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-eval"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-ml"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-core"))

from vigil_eval.metrics import ipcw_time_dependent_roc_auc
from vigil_ml.baselines import (
    GradientBoostingBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)
from vigil_ml.features import WindowedFeatureExtractor
from vigil_ml.joint_model import FastLandmarkJointModel
from vigil_ml.k1 import HybridKineticModelK1, K1Observations
from vigil_sim.generators import GeneratorType, get_generator


def run_comparison(seed: int = 42, V: int = 10) -> Dict[str, Any]:
    print(f"Generating G1 cohorts (seed={seed}, N=1,000 train, N=1,000 test, V={V})...")
    g1_gen = get_generator(GeneratorType.G1_SMOOTH, seed=seed)
    train_cohort = g1_gen.generate_cohort(num_patients=1000, duration_days=730.0)
    test_cohort = g1_gen.generate_cohort(num_patients=1000, duration_days=730.0)

    train_pts_df = train_cohort.to_patients_dataframe()
    test_pts_df = test_cohort.to_patients_dataframe()

    # 1. Leaky dataframes (legacy_leaky=True)
    train_obs_leaky = train_cohort.to_observations_dataframe(legacy_leaky=True)
    test_obs_leaky = test_cohort.to_observations_dataframe(legacy_leaky=True)

    # 2. Clean dataframes (legacy_leaky=False)
    train_obs_clean = train_cohort.to_observations_dataframe(legacy_leaky=False)
    test_obs_clean = test_cohort.to_observations_dataframe(legacy_leaky=False)

    # Slice test observations to V visits per patient (same as S1)
    pt_counts_leaky = test_obs_leaky.groupby("patient_id").cumcount() + 1
    test_obs_leaky_sliced = test_obs_leaky[pt_counts_leaky <= V].copy()

    pt_counts_clean = test_obs_clean.groupby("patient_id").cumcount() + 1
    test_obs_clean_sliced = test_obs_clean[pt_counts_clean <= V].copy()

    extractor = WindowedFeatureExtractor()

    print("Transforming cohorts into feature matrices...")
    X_train_leaky, y_train_leaky, t_train_leaky, d_train_leaky = extractor.transform_cohort(
        patients_df=train_pts_df, observations_df=train_obs_leaky, horizon_days=365.0
    )
    X_test_leaky, y_test_leaky, t_test_leaky, d_test_leaky = extractor.transform_cohort(
        patients_df=test_pts_df, observations_df=test_obs_leaky_sliced, horizon_days=365.0
    )

    X_train_clean, y_train_clean, t_train_clean, d_train_clean = extractor.transform_cohort(
        patients_df=train_pts_df, observations_df=train_obs_clean, horizon_days=365.0
    )
    X_test_clean, y_test_clean, t_test_clean, d_test_clean = extractor.transform_cohort(
        patients_df=test_pts_df, observations_df=test_obs_clean_sliced, horizon_days=365.0
    )

    # Test event indicators and times are identical across leaky and clean because patients & event days are identical
    t_test = t_test_clean
    d_test = d_test_clean
    n_test = len(t_test)

    # Models under comparison
    model_configs = [
        ("B1_SingleThreshold", lambda: SingleThresholdBaseline()),
        ("B2_Velocity", lambda: VelocityBaseline()),
        ("B3_RegularizedHazard", lambda: RegularizedCoxHazardBaseline(C=0.5)),
        ("B4_GradientBoosting", lambda: GradientBoostingBaseline(max_depth=3, n_estimators=100)),
        ("K3_JointModel", lambda: FastLandmarkJointModel(horizon_days=365.0)),
        ("K1_Kinetic", lambda: HybridKineticModelK1(horizon_days=365.0)),
    ]

    results: Dict[str, Any] = {
        "metadata": {
            "study": "LEAKAGE_DELTA",
            "seed": seed,
            "visit_depth": V,
            "n_train": 1000,
            "n_test": 1000,
            "n_bootstrap_resamples": 1000,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        },
        "models": {},
    }

    # Function to get predictions for a model on a cohort
    def get_preds(m, name, X_tr, y_tr, X_te, obs_te):
        m.fit(X_tr, y_tr)
        if name == "K1_Kinetic":
            obs_list = []
            for _, row in X_te.iterrows():
                pid = row["patient_id"]
                eval_d = row.get("eval_day", 730.0)
                p_obs = obs_te[
                    (obs_te["patient_id"] == pid)
                    & (obs_te["day"] <= eval_d)
                    & (obs_te["ca_15_3"].notna())
                ]
                days = p_obs["day"].to_numpy(dtype=float)
                ca_vals = p_obs["ca_15_3"].to_numpy(dtype=float)
                obs_list.append(K1Observations(days=days, values={"ca153": ca_vals}))
            return m.predict_risk(obs_list)
        else:
            return m.predict_risk(X_te)

    # Pre-cluster by patient for patient-level bootstrap
    unique_patients = X_test_clean["patient_id"].unique()
    patient_to_indices = {
        pid: np.where(X_test_clean["patient_id"].values == pid)[0]
        for pid in unique_patients
    }
    n_unique = len(unique_patients)

    for name, factory in model_configs:
        print(f"Evaluating {name}...")
        # Fit on leaky
        m_leaky = factory()
        preds_leaky = get_preds(m_leaky, name, X_train_leaky, y_train_leaky, X_test_leaky, test_obs_leaky_sliced)

        # Fit on clean
        m_clean = factory()
        preds_clean = get_preds(m_clean, name, X_train_clean, y_train_clean, X_test_clean, test_obs_clean_sliced)

        auc_leaky = float(ipcw_time_dependent_roc_auc(preds_leaky, t_test, d_test, horizon_time=365.0))
        auc_clean = float(ipcw_time_dependent_roc_auc(preds_clean, t_test, d_test, horizon_time=365.0))
        delta_auc = auc_clean - auc_leaky

        # Paired patient-cluster bootstrap (1,000 resamples)
        rng_boot = np.random.default_rng(seed)
        boot_deltas = []
        for _ in range(1000):
            sampled_pts = rng_boot.choice(unique_patients, size=n_unique, replace=True)
            sampled_idx = np.concatenate([patient_to_indices[p] for p in sampled_pts])
            if len(np.unique(d_test[sampled_idx])) < 2:
                continue
            b_leaky = ipcw_time_dependent_roc_auc(
                preds_leaky[sampled_idx], t_test[sampled_idx], d_test[sampled_idx], horizon_time=365.0
            )
            b_clean = ipcw_time_dependent_roc_auc(
                preds_clean[sampled_idx], t_test[sampled_idx], d_test[sampled_idx], horizon_time=365.0
            )
            boot_deltas.append(b_clean - b_leaky)

        boot_deltas_arr = np.array(boot_deltas)
        ci_lower = float(np.percentile(boot_deltas_arr, 2.5))
        ci_upper = float(np.percentile(boot_deltas_arr, 97.5))

        direction = "decreased" if ci_upper < -0.0005 else ("increased" if ci_lower > 0.0005 else "stable")

        results["models"][name] = {
            "leaky_auc": round(auc_leaky, 4),
            "clean_auc": round(auc_clean, 4),
            "delta_auc": round(delta_auc, 4),
            "delta_ci95": [round(ci_lower, 4), round(ci_upper, 4)],
            "direction": direction,
            "interpretation": (
                f"Discrimination {direction} by {abs(delta_auc):.4f} AUC points [{ci_lower:.4f}, {ci_upper:.4f}] "
                f"when unobserved latent values are properly masked to NaN."
            ),
        }
        print(f"  {name}: Leaky={auc_leaky:.4f}, Clean={auc_clean:.4f}, Delta={delta_auc:+.4f} [{ci_lower:+.4f}, {ci_upper:+.4f}] ({direction})")

    out_file = ROOT / "reports" / "ml" / "LEAKAGE_DELTA.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Leakage comparison complete. Output saved to {out_file}")
    return results


if __name__ == "__main__":
    run_comparison()
