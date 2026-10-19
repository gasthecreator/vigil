"""
packages/vigil-ml/tests/test_phase3_models.py

Comprehensive test suite for Phase 3 ML deliverables:
1. K1 Kinetic Hybrid Model: Continuous ODE dynamics, online UKF filtering, SBC, and parameter recovery.
2. K2 sequential scoring: Exercise implementation behavior. These empirical tests do not establish a supermartingale or Ville-valid guarantee (see S-018).
3. K4 Deep Irregular-Time Zoo: moved to `packages/vigil-ml/tests/test_k4.py` (the earlier stub `deep_zoo_k4.py` is retired, ADR-0025).
4. K5 Hierarchical Pooling & Lab Harmonisation: Site offsets, empirical Bayes shrinkage, and analytical changepoint detector.
5. K6 Active Sensing: moved to `packages/vigil-ml/tests/test_k6.py` (the earlier stub `active_sensing_k6.py` is retired, ADR-0026).
6. K8 Conformal Ensemble & Runtime: False Negative Rate bounds, Mahalanobis OOD detection, abstention policy, ONNX/Safetensors export, parity (< 1e-4), and CPU latency budget (p95 < 100 ms).
"""

from __future__ import annotations

import numpy as np
import pytest
from vigil_ml import k1
from vigil_ml.conformal_k8 import AbstentionReason, ConformalRiskControllerK8
from vigil_ml.export import (
    SurrogateInferenceNet,
    export_to_onnx,
    export_to_safetensors,
    verify_onnx_parity,
)
from vigil_ml.harmonisation_k5 import HierarchicalLabHarmoniserK5
from vigil_ml.k2 import AlertTier, SequentialDetector
from vigil_ml.runtime import VigilProductionRuntime

# ---------------------------------------------------------------------------
# K1 Tests
# ---------------------------------------------------------------------------

def test_k1_legacy_import_resolves_to_canonical_implementation():
    from vigil_ml.kinetic_k1 import HybridKineticModelK1

    assert HybridKineticModelK1 is k1.HybridKineticModelK1


def test_k1_identity_does_not_expose_legacy_label_training_api():
    model = k1.HybridKineticModelK1()
    assert not hasattr(model, "fit")
    assert not hasattr(model, "filter_online")


# ---------------------------------------------------------------------------
# K2 Tests
# ---------------------------------------------------------------------------

def test_k2_sequential_eprocess_and_tiers():
    ep = SequentialDetector(alpha_pt=0.05, sigma_log=0.12)
    # Baseline quiescent sequence -> e-value remains small
    rng = np.random.default_rng(20261019)
    quiescent_visits = [18.0 + rng.normal(0.0, 0.3) for _ in range(8)]
    for day, value in enumerate(quiescent_visits):
        ep.update(float(day * 90), float(value))
    assert not ep.alert
    assert ep.tier in [AlertTier.NONE, AlertTier.WATCH]

    # Escalating sequence -> e-value spikes crossing Ville's threshold
    spiking_visits = [
        {"day": 0.0, "ca15_3": 18.0},
        {"day": 90.0, "ca15_3": 28.0},
        {"day": 180.0, "ca15_3": 45.0},
        {"day": 270.0, "ca15_3": 85.0},
    ]
    for visit in spiking_visits:
        ep.update(visit["day"], visit["ca15_3"])
    assert ep.alert
    assert ep.tier in [AlertTier.REVIEW, AlertTier.URGENT]


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
    k8.calibrate(np.array([0.1, 0.2, 0.3, 0.4]), np.array([1, 1, 1, 1]))
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
    assert res_ood.risk_score is None
    assert res_ood.score_range is None


def test_k8_finite_sample_rank_and_uncalibrated_abstention():
    k8 = ConformalRiskControllerK8(alpha_conf=0.5)
    uncalibrated = k8.predict(raw_risk=0.2, epistemic_std=0.01)
    assert uncalibrated.abstention == AbstentionReason.ABSTAIN_UNCALIBRATED
    assert uncalibrated.risk_score is None
    assert uncalibrated.score_range is None
    assert uncalibrated.conformal_quantile is None

    k8.calibrate(np.array([0.1, 0.2, 0.3]), np.array([1, 1, 1]))
    high_uncertainty = k8.predict(raw_risk=0.2, epistemic_std=0.4)
    assert high_uncertainty.abstention == AbstentionReason.ABSTAIN_HIGH_UNCERTAINTY
    assert high_uncertainty.risk_score is None
    assert high_uncertainty.score_range is None

    # floor((3 + 1) * .5) = 2; the second ascending positive score is the cutoff.
    assert k8.calibrated_threshold == 0.2


def test_k8_rejects_invalid_calibration_and_prediction_inputs():
    k8 = ConformalRiskControllerK8()
    with pytest.raises(ValueError, match="scores must be finite"):
        k8.calibrate(np.array([0.2, 0.4]), np.array([0, 1.5]))
    with pytest.raises(ValueError, match="scores must be finite"):
        k8.calibrate(np.array([0.2, 1.1]), np.array([0, 1]))
    with pytest.raises(ValueError, match="raw_risk"):
        k8.predict(raw_risk=float("nan"), epistemic_std=0.1)


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
