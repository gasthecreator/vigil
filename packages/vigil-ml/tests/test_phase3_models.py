"""
packages/vigil-ml/tests/test_phase3_models.py

Comprehensive test suite for Phase 3 ML deliverables:
1. K1 Kinetic Hybrid Model: Continuous ODE dynamics, online UKF filtering, SBC, and parameter recovery.
2. K2 Anytime-Valid Sequential Detection: Test supermartingales (e-processes), Ville's inequality, and 5-scenario Null Stress Suite.
3. K4 Deep Irregular-Time Zoo: moved to `packages/vigil-ml/tests/test_k4.py` (the earlier stub `deep_zoo_k4.py` is retired, ADR-0025).
4. K5 Hierarchical Pooling & Lab Harmonisation: Site offsets, empirical Bayes shrinkage, and analytical changepoint detector.
5. K6 Active Sensing: moved to `packages/vigil-ml/tests/test_k6.py` (the earlier stub `active_sensing_k6.py` is retired, ADR-0026).
6. K8 Conformal Ensemble & Runtime: False Negative Rate bounds, Mahalanobis OOD detection, abstention policy, ONNX/Safetensors export, parity (< 1e-4), and CPU latency budget (p95 < 100 ms).
"""

from __future__ import annotations

import numpy as np
import torch
from vigil_ml.conformal_k8 import AbstentionReason, ConformalRiskControllerK8
from vigil_ml.export import (
    SurrogateInferenceNet,
    export_to_onnx,
    export_to_safetensors,
    verify_onnx_parity,
)
from vigil_ml.harmonisation_k5 import HierarchicalLabHarmoniserK5
from vigil_ml.kinetic_k1 import HybridKineticModelK1, KineticODEFactor
from vigil_ml.runtime import VigilProductionRuntime
from vigil_ml.sequential_k2 import AlertTier, SequentialDetectorBenchmark, SequentialEProcessK2

# ---------------------------------------------------------------------------
# K1 Tests
# ---------------------------------------------------------------------------

def test_k1_ode_dynamics_forward():
    ode = KineticODEFactor(hidden_dim=16)
    z = torch.ones(2, 9) * 10.0
    treatment = torch.zeros(2, 3)
    t = torch.tensor([[0.0]])
    dz = ode(t, z, treatment)
    assert dz.shape == (2, 9)
    assert torch.isfinite(dz).all()


def test_k1_online_ukf_filtering():
    k1 = HybridKineticModelK1()
    history = [
        {"day": 0.0, "ca15_3": 18.2, "alt": 21.0},
        {"day": 90.0, "ca15_3": 19.5, "alt": 22.5},
        {"day": 180.0, "ca15_3": 24.0, "alt": 25.0},
    ]
    x, P, log_liks, consistency = k1.filter_online(history)
    assert x.shape == (9,)
    assert P.shape == (9, 9)
    assert len(log_liks) == 3
    assert "average_nis" in consistency
    assert np.all(x >= 0.0)


def test_k1_sbc_and_parameter_recovery():
    k1 = HybridKineticModelK1()
    sbc_res = k1.run_sbc(n_simulations=50)
    assert sbc_res["ks_pvalue"] > 0.01, f"SBC failed: {sbc_res}"

    rec_res = k1.parameter_recovery_test(n_cohorts=30)
    assert rec_res["correlation"] > 0.80
    assert rec_res["empirical_90pct_coverage"] >= 0.75


# ---------------------------------------------------------------------------
# K2 Tests
# ---------------------------------------------------------------------------

def test_k2_sequential_eprocess_and_tiers():
    ep = SequentialEProcessK2(alpha_pt=0.05)
    # Baseline quiescent sequence -> e-value remains small
    quiescent_visits = [{"day": d * 90.0, "ca15_3": 18.0 + np.random.normal(0, 1.0)} for d in range(5)]
    q_results = ep.evaluate_trajectory(quiescent_visits)
    assert q_results[-1].e_value < 20.0
    assert q_results[-1].tier in [AlertTier.NONE, AlertTier.WATCH]

    # Escalating sequence -> e-value spikes crossing Ville's threshold
    spiking_visits = [
        {"day": 0.0, "ca15_3": 18.0},
        {"day": 90.0, "ca15_3": 28.0},
        {"day": 180.0, "ca15_3": 45.0},
        {"day": 270.0, "ca15_3": 85.0},
    ]
    s_results = ep.evaluate_trajectory(spiking_visits)
    assert s_results[-1].e_value > 20.0
    assert s_results[-1].tier in [AlertTier.REVIEW, AlertTier.URGENT]


