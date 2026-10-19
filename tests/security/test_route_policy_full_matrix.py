"""Every route x every role, over HTTP, against the declared authorization policy.

``vigil_api.route_policy.ROUTE_POLICY`` declares who may call each route. This module calls **all** routes as
every role, as an unauthenticated caller and as an unknown role (``attacker``), with valid bodies where the
handler decides authorization after body validation, and fails on any disagreement. It also proves that the
coverage check itself can fail: a route added to an application without a policy entry is detected.

``tests/security/test_penetration_suite.py`` holds an older table (``OPENAPI_RBAC_POLICY``) and checks a sample of
eleven routes against it. The two tables differ on the routes listed in ``KNOWN_DIFFERENCES``; the evidence and
the request for a ruling are in ``docs/proposals/PROP-0004-penetration-suite-policy-table.md``. The older file is
not edited.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vigil_api.auth import create_access_token
from vigil_api.config import settings
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import ConsentRecord, Facility, Observation, Patient
from vigil_api.route_policy import ROUTE_POLICY

_SPEC = importlib.util.spec_from_file_location(
    "vigil_pen_suite_policy", Path(__file__).with_name("test_penetration_suite.py")
)
_PEN = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PEN)
PEN_TABLE: Dict[Tuple[str, str], Set[str]] = _PEN.OPENAPI_RBAC_POLICY

ROLES = ["clinician", "nurse_clerk", "quality_lead", "admin", "patient", "caregiver"]
HTTP_METHODS = ("get", "post", "put", "patch", "delete")

def openapi_routes(application: FastAPI) -> Set[Tuple[str, str]]:
    found: Set[Tuple[str, str]] = set()
    for path, ops in application.openapi()["paths"].items():
        for method in ops:
            if method.lower() in HTTP_METHODS:
                found.add((method.upper(), path))
    return found


def policy_coverage_problems(routes: Set[Tuple[str, str]], policy: Dict) -> List[str]:
    """Problems of policy/route parity; an empty list means every route has an entry and no entry is dead."""
    problems = [f"route without policy entry: {m} {p}" for m, p in sorted(routes - set(policy))]
    problems += [f"policy entry without route: {m} {p}" for m, p in sorted(set(policy) - routes)]
    return problems


@pytest.fixture
def env(tmp_path):
    orig = settings.REQUIRE_AUTH
    settings.REQUIRE_AUTH = True
    engine = create_engine(
        f"sqlite:///{tmp_path / 'matrix.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with Session(engine) as session:
        session.add(Facility(id="FAC-M", name="Matrix Hospital", code="MX-01", tier="tertiary"))
        session.add(Patient(id="PAT-M", facility_id="FAC-M", mrn="MRN-M", status="active", age=50))
        session.add(
            ConsentRecord(
                id="CNS-M",
                patient_id="PAT-M",
                consent_type="surveillance_monitoring",
                granted=True,
                granted_at=dt.datetime.now(dt.timezone.utc),
                scope="clinical_care,caregiver",
            )
        )
        session.add(
            Observation(
                id="OBS-M",
                patient_id="PAT-M",
                analyte_code="ca_15_3",
                value=22.0,
                unit="U/mL",
                specimen_collected_at=dt.datetime.now(dt.timezone.utc),
                result_received_at=dt.datetime.now(dt.timezone.utc),
                plausibility_status="plausible",
                raw_value=22.0,
                raw_unit="U/mL",
                status="valid",
                created_at=dt.datetime.now(dt.timezone.utc),
            )
        )
        session.commit()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client
    finally:
        settings.REQUIRE_AUTH = orig
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def headers_for(role: str) -> Dict[str, str]:
    if role == "unauthenticated":
        return {}
    token = create_access_token(
        subject="PAT-M" if role == "patient" else f"sub_{role}",
        role=role,
        patient_id="PAT-M" if role in ("patient", "caregiver") else None,
        expires_delta=dt.timedelta(hours=1),
    )
    return {"Authorization": f"Bearer {token}"}


def fill(path: str) -> str:
    values = {
        "id": "PAT-M",
        "obs_id": "OBS-M",
        "alert_id": "no-such-alert",
        "task_id": "no-such-task",
        "share_id": "no-such-share",
        "share_token": "cg_no-such-token",
        "draft_id": "no-such-draft",
    }
    out = path
    if path.startswith("/api/v1/fhir/Observation/"):
        return "/api/v1/fhir/Observation/OBS-M"
    for key, val in values.items():
        out = out.replace("{" + key + "}", val)
    assert "{" not in out, f"unfilled path parameter in {path}"
    return out


# Valid bodies for routes whose authorization is decided inside the handler (after body validation). With an
# empty body such a route answers 422 to every caller and the test would learn nothing about who is allowed.
VALID_BODIES: Dict[Tuple[str, str], dict] = {
    ("POST", "/api/v1/patients/"): {"age": 50},
    ("POST", "/api/v1/patients/{id}/baseline"): {
        "tumor_stage": 2, "er_status": True, "pr_status": True, "her2_status": False,
    },
    ("POST", "/api/v1/patients/{id}/labs"): {
        "alt_level": 25.0, "ast_level": 25.0, "creatinine": 0.9, "ca_15_3": 22.0, "wbc_count": 6.0,
    },
    ("POST", "/api/v1/patients/{id}/symptoms"): {"symptom_name": "fatigue", "severity": 1},
    ("POST", "/api/v1/patients/{id}/shares"): {
        "caregiver_name": "Matrix Caregiver", "relationship_type": "spouse", "scope": "view_summary",
    },
    ("POST", "/api/v1/patients/{id}/second-look"): {"observation_id": "OBS-M"},
    ("POST", "/api/v1/patients/{id}/disclosure/request-release"): {},
    ("POST", "/api/v1/test-ladder/recommend"): {
        "organ": "liver",
        "prior": {"value": 0.15, "provenance": "matrix"},
        "facility_id": "TEMPLATE-TERTIARY",
    },
    ("POST", "/api/v1/patients/{id}/ocr-drafts"): {
        "filename": "report.png",
        "content_type": "image/png",
        "content_base64": (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        ),
    },
    ("POST", "/api/v1/patients/{id}/ocr-drafts/{draft_id}/confirm"): {
        "confirmed": True,
        "analyte_code": "ca_15_3",
        "value": 22.0,
        "unit": "U/mL",
        "specimen_collected_at": "2026-01-15T00:00:00Z",
    },
}


def call(client: TestClient, method: str, path: str, headers: Dict[str, str]):
    url = fill(path)
    body = VALID_BODIES.get((method, path), {})
    if method == "GET":
        return client.get(url, headers=headers)
    if method == "DELETE":
        return client.delete(url, headers=headers)
    if method == "PATCH":
        return client.patch(url, json=body, headers=headers)
    return client.post(url, json=body, headers=headers)


# Where the older penetration-suite table disagrees with the declared policy (see PROP-0004). Each key is a
# route; the set is exactly the symmetric difference of the two role sets. A new disagreement fails the test.
KNOWN_DIFFERENCES = {
    ("GET", "/api/v1/alerts/stream"),
    ("GET", "/api/v1/continuity/ledger"),
    ("GET", "/api/v1/fhir/Observation/{id}"),
    ("GET", "/api/v1/follow-up/reminders/receipts"),
    ("GET", "/api/v1/quality/audit/latest"),
    ("POST", "/api/v1/alerts/{alert_id}/acknowledge"),
    ("POST", "/api/v1/analytics/seed-demo-cohort"),
    ("POST", "/api/v1/follow-up/reminders/run"),
    ("POST", "/api/v1/follow-up/{task_id}/transition"),
}


def test_every_route_has_a_policy_entry_and_every_entry_a_route():
    assert policy_coverage_problems(openapi_routes(app), ROUTE_POLICY) == []


def test_coverage_check_fails_for_a_new_route_without_policy():
    """The check must be able to fail: add a route to a throw-away app and expect a reported problem."""
    probe = FastAPI()

    @probe.get("/api/v1/patients/")
    def known():  # pragma: no cover - never called
        return []

    @probe.post("/api/v1/new-unlisted-mutation")
    def unlisted():  # pragma: no cover - never called
        return {}

    problems = policy_coverage_problems(openapi_routes(probe), ROUTE_POLICY)
    assert "route without policy entry: POST /api/v1/new-unlisted-mutation" in problems
    assert any(p.startswith("policy entry without route:") for p in problems)


def test_differences_from_the_penetration_suite_table_are_exactly_the_recorded_ones():
    differing = {
        key
        for key in ROUTE_POLICY
        if key in PEN_TABLE and set(ROUTE_POLICY[key].roles) != PEN_TABLE[key]
    }
    assert differing == KNOWN_DIFFERENCES


def test_full_route_by_role_matrix(env):
    client = env
    violations: List[str] = []
    checked = 0
    for (method, path), policy in sorted(ROUTE_POLICY.items()):
        allowed = set(policy.roles)
        if "public" in allowed:
            reference = call(client, method, path, headers_for("unauthenticated")).status_code
            for role in ROLES:
                got = call(client, method, path, headers_for(role)).status_code
                checked += 1
                if got != reference:
                    violations.append(
                        f"{method} {path}: public route depends on role {role} ({got} vs {reference})"
                    )
            continue
        for role in ["unauthenticated", "attacker"] + ROLES:
            got = call(client, method, path, headers_for(role)).status_code
            checked += 1
            if role in ("unauthenticated", "attacker"):
                if got not in (401, 403):
                    violations.append(f"{method} {path}: {role} got {got}")
            elif role not in allowed:
                if got != 403:
                    violations.append(f"{method} {path}: role {role} not allowed by policy but got {got}")
            elif got in (401, 403):
                violations.append(f"{method} {path}: role {role} allowed by policy but got {got}")
    assert checked > 400, f"suspiciously few checks ran: {checked}"
    assert violations == [], "\n".join(violations)
