import numpy as np
import pytest
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
