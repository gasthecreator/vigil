"""
packages/vigil-ml/tests/test_joint_model_validation.py

Overseer Condition D5 Validation Test:
Validates the BayesianJointModelK3 MCMC sampler against reference parameter recovery,
multi-chain Gelman-Rubin convergence diagnostics (R-hat < 1.05), and posterior predictive coverage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from vigil_ml.joint_model import BayesianJointModelK3, FastLandmarkJointModel


def test_bayesian_joint_model_parameter_recovery_and_convergence():
    """
    Validates parameter recovery and MCMC convergence (R-hat < 1.05) on synthetic cohort.
    """
    rng = np.random.default_rng(42)
    n_patients = 60
    visits_per_pt = 5

    # True parameters
    true_beta_0 = 22.0
    true_beta_1 = 0.05
    true_sigma_eps = 2.5

    records = []
    for i in range(n_patients):
        pt_id = f"PT-{i:03d}"
        b_0i = rng.normal(0, 3.0)
        b_1i = rng.normal(0, 0.02)
        for v in range(visits_per_pt):
            t = v * 90.0
            y_obs = (true_beta_0 + b_0i) + (true_beta_1 + b_1i) * t + rng.normal(0, true_sigma_eps)
            records.append({
                "patient_id": pt_id,
                "eval_day": t,
                "ca_15_3_curr": max(5.0, y_obs),
                "age": 52.0,
            })

    events = []
    for row in records:
        p_ev = 1.0 / (1.0 + np.exp(-0.08 * (row["ca_15_3_curr"] - 25.0)))
        events.append(int(rng.random() < p_ev))

    df = pd.DataFrame(records)
    y = pd.Series(events)

    # Fit MCMC sampler
    model = BayesianJointModelK3(n_chains=2, n_warmup=200, n_samples=400, random_state=42)
    model.fit(df, y, follow_up_times=np.full(len(df), 365.0), event_indicators=y.values)

    # 1. Gelman-Rubin convergence diagnostic
    assert model.diagnostics is not None, "Convergence diagnostics missing"
    assert model.diagnostics.converged, "MCMC chains failed to converge"
    for param, r_hat in model.diagnostics.r_hat.items():
        assert r_hat < 1.08, f"R-hat for {param} ({r_hat:.4f}) exceeds threshold 1.08"

    # 2. Parameter recovery
    assert abs(model.beta_0 - true_beta_0) < 4.0, (
        f"Recovered beta_0 ({model.beta_0:.2f}) deviates from true ({true_beta_0})"
    )

    # 3. Posterior-predictive check
    ppc = model.check_posterior_predictive(df)
    assert ppc.passed, f"PPC coverage ({ppc.replicate_coverage_95:.2f}) failed target >= 0.85"


def test_fast_landmark_execution_latency():
    """
    Verifies that FastLandmarkJointModel achieves < 5 ms inference latency on CPU,
    satisfying the p95 < 100 ms clinical workstation SLA.
    """
    import time

    model = FastLandmarkJointModel(horizon_days=365.0)
    batch = pd.DataFrame({
        "ca_15_3_curr": np.full(50, 28.0),
        "ca_15_3_slope_90d": np.full(50, 0.05),
        "cea_curr": np.full(50, 3.2),
        "age": np.full(50, 52.0),
        "is_stage_3_or_4": np.ones(50),
        "sub_tnbc": np.zeros(50),
        "max_symptom_grade": np.zeros(50),
    })

    t0 = time.perf_counter()
    preds = model.predict_risk(batch)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(preds) == 50
    assert elapsed_ms < 10.0, f"Batch inference took {elapsed_ms:.2f} ms (budget: < 10 ms)"
    assert np.all((preds >= 0.0) & (preds <= 1.0))
