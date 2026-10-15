"""
Tests for vigil_ml.organ_susceptibility: M1 Baseline Organ Susceptibility Model.
"""

import numpy as np
import pandas as pd
from vigil_ml.organ_susceptibility import (
    TARGET_ORGANS,
    BaselineOrganSusceptibilityModelM1,
)


def test_m1_organ_susceptibility_predictions():
    model = BaselineOrganSusceptibilityModelM1()

    # 1. Luminal (HR+/HER2-): Predominant bone tropism (E12)
    pred_luminal = model.predict_susceptibility(subtype="HR+/HER2-", stage="Stage II", age=50.0)
    assert set(pred_luminal.probabilities.keys()) == set(TARGET_ORGANS)
    assert np.isclose(sum(pred_luminal.probabilities.values()), 1.0, atol=1e-3)
    assert pred_luminal.probabilities["bone"] > 0.60
    assert pred_luminal.probabilities["bone"] > pred_luminal.probabilities["brain"]
    assert "E12" in pred_luminal.evidence_badge

    # 2. TNBC: Higher visceral/brain tropism than Luminal (E12)
    pred_tnbc = model.predict_susceptibility(subtype="TNBC", stage="Stage II", age=45.0)
    assert pred_tnbc.probabilities["brain"] > pred_luminal.probabilities["brain"]
    assert pred_tnbc.probabilities["lung"] > pred_luminal.probabilities["lung"]

    # 3. 95% Credible intervals validity
    for organ in TARGET_ORGANS:
        low, high = pred_luminal.credible_intervals_95[organ]
        assert 0.0 <= low < high <= 1.0
        assert low <= pred_luminal.probabilities[organ] <= high


def test_m1_cohort_dataframe_prediction():
    model = BaselineOrganSusceptibilityModelM1()
    cohort_df = pd.DataFrame(
        [
            {"patient_id": "PT-01", "subtype": "TNBC", "stage": "Stage III", "age": 42.0},
            {"patient_id": "PT-02", "subtype": "HR+/HER2-", "stage": "Stage I", "age": 58.0},
        ]
    )

    preds_df = model.predict_cohort_dataframe(cohort_df)
    assert len(preds_df) == 2
    assert "prob_bone" in preds_df.columns
    assert "prob_liver" in preds_df.columns
    assert "prob_brain" in preds_df.columns
    assert "evidence_badge" in preds_df.columns