def test_k2_validity_stress_suite_5_scenarios():
    benchmark = SequentialDetectorBenchmark(alpha_pt=0.05)
    stress_res = benchmark.run_stress_suite(n_patients=60, n_visits=10)
    assert stress_res["all_passed"], f"Stress suite failed: {stress_res}"
    for scenario_name, sc_data in stress_res["scenarios"].items():
        assert sc_data["empirical_patient_level_far"] <= (0.05 + 0.05), (
            f"Scenario {scenario_name} violated patient-level false alarm bound: {sc_data}"
        )


# ---------------------------------------------------------------------------
# K5 Tests
# ---------------------------------------------------------------------------

def test_k5_hierarchical_pooling_and_changepoints():
    k5 = HierarchicalLabHarmoniserK5()
    site_data = {
        "lab_a": [{"ca15_3": 18.0, "alt": 22.0} for _ in range(30)],
        "lab_b_biased": [{"ca15_3": 24.0, "alt": 22.0} for _ in range(40)],
    }
    k5.fit_sites(site_data)
    assert "lab_b_biased" in k5.site_profiles
    assert k5.site_profiles["lab_b_biased"].analyte_offsets["ca15_3"] > 2.0

    # Test changepoint detector on sudden systemic shift
    shift_detected = False
    for _ in range(15):
        _, is_shift = k5.ingest_and_check_lab_shift("lab_b_biased", "ca15_3", 35.0, expected_val=24.0)
        if is_shift:
            shift_detected = True
            break
    assert shift_detected, "Failed to detect systemic lab shift"


# ---------------------------------------------------------------------------
# K8 & Production Runtime Tests
# ---------------------------------------------------------------------------

def test_k8_conformal_risk_control_and_ood():
    k8 = ConformalRiskControllerK8(alpha_conf=0.10)
    # Fit OOD on standard normal features
    X_train = np.random.normal(0, 1.0, (100, 15))
    k8.fit_ood_detector(X_train)

    # In-distribution sample
    in_dist_x = np.random.normal(0, 1.0, 15)
    res_in = k8.predict(raw_risk=0.35, epistemic_std=0.05, feature_vector=in_dist_x)
    assert res_in.abstention == AbstentionReason.NONE
    assert res_in.alert_tier in ["review", "watch"]

    # Extreme OOD sample -> Abstention triggered
    ood_x = np.ones(15) * 50.0
    res_ood = k8.predict(raw_risk=0.35, epistemic_std=0.05, feature_vector=ood_x)
    assert res_ood.abstention == AbstentionReason.ABSTAIN_OOD
    assert res_ood.alert_tier == "abstain"


def test_production_export_parity_and_latency(tmp_path):
    net = SurrogateInferenceNet(input_dim=15, hidden_dim=32)
    onnx_file = tmp_path / "model.onnx"
    safetensors_file = tmp_path / "model.safetensors"

    export_to_onnx(net, onnx_file)
    export_to_safetensors(net, safetensors_file)
    assert onnx_file.exists()
    assert safetensors_file.exists()

    # Numerical parity verification (< 1e-4)
    parity_res = verify_onnx_parity(net, onnx_file, input_dim=15, n_samples=50)
    assert parity_res["parity_passed"], f"Parity failed: {parity_res}"
    assert parity_res["max_absolute_difference"] < 1e-4

    # Runtime and CPU latency benchmark (p95 < 100 ms)
    runtime = VigilProductionRuntime(onnx_model_path=onnx_file)
    bench = runtime.benchmark_latency(n_calls=200)
    assert bench["budget_passed"], f"Latency budget exceeded: {bench}"
    assert bench["p95_latency_ms"] < 100.0
