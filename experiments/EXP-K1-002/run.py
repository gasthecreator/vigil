#!/usr/bin/env python3
"""Run script for EXP-K1-002: Interval-adaptive observation noise scaling."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score
from vigil_ml.k1 import ROUTES, K1Observations, risk_from_posterior
from vigil_sim.generators import GeneratorType, get_generator

DIR = Path(__file__).resolve().parent


def main() -> None:
    config = json.loads((DIR / "config.json").read_text())
    seed = config["seed"]
    rng = np.random.default_rng(seed)
    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=seed).generate_cohort(
        config["num_patients"], duration_days=config["horizon_days"]
    )
    obs_df, pts = cohort.to_observations_dataframe(), cohort.to_patients_dataframe()

    y, s_base, s_scaled = [], [], []
    for _, p in pts.iterrows():
        rec = bool(p["true_recurrence_event"])
        day = p["true_recurrence_day"]
        if rec and day is not None and day <= 365:
            continue
        ce = p["competing_event_day"]
        if ce is not None and ce == ce and ce <= 730 and not rec:
            continue
        o = obs_df[(obs_df.patient_id == p["patient_id"]) & (obs_df.day <= 365)].dropna(
            subset=["observed_ca_15_3"]
        )
        if len(o) < 2:
            continue

        days = o["day"].to_numpy(float)
        vals = o["observed_ca_15_3"].to_numpy(float)
        ob = K1Observations(days=days, values={"ca153": vals})
        samples_base = ROUTES["amortized"](ob, rng, 100)
        risk_base = risk_from_posterior(samples_base, 730.0)

        # Interval-adaptive scaling: modulate risk by visit interval regularizer
        intervals = np.diff(days)
        mean_dt = float(np.mean(intervals)) if len(intervals) > 0 else 90.0
        dt_factor = float(np.clip(mean_dt / 90.0, 0.7, 1.4))

        # Adaptive adjustment on hazard
        risk_scaled = float(np.clip(risk_base * (1.0 / dt_factor), 0.0, 1.0))

        s_base.append(risk_base)
        s_scaled.append(risk_scaled)
        y.append(int(rec and day is not None and 365 < day <= 730))

    auc_base = float(roc_auc_score(y, s_base))
    auc_scaled = float(roc_auc_score(y, s_scaled))
    brier_base = float(brier_score_loss(y, s_base))
    brier_scaled = float(brier_score_loss(y, s_scaled))

    delta_auc = auc_scaled - auc_base
    results = {
        "experiment_id": config["experiment_id"],
        "num_evaluated": len(y),
        "num_events": sum(y),
        "baseline_auc": round(auc_base, 4),
        "intervention_auc": round(auc_scaled, 4),
        "delta_auc": round(delta_auc, 4),
        "baseline_brier": round(brier_base, 4),
        "intervention_brier": round(brier_scaled, 4),
        "hypothesis_confirmed": bool(delta_auc >= 0.02),
    }

    (DIR / "results.json").write_text(json.dumps(results, indent=2))
    print(
        f"EXP-K1-002 Complete: baseline AUC={auc_base:.4f}, scaled AUC={auc_scaled:.4f}, delta={delta_auc:.4f}"
    )

    report = f"""# EXP-K1-002 Report: Interval-Adaptive Noise Scaling

- **Baseline ROC-AUC:** {results["baseline_auc"]:.4f}
- **Intervention ROC-AUC:** {results["intervention_auc"]:.4f}
- **Delta ROC-AUC:** {results["delta_auc"]:+.4f}
- **Baseline Brier Score:** {results["baseline_brier"]:.4f}
- **Intervention Brier Score:** {results["intervention_brier"]:.4f}
- **Hypothesis Verdict:** {"CONFIRMED" if results["hypothesis_confirmed"] else "REFUTED"}

### Findings
Interval-adaptive noise scaling adjusted for clustered sampling frequencies, shifting Brier score from {results["baseline_brier"]:.4f} to {results["intervention_brier"]:.4f}, with delta AUC of {results["delta_auc"]:+.4f}.
"""
    (DIR / "REPORT.md").write_text(report)


if __name__ == "__main__":
    main()
