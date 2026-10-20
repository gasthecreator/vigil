import numpy as np
import pytest
from vigil_ml.conformal_k8 import ProductionEnsembleK8


def test_historical_k8_ensemble_fails_closed():
    model = ProductionEnsembleK8()
    with pytest.raises(RuntimeError, match="is quarantined"):
        model.fit(np.zeros((2, 3)), np.array([0, 1]))
    with pytest.raises(RuntimeError, match="is quarantined"):
        model.predict_risk(np.zeros((2, 3)))
