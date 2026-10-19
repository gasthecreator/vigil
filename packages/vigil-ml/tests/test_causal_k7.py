"""Unit and Statistical Property Tests for Causal K7 (Study S8-K7).

Verifies Master Plan §3, §6.7, §11, and ML_PROGRAM §3.7:
1. Target-trial cohort generation integrity.
2. VanderWeele & Ding E-value properties and boundary conditions.
3. Covariate balance under IPTW (SMD reduction).
4. Recovery of ground-truth causal effect under measured confounding.
5. Injected unmeasured confounding failure detection.
"""

import math

import numpy as np
from vigil_ml.causal_k7 import (
    TargetTrialEmulation,
    compute_e_value,
    generate_synthetic_causal_cohort,
)


def test_synthetic_cohort_generation():
    """Cohort generator must emit valid patient structures and realistic clinical distributions."""
    cohort = generate_synthetic_causal_cohort(n_patients=500, seed=123)
    assert len(cohort.patient_ids) == 500
    assert cohort.covariate_matrix.shape == (500, 6)
    assert len(cohort.covariate_names) == 6
    assert set(np.unique(cohort.treatment)).issubset({0, 1})
    assert set(np.unique(cohort.outcome)).issubset({0, 1})
    assert np.all(cohort.delays_days >= 14.0)


def test_e_value_properties():
    """E-value must strictly obey mathematical bounds of VanderWeele & Ding (2017)."""
    # Null effect (RR = 1.0) -> E-value = 1.0
    null_res = compute_e_value(1.0, (1.0, 1.0))
    assert null_res["e_value_estimate"] == 1.0
    assert null_res["e_value_ci_lower"] == 1.0
    assert compute_e_value(float("inf"))["e_value_estimate"] == 1.0

    # RR = 1.5 -> E-value = 1.5 + sqrt(1.5 * 0.5) = 1.5 + 0.8660 = 2.3660
    res = compute_e_value(1.5, (1.2, 1.8))
    expected_est = 1.5 + math.sqrt(1.5 * 0.5)
    expected_ci = 1.2 + math.sqrt(1.2 * 0.2)
    assert abs(res["e_value_estimate"] - expected_est) < 0.001
    assert abs(res["e_value_ci_lower"] - expected_ci) < 0.001

    # For a protective estimate, the upper limit is closest to the null.
    protective_ci = compute_e_value(0.5, (0.4, 0.8))
    nearest_null_rr = 1 / 0.8
    expected_protective_ci = nearest_null_rr + math.sqrt(nearest_null_rr * (nearest_null_rr - 1))
    assert abs(protective_ci["e_value_ci_lower"] - expected_protective_ci) < 0.001
    assert compute_e_value(0.8, (0.6, 1.1))["e_value_ci_lower"] == 1.0

    # Protective effect (RR = 0.5) -> inverted RR* = 2.0 -> E-value = 2 + sqrt(2 * 1) = 3.4142
    prot = compute_e_value(0.5)
    expected_prot = 2.0 + math.sqrt(2.0 * 1.0)
    assert abs(prot["e_value_estimate"] - expected_prot) < 0.001


def test_smd_covariate_balance():
    """IPTW weighting must reduce covariate imbalance between timely and delayed groups."""
    cohort = generate_synthetic_causal_cohort(n_patients=2000, seed=42)
    tte = TargetTrialEmulation()
    res = tte.estimate_effects(cohort)

    unweighted_smd = res["covariate_balance"]["unweighted_smd"]
    res["covariate_balance"]["weighted_smd"]

    # Maximum weighted SMD must be lower than maximum unweighted SMD
    max_unweighted = max(unweighted_smd.values())
    max_weighted = res["covariate_balance"]["max_weighted_smd"]
    assert max_weighted < max_unweighted
    # IPTW must achieve standardized mean differences < 0.10 across all measured covariates
    assert max_weighted < 0.10, (
        f"Max weighted SMD ({max_weighted}) exceeded target balance threshold 0.10"
    )


def test_smd_rejects_empty_arm_and_zero_weight_arm():
    import pytest
    from vigil_ml.causal_k7 import compute_smd

    with pytest.raises(ValueError, match="both treatment groups"):
        compute_smd(np.array([1.0, 2.0]), np.array([0, 0]))
    with pytest.raises(ValueError, match="zero total weight"):
        compute_smd(np.array([1.0, 2.0]), np.array([0, 1]), np.array([1.0, 0.0]))


def test_aipw_recovers_known_ground_truth():
    """AIPW and IPTW must recover true synthetic causal risk ratio under measured confounding."""
    cohort = generate_synthetic_causal_cohort(
        n_patients=5000, seed=20261017, true_causal_rr=1.20, inject_unmeasured_confounder=False
    )
    tte = TargetTrialEmulation()
    res = tte.estimate_effects(cohort)

    true_rr = cohort.true_rr
    aipw_rr = res["estimates"]["aipw"]["rr"]
    naive_rr = res["estimates"]["naive"]["rr"]

    # Naive estimator is confounded (away from true_rr)
    # AIPW should be closer to true_rr than naive
    assert abs(aipw_rr - true_rr) < abs(naive_rr - true_rr)
    # AIPW error within 0.08 of true RR
    assert abs(aipw_rr - true_rr) < 0.08


def test_honest_failure_under_unmeasured_confounding():
    """Condition P13-E: AIPW fails under unmeasured confounding and the E-value only quantifies how strong a confounder would need to be."""
    true_rr = 1.12
    cohort = generate_synthetic_causal_cohort(
        n_patients=3000, seed=999, true_causal_rr=true_rr, inject_unmeasured_confounder=True
    )
    tte = TargetTrialEmulation()
    res = tte.estimate_effects(cohort)

    # Injected confounder shifts naive and unadjusted estimates upward (AIPW failure mode)
    aipw_rr = res["estimates"]["aipw"]["rr"]
    bias = aipw_rr - true_rr
    assert bias > 0.05, f"Expected substantial unmeasured confounding bias, got {bias}"

    # E-value quantifies sensitivity (how strong confounder must be), not confounding detection
    e_val = compute_e_value(aipw_rr)
    assert e_val["e_value_estimate"] >= 1.5
