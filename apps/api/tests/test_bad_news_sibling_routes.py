"""H17 (premature disclosure of bad news) on every route a patient or caregiver token can reach.

``tests/acceptance_p11`` proves the gate on the explainer routes. A safety gate enforced on one route is not an
invariant: this module drives the same state (an escalate-level result, disclosure locked) and calls every
sibling route that returns model output as the patient and as a caregiver, over HTTP, before and after a
clinician releases the result.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session
from vigil_api.models.patient import RiskInference

ESCALATE_MARKERS = ("escalate", "biomarker_spike", "high")


def _escalated_patient(env, mrn: str, legacy: bool = False) -> str:
    pid = env.create_patient(mrn)
    clin = env.headers("clinician")
    base = datetime.now(timezone.utc) - timedelta(days=60)
    values = [20.1, 20.4, 19.8, 20.2, 21.0, 80.0, 95.0]
    for i, value in enumerate(values):
        res = env.client.post(
            f"/api/v1/patients/{pid}/observations",
            json={
                "analyte_code": "ca_15_3",
                "value": value,
                "unit": "U/mL",
                "specimen_collected_at": (base + timedelta(days=7 * i)).isoformat(),
            },
            headers=clin,
        )
        assert res.status_code == 201, res.text
    last = res.json()
    assert last["adjudicated_action"] == "escalate", "setup must produce an escalate-level result"
    if legacy:
        res = env.client.post(
            f"/api/v1/patients/{pid}/labs",
            json={"alt_level": 400.0, "ast_level": 380.0, "creatinine": 2.5, "ca_15_3": 900.0, "wbc_count": 25.0},
            headers=clin,
        )
        assert res.status_code == 200, res.text
        assert res.json()["triage_flag"] is None
        # Seed a pre-quarantine row to verify it remains a conservative
        # disclosure hold while never being returned as a validated score.
        with Session(env.engine) as session:
            session.add(
                RiskInference(
                    patient_id=pid,
                    lab_result_id=res.json()["lab_result_id"],
                    calculated_metastasis_risk=0.99,
                    triage_flag=True,
                    justification_text="historical quarantined output",
                )
            )
            session.commit()
    return pid


def _patient_routes(pid: str):
    return [
        f"/api/v1/patients/{pid}",
        f"/api/v1/patients/{pid}/risk-history",
        f"/api/v1/patients/{pid}/trajectory",
        f"/api/v1/patients/{pid}/observations",
        f"/api/v1/alerts/stream?patient_id={pid}",
    ]


def _leaks(response, clinician_note: str) -> bool:
    if response.status_code != 200:
        return False
    text = response.text
    if clinician_note and clinician_note in text:
        return True
    try:
        body = json.loads(text)
    except ValueError:
        body = None
    if isinstance(body, dict) and body.get("latest_risk") is not None:
        return True
    if isinstance(body, list) and body and isinstance(body[0], dict) and "quality_flags" in body[0]:
        return any(item.get("quality_flags") for item in body)
    if isinstance(body, list) and body:
        return True
    return any(marker in text for marker in ("escalate", "biomarker_spike", "sequential_divergence"))


@pytest.mark.parametrize("role", ["patient", "caregiver"])
@pytest.mark.parametrize("legacy", [False, True])
def test_locked_bad_news_is_withheld_on_every_sibling_route(api_env, role, legacy):
    env = api_env
    pid = _escalated_patient(env, f"MRN-H17-{role}-{legacy}", legacy=legacy)
    clin = env.headers("clinician")
    note = ""
    history = env.client.get(f"/api/v1/patients/{pid}/risk-history", headers=clin).json()
    note = next(a["clinical_note"] for a in history if a["adjudicated_action"] == "escalate")
    assert note

    headers = env.headers(role, subject=pid, patient_id=pid)
    leaking = []
    for url in _patient_routes(pid):
        res = env.client.get(url, headers=headers)
        if _leaks(res, note):
            leaking.append(f"{role} GET {url} -> {res.status_code}")
    assert leaking == [], "bad news reached a patient-facing route before release:\n" + "\n".join(leaking)

    # Clinical staff keep full access while the result is locked for the patient.
    for staff in ("clinician", "nurse_clerk", "quality_lead", "admin"):
        res = env.client.get(f"/api/v1/patients/{pid}/risk-history", headers=env.headers(staff))
        assert res.status_code == 200 and note in res.text

    # Release is clinician/admin-only, and the patient routes open afterwards.
    nurse = env.client.post(
        f"/api/v1/patients/{pid}/disclosure/unlock", json={"reason": "x"}, headers=env.headers("nurse_clerk")
    )
    assert nurse.status_code == 403
    still = [u for u in _patient_routes(pid) if _leaks(env.client.get(u, headers=headers), note)]
    assert still == []
    release = env.client.post(
        f"/api/v1/patients/{pid}/disclosure/unlock", json={"reason": "clinician release"}, headers=clin
    )
    assert release.status_code == 200, release.text
    after = env.client.get(f"/api/v1/patients/{pid}/risk-history", headers=headers)
    assert after.status_code == 200 and note in after.text


def test_patient_without_escalation_is_not_withheld(api_env):
    env = api_env
    pid = env.create_patient("MRN-H17-calm")
    clin = env.headers("clinician")
    for i, value in enumerate([20.1, 20.4, 19.8]):
        env.client.post(
            f"/api/v1/patients/{pid}/observations",
            json={"analyte_code": "ca_15_3", "value": value, "unit": "U/mL"},
            headers=clin,
        )
    res = env.client.get(f"/api/v1/patients/{pid}/risk-history", headers=env.headers("patient", subject=pid, patient_id=pid))
    assert res.status_code == 200
