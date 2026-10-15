"""
packages/vigil-ml/tests/test_kinetic_k1_real.py

Comprehensive test suite verifying Phase 3A requirements for Model K1:
1. Unit tests of continuous ODE integrator against analytical closed-form solutions (marker clearance, uncoupled growth).
2. Step-size convergence of the RK4 integrator.
3. Genuine model training via fit() on simulated patient cohorts with loss logging.
4. Posterior-derived prospective risk scoring with credible intervals.
5. Online continuous-discrete UKF filtering with Normalized Innovation Squared (NIS) consistency check.
6. Real Simulation-Based Calibration (SBC) rank-uniformity test.
7. Real parameter recovery for tumor doubling times, shedding rates, and clearance.
8. Structural identifiability analysis under typical visit schedules.
"""

from __future__ import annotations

import math

import numpy as np
import torch
from vigil_ml.kinetic_k1 import (
    STATE_DIM,
    HybridKineticModelK1,
    KineticODEFactor,
)


def test_kinetic_ode_closed_form_clearance():
    """
    Verifies that under zero tumor burden (b=0), circulating marker pool
    decays according to exact analytical first-order clearance: m(t) = m_0 * exp(-c * t).
    """
    ode = KineticODEFactor(hidden_dim=16, max_residual=0.0)
    # Zero out neural residual
    for p in ode.residual_net.parameters():
        p.data.zero_()

    z0 = torch.zeros(1, STATE_DIM)
    m0_ca153 = 50.0
    m0_cea = 15.0
    z0[0, 5] = m0_ca153
    z0[0, 6] = m0_cea

    t_span = 30.0  # 30 days
    dt = 0.5  # 0.5-day RK4 steps

    z_final = ode.integrate(z0, t_span=t_span, dt=dt)
    m_final_ca153 = float(z_final[0, 5].item())
    m_final_cea = float(z_final[0, 6].item())

    # Analytical expectation: m(t) = m_0 * exp(-c * t)
    c_ca153 = 0.085
    c_cea = 0.140
    expected_ca153 = m0_ca153 * math.exp(-c_ca153 * t_span)
    expected_cea = m0_cea * math.exp(-c_cea * t_span)

    # Relative error should be < 0.1%
    rel_err_ca153 = abs(m_final_ca153 - expected_ca153) / expected_ca153
    rel_err_cea = abs(m_final_cea - expected_cea) / expected_cea

    assert rel_err_ca153 < 1e-3, f"CA 15-3 clearance rel error {rel_err_ca153:.6f} exceeded tolerance"
    assert rel_err_cea < 1e-3, f"CEA clearance rel error {rel_err_cea:.6f} exceeded tolerance"


def test_kinetic_ode_closed_form_growth():
    """
    Verifies that for small tumor mass (b << K) and no treatment,
    tumor burden outgrowth matches exact uncoupled exponential growth: b(t) = b_0 * exp(g * t).
    """
    ode = KineticODEFactor(hidden_dim=16, max_residual=0.0)
    for p in ode.residual_net.parameters():
        p.data.zero_()

    z0 = torch.zeros(1, STATE_DIM)
    b0 = 0.5  # Very small initial mass (far from saturation limit K=1000)
    z0[0, 0] = b0  # Locoregional compartment

    # Set known growth rate g = 0.020 / day
    ode.log_growth.data[0] = math.log(0.020)

    t_span = 20.0
    z_final = ode.integrate(z0, t_span=t_span, dt=0.5)
    b_final = float(z_final[0, 0].item())

    expected_b = b0 * math.exp(0.020 * t_span)
    rel_err = abs(b_final - expected_b) / expected_b

    assert rel_err < 5e-3, f"Tumor growth rel error {rel_err:.6f} exceeded tolerance"


def test_kinetic_ode_step_size_convergence():
    """
    Verifies that the RK4 numerical integrator exhibits high-order step-size convergence:
    halving step size dt reduces integration truncation error.
    """
    ode = KineticODEFactor(hidden_dim=16, max_residual=0.0)
    z0 = torch.zeros(1, STATE_DIM)
    z0[0, 0] = 5.0
    z0[0, 5] = 20.0

    t_span = 10.0

    # Reference "exact" solution computed with very fine step size (dt=0.01)
    z_ref = ode.integrate(z0, t_span=t_span, dt=0.01)

    # Coarse step (dt=2.0)
    z_coarse = ode.integrate(z0, t_span=t_span, dt=2.0)
    # Fine step (dt=1.0)
    z_fine = ode.integrate(z0, t_span=t_span, dt=1.0)

    err_coarse = float(torch.norm(z_coarse - z_ref).item())
    err_fine = float(torch.norm(z_fine - z_ref).item())

    # Finer step size must yield strictly smaller error
    assert err_fine < err_coarse, f"Fine error {err_fine} not smaller than coarse error {err_coarse}"
    assert err_fine < 0.1 * err_coarse + 1e-4, "Expected significant error reduction upon halving dt"


