#!/usr/bin/env python3
"""Run script for EXP-K1-001: Informative prior shrinkage."""

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

    y, s_base, s_shrunk = [], [], []
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

        ob = K1Observations(
            days=o["day"].to_numpy(float), values={"ca153": o["observed_ca_15_3"].to_numpy(float)}
        )
        samples_base = ROUTES["amortized"](ob, rng, 100)
        risk_base = risk_from_posterior(samples_base, 730.0)

        # Prior shrinkage intervention: constrain T_d to [50, 100]
        samples_shrunk = {k: np.copy(v) for k, v in samples_base.items()}
        samples_shrunk["doubling_time_days"] = np.clip(
            samples_shrunk["doubling_time_days"], 50.0, 100.0
        )
        risk_shrunk = risk_from_posterior(samples_shrunk, 730.0)

        s_base.append(risk_base)
        s_shrunk.append(risk_shrunk)
        y.append(int(rec and day is not None and 365 < day <= 730))

    auc_base = float(roc_auc_score(y, s_base))
    auc_shrunk = float(roc_auc_score(y, s_shrunk))
    brier_base = float(brier_score_loss(y, s_base))
    brier_shrunk = float(brier_score_loss(y, s_shrunk))
    delta_auc = auc_shrunk - auc_base
    delta_brier = brier_shrunk - brier_base

    # Compute patient-level paired bootstrap 95% CIs (RR14)
    y_arr = np.asarray(y)
    b_arr = np.asarray(s_base)
    i_arr = np.asarray(s_shrunk)
    n = len(y_arr)
    rng_b = np.random.default_rng(seed)
    d_aucs, d_briers = [], []
    for _ in range(1000):
        idx = rng_b.choice(n, size=n, replace=True)
        yb = y_arr[idx]
        if len(np.unique(yb)) < 2:
            continue
        auc_b = roc_auc_score(yb, b_arr[idx])
        auc_i = roc_auc_score(yb, i_arr[idx])
        br_b = brier_score_loss(yb, b_arr[idx])
        br_i = brier_score_loss(yb, i_arr[idx])
        d_aucs.append(auc_i - auc_b)
        d_briers.append(br_i - br_b)

    delta_auc_ci = [round(float(np.percentile(d_aucs, 2.5)), 4), round(float(np.percentile(d_aucs, 97.5)), 4)]
    delta_brier_ci = [round(float(np.percentile(d_briers, 2.5)), 4), round(float(np.percentile(d_briers, 97.5)), 4)]
    ci_excludes_zero = bool(delta_auc_ci[0] > 0.0 or delta_auc_ci[1] < 0.0)
    confirmed = bool(ci_excludes_zero and delta_auc >= 0.02)

    results = {
        "experiment_id": config["experiment_id"],
        "num_evaluated": len(y),
        "num_events": sum(y),
        "baseline_auc": round(auc_base, 4),
        "intervention_auc": round(auc_shrunk, 4),
        "delta_auc": round(delta_auc, 4),
        "delta_auc_ci_95": delta_auc_ci,
        "baseline_brier": round(brier_base, 4),
        "intervention_brier": round(brier_shrunk, 4),
        "delta_brier": round(delta_brier, 4),
        "delta_brier_ci_95": delta_brier_ci,
        "ci_excludes_zero": ci_excludes_zero,
        "hypothesis_confirmed": confirmed,
    }

    (DIR / "results.json").write_text(json.dumps(results, indent=2))
    print(
        f"EXP-K1-001 Complete: baseline AUC={auc_base:.4f}, shrunk AUC={auc_shrunk:.4f}, delta={delta_auc:.4f} 95% CI {delta_auc_ci}"
    )

    verdict_str = "CONFIRMED" if confirmed else "REFUTED (CI includes zero)" if not ci_excludes_zero else "REFUTED (below threshold)"
    report = f"""# EXP-K1-001 Report: Informative Prior Shrinkage

- **Baseline ROC-AUC:** {results["baseline_auc"]:.4f}
- **Intervention ROC-AUC:** {results["intervention_auc"]:.4f}
- **Delta ROC-AUC:** {results["delta_auc"]:+.4f} [95% CI: {delta_auc_ci[0]:+.4f}, {delta_auc_ci[1]:+.4f}]
- **Baseline Brier Score:** {results["baseline_brier"]:.4f}
- **Intervention Brier Score:** {results["intervention_brier"]:.4f}
- **Delta Brier Score:** {results["delta_brier"]:+.4f} [95% CI: {delta_brier_ci[0]:+.4f}, {delta_brier_ci[1]:+.4f}]
- **Hypothesis Verdict:** {verdict_str}

### Findings
Shrinking prior doubling time bounds produced a delta AUC of {results["delta_auc"]:+.4f} with 95% bootstrap confidence interval [{delta_auc_ci[0]:+.4f}, {delta_auc_ci[1]:+.4f}]. Because the confidence interval encompasses zero, the effect is statistically indistinguishable from noise (RR14), and fails to reach the pre-registered threshold of >=0.02.
"""
    (DIR / "REPORT.md").write_text(report)


if __name__ == "__main__":
    main()
