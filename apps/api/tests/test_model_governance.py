from sqlalchemy import update
from vigil_api.governance_attestation import attest_monitor_report
from vigil_api.models.v2 import ModelGovernanceRecord

URL = "/api/v1/models/governance"
EVALUATION_URL = f"{URL}/candidate-evaluations"


def report(breach=True):
    return attest_monitor_report({
        "source": "shadow store only",
        "breach": breach,
        "sections": {"alarm_rate": {"status": "BREACH" if breach else "OK"}},
        "data": {"patients": 12},
    })


def payload(**overrides):
    value = {
        "monitor_report": report(),
        "candidate_id": "K2-SHADOW-1",
        "max_alert_rate_increase": 0.25,
        "series": [
            {"observations": [{"day": 0, "value": 20}, {"day": 30, "value": 21},
                               {"day": 60, "value": 19}, {"day": 90, "value": 20}]},
            {"observations": [{"day": 0, "value": 10}, {"day": 30, "value": 11},
                               {"day": 60, "value": 11}, {"day": 90, "value": 12}]},
        ],
    }
    value.update(overrides)
    return value


def test_governance_is_admin_only_and_requires_real_breach(api_env):
    assert api_env.client.get(f"{URL}/status", headers=api_env.headers("clinician")).status_code == 403
    assert api_env.client.post(EVALUATION_URL, json=payload(), headers=api_env.headers("clinician")).status_code == 403
    invalid = api_env.client.post(
        EVALUATION_URL, json=payload(monitor_report=report(False)), headers=api_env.headers("admin")
    )
    assert invalid.status_code == 409
    tampered = report()
    tampered["sections"]["alarm_rate"]["status"] = "OK"
    invalid_signature = api_env.client.post(
        EVALUATION_URL, json=payload(monitor_report=tampered), headers=api_env.headers("admin")
    )
    assert invalid_signature.status_code == 409


def test_shadow_requires_criterion_and_separate_human_approval_then_promotes_and_rolls_back(api_env):
    start = api_env.client.post(EVALUATION_URL, json=payload(), headers=api_env.headers("admin", "evaluator"))
    assert start.status_code == 201, start.text
    result = start.json()
    assert result["patient_level_outputs_stored"] is False
    assert result["clinician_routes_unchanged"] is True
    assert "patient_id" not in str(result)
    evaluation_id = result["evaluation_id"]
    replay = api_env.client.post(EVALUATION_URL, json=payload(), headers=api_env.headers("admin", "second-evaluator"))
    assert replay.status_code == 409
    promote_body = {"evaluation_id": evaluation_id}
    assert api_env.client.post(f"{URL}/promote", json=promote_body, headers=api_env.headers("admin")).status_code == 409
    assert api_env.client.post(f"{URL}/approvals", json=promote_body, headers=api_env.headers("admin", "evaluator")).status_code == 409
    approved = api_env.client.post(f"{URL}/approvals", json=promote_body, headers=api_env.headers("admin", "approver"))
    assert approved.status_code == 201, approved.text
    promoted = api_env.client.post(f"{URL}/promote", json=promote_body, headers=api_env.headers("admin", "promoter"))
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["active_candidate"] == "K2-SHADOW-1"
    assert api_env.client.post(f"{URL}/promote", json=promote_body, headers=api_env.headers("admin", "replayer")).status_code == 409
    rolled_back = api_env.client.post(
        f"{URL}/rollback", json={"reason": "Operator observed a regression"}, headers=api_env.headers("admin", "rollbacker")
    )
    assert rolled_back.status_code == 200, rolled_back.text
    status = api_env.client.get(f"{URL}/status", headers=api_env.headers("admin")).json()
    assert status["chain_valid"] is True
    assert status["active_candidate"] == "K2"
    assert [r["event_type"] for r in status["records"]] == ["shadow_evaluated", "human_approved", "promoted", "rolled_back"]


def test_tampered_hash_chained_record_is_refused(api_env):
    start = api_env.client.post(EVALUATION_URL, json=payload(), headers=api_env.headers("admin"))
    assert start.status_code == 201, start.text
    with api_env.engine.begin() as connection:
        connection.execute(
            update(ModelGovernanceRecord.__table__).values(payload={"tampered": True})
        )
    response = api_env.client.get(f"{URL}/status", headers=api_env.headers("admin"))
    assert response.status_code == 409
    assert "chain failed verification" in response.json()["detail"]


def test_governance_transition_and_audit_event_roll_back_together(api_env, monkeypatch):
    from vigil_api.api.endpoints import governance

    def fail_audit(*_args, **_kwargs):
        raise ValueError("audit write failed")

    monkeypatch.setattr(governance, "record_audit_event", fail_audit)
    response = api_env.client.post(EVALUATION_URL, json=payload(), headers=api_env.headers("admin"))
    assert response.status_code == 409
    assert response.json()["detail"] == "audit write failed"
    status = api_env.client.get(f"{URL}/status", headers=api_env.headers("admin"))
    assert status.status_code == 200
    assert status.json()["records"] == []