def test_k1_model_fit_genuine_training():
    """
    Verifies that fit() executes real neural training on clinical features:
    - Training and validation losses are computed and logged per epoch.
    - Loss decreases across training epochs.
    - Model weights are modified from initial values.
    """
    k1 = HybridKineticModelK1(horizon_days=365.0, hidden_dim=32, lr=5e-3, seed=123)

    # Synthetic training dataset of 120 patients
    rng = np.random.default_rng(42)
    n = 120
    ca153 = rng.uniform(15.0, 60.0, size=n)
    slopes = rng.uniform(-0.1, 0.8, size=n)
    # Event correlated with elevated marker and steep slope
    prob = 1.0 / (1.0 + np.exp(-(-2.0 + 0.05 * (ca153 - 25.0) + 2.5 * slopes)))
    y = (rng.uniform(0.0, 1.0, size=n) < prob).astype(float)

    X_df = {
        "ca_15_3_curr": ca153,
        "ca_15_3_slope_90d": slopes,
        "cea_curr": rng.uniform(1.0, 8.0, size=n),
        "alt_curr": rng.uniform(15.0, 45.0, size=n),
        "ast_curr": rng.uniform(15.0, 40.0, size=n),
        "alp_curr": rng.uniform(50.0, 120.0, size=n),
        "age": rng.uniform(35.0, 70.0, size=n),
    }

    initial_weight = k1.recognition_net.fc_risk_logit.weight.clone()

    k1.fit(X_df, y, epochs=10, batch_size=32)

    assert k1.is_fitted is True
    assert len(k1.training_history_["train_loss"]) == 10
    assert len(k1.training_history_["val_loss"]) == 10

    # Verify loss decreased from start to end
    first_loss = k1.training_history_["train_loss"][0]
    final_loss = k1.training_history_["train_loss"][-1]
    assert final_loss < first_loss, f"Final loss {final_loss:.4f} not lower than first loss {first_loss:.4f}"

    # Verify weights changed
    final_weight = k1.recognition_net.fc_risk_logit.weight
    assert not torch.allclose(initial_weight, final_weight), "Model weights did not update during fit()"


def test_k1_predict_risk_posterior_and_intervals():
    """
    Verifies predict_risk outputs valid probabilities in (0, 1),
    shows biological sensitivity (higher marker level -> higher risk),
    and produces valid 90% credible intervals when return_ci=True.
    """
    k1 = HybridKineticModelK1(horizon_days=365.0, hidden_dim=32, seed=42)
    # Fit on small synthetic cohort
    ca153 = np.array([18.0, 22.0, 28.0, 45.0, 65.0] * 20)
    slopes = np.array([0.0, 0.05, 0.15, 0.40, 0.80] * 20)
    y = np.array([0.0, 0.0, 0.0, 1.0, 1.0] * 20)
    k1.fit({"ca_15_3_curr": ca153, "ca_15_3_slope_90d": slopes}, y, epochs=8)

    # Test cases: quiescent vs accelerating patient
    test_cases = {
        "ca_15_3_curr": np.array([18.0, 55.0]),
        "ca_15_3_slope_90d": np.array([0.0, 0.65]),
        "cea_curr": np.array([1.5, 6.0]),
        "alt_curr": np.array([20.0, 45.0]),
    }

    risks, ci_low, ci_high = k1.predict_risk(test_cases, return_ci=True)

    assert len(risks) == 2
    assert 0.0 < risks[0] < risks[1] < 1.0, "High marker case must have higher risk than low marker case"
    assert ci_low[0] <= risks[0] <= ci_high[0]
    assert ci_low[1] <= risks[1] <= ci_high[1]


def test_k1_online_ukf_consistency_check():
    """
    Verifies that the UKF online filtering engine evaluates Normalized Innovation Squared (NIS)
    and reports consistency against 95% chi-square theoretical confidence bounds.
    """
    k1 = HybridKineticModelK1()
    history = [
        {"day": 0.0, "ca15_3": 18.0, "cea": 2.0, "alt": 22.0},
        {"day": 90.0, "ca15_3": 18.8, "cea": 2.1, "alt": 21.5},
        {"day": 180.0, "ca15_3": 19.5, "cea": 2.2, "alt": 23.0},
        {"day": 270.0, "ca15_3": 20.2, "cea": 2.1, "alt": 22.0},
    ]

    x_post, P_post, log_liks, consistency = k1.filter_online(history)

    assert x_post.shape == (9,)
    assert P_post.shape == (9, 9)
    assert len(log_liks) == 4
    assert "average_nis" in consistency
    assert "bounds_95pct" in consistency
    assert consistency["average_nis"] > 0.0
    assert consistency["is_consistent"] is True


def test_k1_sbc_rank_uniformity():
    """
    Verifies that Simulation-Based Calibration (SBC) runs through actual ODE dynamics
    and inference code, yielding uniform rank statistics with KS p-value > 0.01.
    """
    k1 = HybridKineticModelK1()
    sbc_results = k1.run_sbc(n_simulations=40, seed=123)

    assert sbc_results["n_simulations"] == 40
    assert sbc_results["ks_pvalue"] > 0.01, f"SBC failed rank uniformity: {sbc_results}"
    assert sbc_results["sbc_passed"] is True


def test_k1_parameter_recovery_real():
    """
    Verifies that parameter recovery runs through the actual kinetic ODE dynamics
    and evaluates doubling times with correlation > 0.70 and 90% credible interval coverage >= 0.70.
    """
    k1 = HybridKineticModelK1()
    recovery = k1.parameter_recovery_test(n_cohorts=25, seed=42)

    assert recovery["n_cohorts"] == 25
    assert recovery["correlation"] > 0.70, f"Correlation {recovery['correlation']} below 0.70 threshold"
    assert recovery["empirical_90pct_coverage"] >= 0.70, (
        f"Coverage {recovery['empirical_90pct_coverage']} below nominal 0.70 bound"
    )
    assert recovery["recovery_passed"] is True


def test_k1_identifiability_analysis():
    """
    Verifies that structural identifiability analysis computes Fisher information
    eigenvalues and documents identifiable vs non-identifiable parameters.
    """
    k1 = HybridKineticModelK1()
    ident = k1.identifiability_analysis()

    assert "eigenvalues" in ident
    assert len(ident["eigenvalues"]) > 0
    assert len(ident["identifiable_parameters"]) >= 3
    assert len(ident["non_identifiable_parameters"]) >= 2
    assert ident["identifiability_status"] == "IDENTIFIABLE_UNDER_REGULARIZING_PRIOR"
