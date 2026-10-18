"""POST /patients/{id}/labs does not check patient consent (known gap, PROP-0005).

`/observations` refuses a patient without active consent (HTTP 403). `/labs` was written before the consent
engine, and the overseer-owned `tests/acceptance_p5/test_api_security.py::
test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline` posts to it for a patient that has no consent
record and requires the draw to be ingested. Enforcing consent on `/labs` makes that test fail, and acceptance
tests are read-only for the executor, so the check is NOT enforced and the gap is pinned here:

* the control test passes today (the sibling route refuses);
* the two `xfail(strict=True)` tests state the required behaviour. They fail today; when the gap is closed
  they pass and strict mode turns the unexpected pass into a failure that says to remove the marker.
"""

from __future__ import annotations

import pytest

LAB_BODY = {"alt_level": 25.0, "ast_level": 25.0, "creatinine": 0.9, "ca_15_3": 22.0, "wbc_count": 6.0}
OBS_BODY = {"analyte_code": "ca_15_3", "value": 22.0, "unit": "U/mL"}


def test_control_observations_route_refuses_a_patient_without_consent(api_env):
    pid = api_env.create_patient("MRN-GAP-0", consent=False)
    res = api_env.client.post(
        f"/api/v1/patients/{pid}/observations", json=OBS_BODY, headers=api_env.headers("clinician")
    )
    assert res.status_code == 403, res.text


@pytest.mark.xfail(
    strict=True, reason="PROP-0005: /labs does not call verify_patient_consent (acceptance_p5 conflict)"
)
def test_labs_route_refuses_a_patient_without_consent(api_env):
    pid = api_env.create_patient("MRN-GAP-1", consent=False)
    res = api_env.client.post(
        f"/api/v1/patients/{pid}/labs", json=LAB_BODY, headers=api_env.headers("clinician")
    )
    assert res.status_code == 403, res.text


@pytest.mark.xfail(
    strict=True, reason="PROP-0005: /labs does not call verify_patient_consent (acceptance_p5 conflict)"
)
def test_labs_route_refuses_a_patient_who_withdrew_consent(api_env):
    pid = api_env.create_patient("MRN-GAP-2", consent=True)
    w = api_env.client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"consent_type": "surveillance_monitoring", "granted": False, "scope": "full"},
        headers=api_env.headers("admin"),
    )
    assert w.status_code == 201, w.text
    res = api_env.client.post(
        f"/api/v1/patients/{pid}/labs", json=LAB_BODY, headers=api_env.headers("clinician")
    )
    assert res.status_code == 403, res.text
