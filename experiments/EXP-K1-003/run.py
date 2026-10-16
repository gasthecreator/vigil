#!/usr/bin/env python3
"""Run script for EXP-K1-003: Prospective cumulative burden integration vs point hazard."""

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

    y, s_point, s_cum = [], [], []
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
        samples = ROUTES["amortized"](ob, rng, 100)

        # Baseline: instantaneous point hazard at horizon
        r_point = risk_from_posterior(samples, 730.0)

        # Intervention: cumulative burden integration over prospective window (365, 730]
        # For each sample, integrate expected excess burden:
        # onset_day = sample['onset_day'], growth_rate = sample['growth_rate']
        onsets = samples["onset_day"]
        doublings = samples["doubling_time_days"]
        rates = np.log(2.0) / np.maximum(doublings, 1.0)
        # Burden integral for t in [365, 730]
        cum_burdens = []
        for t_on, gr in zip(onsets, rates):
            if t_on >= 730.0:
                cum_burdens.append(0.0)
            else:
                t_start = max(365.0, float(t_on))
                # integral of exp(gr * (t - t_on)) from t_start to 730
                dt = 730.0 - t_start
                if gr > 1e-4:
                    integral = (np.exp(min(gr * dt, 15.0)) - 1.0) / gr
                else:
                    integral = dt
                cum_burdens.append(integral)

        mean_burden = float(np.mean(cum_burdens))
        # Map cumulative burden to calibrated prospective probability
        r_cum = float(1.0 - np.exp(-mean_burden / 500.0))

        s_point.append(r_point)
        s_cum.append(r_cum)
        y.append(int(rec and day is not None and 365 < day <= 730))

    auc_point = float(roc_auc_score(y, s_point))
    auc_cum = float(roc_auc_score(y, s_cum))
    brier_point = float(brier_score_loss(y, s_point))
    brier_cum = float(brier_score_loss(y, s_cum))

    delta_auc = auc_cum - auc_point
    results = {
        "experiment_id": config["experiment_id"],
        "num_evaluated": len(y),
        "num_events": sum(y),
        "baseline_auc": round(auc_point, 4),
        "intervention_auc": round(auc_cum, 4),
        "delta_auc": round(delta_auc, 4),
        "baseline_brier": round(brier_point, 4),
        "intervention_brier": round(brier_cum, 4),
        "hypothesis_confirmed": bool(delta_auc >= 0.02),
    }

    (DIR / "results.json").write_text(json.dumps(results, indent=2))
    print(
        f"EXP-K1-003 Complete: point AUC={auc_point:.4f}, cum AUC={auc_cum:.4f}, delta={delta_auc:.4f}"
    )

    report = f"""# EXP-K1-003 Report: Cumulative Burden Integration

- **Baseline ROC-AUC:** {results["baseline_auc"]:.4f}
- **Intervention ROC-AUC:** {results["intervention_auc"]:.4f}
- **Delta ROC-AUC:** {results["delta_auc"]:+.4f}
- **Baseline Brier Score:** {results["baseline_brier"]:.4f}
- **Intervention Brier Score:** {results["intervention_brier"]:.4f}
- **Hypothesis Verdict:** {"CONFIRMED" if results["hypothesis_confirmed"] else "REFUTED"}

### Findings
Prospective cumulative burden integration over the surveillance interval yielded an AUC of {results["intervention_auc"]:.4f} versus {results["baseline_auc"]:.4f} for point hazard, an incremental change of {results["delta_auc"]:+.4f}.
"""
    (DIR / "REPORT.md").write_text(report)


if __name__ == "__main__":
    main()
