"""M4 test ladder over HTTP (property P11 of docs/ml/M4-CONTRACT.md, plus forged bodies and silent mode)."""

from __future__ import annotations

import re
from datetime import date, timedelta

import pytest
from vigil_api.config import settings
from vigil_api.models.v2 import UserRole
from vigil_ml import m4_ladder

ALL_ROLES = [r.value for r in UserRole]
URL = "/api/v1/test-ladder/recommend"
ALLOWED = {"clinician", "admin"}
BANNED = re.compile(r"\b(ruled out|rule out|excluded|safe|normal|no cancer|negative means)\b", re.I)


def body(**over):
    b = {
        "organ": "liver",
        "prior": {"value": 0.15, "lo": 0.08, "hi": 0.25, "provenance": "test prior"},
        "facility_id": "TEMPLATE-TERTIARY",
    }
    b.update(over)
    return b


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


@pytest.mark.parametrize("role", ALL_ROLES)
def test_p11_only_clinician_and_admin_may_call(api_env, role):
    res = api_env.client.post(URL, json=body(), headers=api_env.headers(role))
    assert res.status_code == (200 if role in ALLOWED else 403), res.text
    fac = api_env.client.get("/api/v1/test-ladder/facilities", headers=api_env.headers(role))
    assert fac.status_code == (200 if role in ALLOWED else 403)


def test_p11_unauthenticated_and_forged_token_are_refused(api_env):
    assert api_env.client.post(URL, json=body()).status_code == 401
    bad = {"Authorization": "Bearer not-a-token"}
    assert api_env.client.post(URL, json=body(), headers=bad).status_code == 401
    assert api_env.client.get("/api/v1/test-ladder/facilities").status_code == 401


def test_p11_the_route_has_a_policy_entry():
    from vigil_api.route_policy import ROUTE_POLICY

    assert ("POST", URL) in ROUTE_POLICY
    assert set(ROUTE_POLICY[("POST", URL)].roles) == ALLOWED
    assert ROUTE_POLICY[("POST", URL)].silent == "blocked"


def test_response_equals_the_pure_engine_and_is_decision_support_only(api_env):
    as_of = date.today()
    res = api_env.client.post(URL, json=body(), headers=api_env.headers("clinician"))
    assert res.status_code == 200
    out = res.json()
    templates = m4_ladder.load_facility_templates()
    expected = m4_ladder.recommend(
        "liver",
        m4_ladder.Prior(0.15, 0.08, 0.25, "test prior"),
        templates["TEMPLATE-TERTIARY"],
        as_of,
        other_facilities=list(templates.values()),
    ).to_dict()
    assert out == {**expected, "as_of": as_of.isoformat()}
    assert out["negative_result_excludes_involvement"] is False
    assert out["illustrative_facility"] is True
    assert out["rungs"] and all(r["evidence_ids"] for r in out["rungs"])
    for s in strings(out):
        assert not BANNED.search(s), s


def test_forged_body_fields_cannot_change_the_negative_result_statement(api_env):
    forged = body(
        negative_result_excludes_involvement=True,
        outcome="ladder",
        rungs=[{"modality": "magic"}],
        illustrative_facility=False,
        notes=[],
    )
    out = api_env.client.post(URL, json=forged, headers=api_env.headers("clinician")).json()
    assert out["negative_result_excludes_involvement"] is False
    assert out["illustrative_facility"] is True
    assert all(r["modality"] != "magic" for r in out["rungs"])


def test_inline_facility_rows_fresh_and_stale_are_labelled(api_env):
    today = date.today()
    fac = {
        "facility_id": "SITE-A",
        "name": "A real site entered by the clinician",
        "tier": "secondary",
        "modalities": [
            {
                "modality": "ct",
                "available": True,
                "turnaround_days": 3,
                "price_band": 3,
                "distance_band": 1,
                "source": "phone call",
                "verified_on": today.isoformat(),
            },
            {
                "modality": "ultrasound",
                "available": True,
                "turnaround_days": 1,
                "price_band": 1,
                "distance_band": 1,
                "source": "old list",
                "verified_on": (today - timedelta(days=900)).isoformat(),
            },
        ],
    }
    res = api_env.client.post(
        URL, json=body(facility_id=None, facility=fac), headers=api_env.headers("admin")
    )
    assert res.status_code == 200, res.text
    out = res.json()
    conf = {r["modality"]: r["availability_confidence"] for r in out["rungs"]}
    assert conf == {"ct": "fresh", "ultrasound": "stale"}
    assert out["illustrative_facility"] is False
    stale = [r for r in out["rungs"] if r["modality"] == "ultrasound"][0]
    assert stale["confirm_availability"] is True


@pytest.mark.parametrize(
    "payload, status_code",
    [
        (body(facility_id=None), 422),  # neither facility spec
        (
            body(facility={"facility_id": "X", "name": "X", "tier": "t", "modalities": []}),
            422,
        ),  # both
        (body(facility_id="NOPE"), 404),
        (body(organ="ovary"), 422),
        (body(prior={"value": 1.2, "provenance": "x"}), 422),
        (body(prior={"value": 0.2, "provenance": ""}), 422),
        (body(prior={"value": 0.2, "lo": 0.3, "hi": 0.4, "provenance": "x"}), 422),
        (body(as_of=(date.today() + timedelta(days=1)).isoformat()), 422),
        (body(max_price_band=9), 422),
    ],
)
def test_invalid_requests_are_refused(api_env, payload, status_code):
    res = api_env.client.post(URL, json=payload, headers=api_env.headers("clinician"))
    assert res.status_code == status_code, res.text


def test_brain_is_reported_as_no_sourced_option_not_as_clear(api_env):
    out = api_env.client.post(
        URL, json=body(organ="brain"), headers=api_env.headers("clinician")
    ).json()
    assert out["outcome"] == "no_sourced_option"
    assert out["rungs"] == []
    assert any("not about the patient" in n for n in out["notes"])


def test_silent_mode_blocks_the_recommendation_but_not_the_registry_listing(api_env, monkeypatch):
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    res = api_env.client.post(URL, json=body(), headers=api_env.headers("clinician"))
    assert res.status_code == 409
    assert "rungs" not in res.text
    fac = api_env.client.get("/api/v1/test-ladder/facilities", headers=api_env.headers("clinician"))
    assert fac.status_code == 200
    assert all(f["illustrative"] for f in fac.json())
