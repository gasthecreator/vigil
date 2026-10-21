"""M1's unsupported historical predictions remain fail closed."""

import pandas as pd
import pytest
from vigil_ml.organ_susceptibility import BaselineOrganSusceptibilityModelM1


def test_m1_prediction_is_quarantined_for_any_input():
    model = BaselineOrganSusceptibilityModelM1()
    for subtype in ("TNBC", "HR+/HER2-", "unrecognized"):
        with pytest.raises(RuntimeError, match="quarantined"):
            model.predict_susceptibility(subtype=subtype)


def test_m1_cohort_prediction_is_quarantined():
    cohort = pd.DataFrame([{"patient_id": "PT-01", "subtype": "TNBC"}])
    with pytest.raises(RuntimeError, match="quarantined"):
        BaselineOrganSusceptibilityModelM1().predict_cohort_dataframe(cohort)
