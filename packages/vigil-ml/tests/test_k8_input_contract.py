import numpy as np
import pytest
from scipy.stats import chi2
from vigil_ml.conformal_k8 import ConformalRiskControllerK8
from vigil_ml.k8 import AdaptiveConformal, ConformalRiskController, OODGate


@pytest.mark.parametrize("alpha", [0.0, 1.0, float("nan"), float("inf")])
def test_conformal_alpha_must_be_finite_and_in_range(alpha):
    with pytest.raises(ValueError, match="alpha must be finite"):
        ConformalRiskController(alpha)


def test_crc_requires_valid_calibration_and_fit_before_prediction():
    controller = ConformalRiskController(0.1)
    with pytest.raises(RuntimeError, match="fit must be called"):
        controller.decide(np.array([0.2]))
    with pytest.raises(ValueError, match="at least one positive"):
        controller.fit(np.array([0.1, 0.2]), np.array([0, 0]))
    with pytest.raises(ValueError, match="equal length"):
        controller.fit(np.array([0.1]), np.array([0, 1]))
    with pytest.raises(ValueError, match="only 0 or 1"):
        controller.fit(np.array([0.1, 0.2]), np.array([0, 0.5]))
    controller.fit(np.array([0.1, 0.8]), np.array([0, 1]))
    with pytest.raises(ValueError, match="finite one-dimensional"):
        controller.decide(np.array([np.nan]))


def test_ood_gate_validates_fit_and_prediction_inputs():
    gate = OODGate()
    with pytest.raises(RuntimeError, match="fit must be called"):
        gate.is_ood(np.zeros((1, 2)))
    with pytest.raises(ValueError, match="at least two rows"):
        gate.fit(np.ones((1, 2)))
    with pytest.raises(ValueError, match="finite values"):
        gate.fit(np.array([[0.0, np.nan], [1.0, 2.0]]))
    gate.fit(np.array([[0.0], [1.0], [2.0]]))
    assert gate.is_ood(np.array([[0.5]])).shape == (1,)
    with pytest.raises(ValueError, match="feature dimension"):
        gate.is_ood(np.zeros((1, 2)))


def test_adaptive_conformal_rejects_invalid_parameters():
    with pytest.raises(ValueError, match="alpha must be finite"):
        AdaptiveConformal(float("nan"))
    with pytest.raises(ValueError, match="gamma must be finite and positive"):
        AdaptiveConformal(0.1, gamma=0.0)


def test_k8_cannot_calibrate_a_false_negative_bound_without_positive_events():
    controller = ConformalRiskControllerK8(alpha_conf=0.1)
    with pytest.raises(ValueError, match="at least one positive event"):
        controller.calibrate(np.array([0.1, 0.2]), np.array([0, 0]))
    assert not controller.is_calibrated
    result = controller.predict(raw_risk=0.15, epistemic_std=0.0)
    assert result.risk_score is None
    assert result.config_id == "k8_unvalidated_research_defaults_v1"
    assert result.config_sha256 == controller.config_sha256


def test_k8_research_configuration_hash_tracks_effective_overrides():
    default = ConformalRiskControllerK8()
    overridden = ConformalRiskControllerK8(alpha_conf=0.2)
    assert default.config_id == overridden.config_id
    assert default.config_sha256 != overridden.config_sha256
    assert not default.is_calibrated
    assert default.running_threshold is None


@pytest.mark.parametrize("kwargs", [{"alpha_conf": True}, {"adapt_rate": "0.05"}])
def test_k8_rejects_non_numeric_research_overrides(kwargs):
    with pytest.raises(ValueError, match="numeric scalar"):
        ConformalRiskControllerK8(**kwargs)


@pytest.mark.parametrize("dimensions", [1, 3, 15, 40])
def test_k8_ood_cutoff_uses_feature_dimension(dimensions):
    controller = ConformalRiskControllerK8()
    rng = np.random.default_rng(20261020 + dimensions)
    controller.fit_ood_detector(rng.normal(size=(100, dimensions)))
    expected = chi2.ppf(1.0 - controller.config["ood_tail_probability"], df=dimensions)
    assert controller.ood_threshold == pytest.approx(expected)


def test_k8_adaptation_requires_fitted_calibration_and_boolean_feedback():
    controller = ConformalRiskControllerK8()
    with pytest.raises(RuntimeError, match="requires a calibrated"):
        controller.adapt_online(pred_alert=False, true_event=True)
    controller.calibrate(np.array([0.1, 0.2]), np.array([1, 1]))
    with pytest.raises(ValueError, match="must be boolean"):
        controller.adapt_online(pred_alert=0, true_event=True)
