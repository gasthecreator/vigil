"""Authorization policy table: who may call each route, and what silent mode does to it.

This table is *declared intent*, reviewed by people. It is not generated from the code: a generated table would
agree with the code by construction and could not catch a route that is too open. ``tests/security/
test_route_policy_full_matrix.py`` calls every route as every role over HTTP and fails on any disagreement,
and fails when a route exists without an entry here (or an entry without a route).

``roles``: roles that may pass the route's authorization (the role gate plus, for patient-scoped routes,
the consent and ownership checks that follow it). ``"public"`` routes take no bearer token (companion share
routes authenticate with their own revocable share token). ``silent``: what silent mode does:
``diverts`` (model outputs go to the shadow store and are withheld from the response), ``blocked`` (HTTP 409:
the response is itself a model output), ``none``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Tuple

ALL = frozenset({"clinician", "nurse_clerk", "quality_lead", "admin", "patient", "caregiver"})
CLIN4 = frozenset({"clinician", "nurse_clerk", "quality_lead", "admin"})
WRITERS = frozenset({"clinician", "nurse_clerk", "admin"})
PUBLIC: FrozenSet[str] = frozenset({"public"})


@dataclass(frozen=True)
class RoutePolicy:
    roles: FrozenSet[str]
    silent: str = "none"
    note: str = ""


def _r(*roles: str) -> FrozenSet[str]:
    return frozenset(roles)


P = "/api/v1/patients"
ROUTE_POLICY: Dict[Tuple[str, str], RoutePolicy] = {
    # Public: liveness, root, share-token routes
    ("GET", "/"): RoutePolicy(PUBLIC),
    ("GET", "/health"): RoutePolicy(PUBLIC),
    ("GET", "/live"): RoutePolicy(PUBLIC, note="liveness probe"),
    ("GET", "/ready"): RoutePolicy(PUBLIC, note="readiness probe; no dependency detail"),
    ("GET", "/metrics"): RoutePolicy(PUBLIC, note="not a user route: bearer VIGIL_METRICS_TOKEN, 403 when unset"),
    ("GET", "/api/v1/companion/share/{share_token}"): RoutePolicy(PUBLIC, note="share token"),
    ("GET", "/api/v1/companion/share/{share_token}/observations/{obs_id}/explainer"): RoutePolicy(PUBLIC, note="share token"),
    ("POST", "/api/v1/companion/share/{share_token}/disclosure/request-release"): RoutePolicy(PUBLIC, note="share token"),
    ("POST", "/api/v1/companion/share/{share_token}/symptoms"): RoutePolicy(PUBLIC, note="share token"),
    # Patients
    ("POST", f"{P}/"): RoutePolicy(WRITERS, note="registration is a clinical-staff act"),
    ("GET", f"{P}/"): RoutePolicy(CLIN4),
    ("GET", f"{P}/triage"): RoutePolicy(CLIN4),
    ("GET", f"{P}/{{id}}"): RoutePolicy(ALL, note="consent- and ownership-gated"),
    ("PATCH", f"{P}/{{id}}"): RoutePolicy(_r("clinician", "admin")),
    ("POST", f"{P}/rotate-keys"): RoutePolicy(_r("admin")),
    ("POST", f"{P}/{{id}}/baseline"): RoutePolicy(WRITERS, silent="blocked", note="returns a model output"),
    ("POST", f"{P}/{{id}}/labs"): RoutePolicy(WRITERS, silent="diverts", note="NO consent check: H25, PROP-0005"),
    ("GET", f"{P}/{{id}}/trajectory"): RoutePolicy(ALL, note="consent-gated; H17 withholds for patient/caregiver"),
    ("POST", f"{P}/{{id}}/simulate"): RoutePolicy(_r("clinician", "admin"), silent="blocked", note="returns a model output"),
    ("POST", f"{P}/{{id}}/observations"): RoutePolicy(WRITERS, silent="diverts"),
    ("GET", f"{P}/{{id}}/observations"): RoutePolicy(ALL),
    ("GET", f"{P}/{{id}}/risk-history"): RoutePolicy(ALL, note="consent-gated; H17 withholds for patient/caregiver"),
    ("POST", f"{P}/{{id}}/consent"): RoutePolicy(WRITERS),
    ("POST", f"{P}/{{id}}/symptoms"): RoutePolicy(_r("patient", "caregiver", "nurse_clerk", "clinician", "admin")),
    ("GET", f"{P}/{{id}}/symptoms"): RoutePolicy(ALL),
    ("POST", f"{P}/{{id}}/shares"): RoutePolicy(_r("patient", "clinician", "admin"), note="caregivers cannot mint further access"),
    ("GET", f"{P}/{{id}}/shares"): RoutePolicy(_r("patient", "clinician", "admin")),
    ("DELETE", f"{P}/{{id}}/shares/{{share_id}}"): RoutePolicy(_r("patient", "clinician", "admin")),
    ("POST", f"{P}/{{id}}/second-look"): RoutePolicy(_r("patient", "caregiver", "clinician", "admin")),
    ("POST", f"{P}/{{id}}/disclosure/unlock"): RoutePolicy(_r("clinician", "admin")),
    ("POST", f"{P}/{{id}}/disclosure/request-release"): RoutePolicy(_r("patient", "caregiver", "clinician", "admin")),
    ("POST", f"{P}/{{id}}/disclosure/lock"): RoutePolicy(_r("clinician", "admin")),
    ("GET", f"{P}/{{id}}/observations/{{obs_id}}/explainer"): RoutePolicy(ALL, note="H17 gate"),
    ("POST", f"{P}/{{id}}/ocr-drafts"): RoutePolicy(
        _r("patient", "caregiver", "clinician", "nurse_clerk", "admin"),
        note="draft only; not an observation",
    ),
    ("GET", f"{P}/{{id}}/ocr-drafts"): RoutePolicy(ALL),
    ("GET", f"{P}/{{id}}/ocr-drafts/{{draft_id}}"): RoutePolicy(ALL),
    ("POST", f"{P}/{{id}}/ocr-drafts/{{draft_id}}/confirm"): RoutePolicy(
        WRITERS, silent="diverts", note="human-posted values only; suggestions ignored"
    ),
    ("POST", f"{P}/{{id}}/ocr-drafts/{{draft_id}}/reject"): RoutePolicy(
        _r("patient", "caregiver", "clinician", "nurse_clerk", "admin")
    ),
    # Continuity (M7)
    ("GET", "/api/v1/continuity/machines"): RoutePolicy(CLIN4),
    ("POST", "/api/v1/continuity/machines/{id}/status"): RoutePolicy(_r("clinician", "admin")),
    ("GET", "/api/v1/continuity/courses"): RoutePolicy(CLIN4),
    ("POST", "/api/v1/continuity/courses"): RoutePolicy(_r("clinician", "admin")),
    ("POST", "/api/v1/continuity/schedule/solve"): RoutePolicy(_r("clinician", "quality_lead", "admin")),
    ("POST", "/api/v1/continuity/schedule/confirm"): RoutePolicy(_r("clinician", "admin")),
    ("GET", "/api/v1/continuity/ledger"): RoutePolicy(CLIN4),
    ("GET", "/api/v1/continuity/patients/{id}/delay-notice"): RoutePolicy(ALL),
    # Ingestion
    ("POST", "/api/v1/observations/batch-import"): RoutePolicy(WRITERS, silent="diverts"),
    ("GET", "/api/v1/fhir/Observation/{id}"): RoutePolicy(ALL, note="consent-gated export of raw data"),
    ("POST", "/api/v1/fhir/Observation"): RoutePolicy(WRITERS, silent="diverts"),
    ("POST", "/api/v1/hl7/oru-r01"): RoutePolicy(WRITERS, silent="diverts"),
    ("POST", "/api/v1/sync/batch"): RoutePolicy(WRITERS, silent="diverts"),
    # Alerts and follow-up
    ("GET", "/api/v1/alerts/"): RoutePolicy(CLIN4),
    ("POST", "/api/v1/alerts/{alert_id}/acknowledge"): RoutePolicy(_r("clinician", "quality_lead"), note="admin cannot acknowledge clinical alerts"),
    ("GET", "/api/v1/alerts/stream"): RoutePolicy(ALL, note="patient/caregiver need patient_id + consent; H17 withholds"),
    ("GET", "/api/v1/follow-up/outreach"): RoutePolicy(CLIN4),
    ("POST", "/api/v1/follow-up/{task_id}/transition"): RoutePolicy(_r("clinician", "nurse_clerk", "quality_lead")),
    ("POST", "/api/v1/follow-up/reminders/run"): RoutePolicy(WRITERS),
    ("GET", "/api/v1/follow-up/reminders/receipts"): RoutePolicy(WRITERS),
    # Resource-aware test ladder (M4): stateless decision aid, a model output, so blocked in silent mode
    ("POST", "/api/v1/test-ladder/recommend"): RoutePolicy(_r("clinician", "admin"), silent="blocked", note="stateless; no patient id"),
    ("GET", "/api/v1/test-ladder/facilities"): RoutePolicy(_r("clinician", "admin"), note="registry listing, not a model output"),
    # Audit, analytics, quality
    ("GET", "/api/v1/audit/verify"): RoutePolicy(_r("admin", "clinician", "quality_lead")),
    ("GET", "/api/v1/audit/events"): RoutePolicy(_r("admin", "quality_lead")),
    ("GET", "/api/v1/analytics/cohort"): RoutePolicy(_r("admin", "clinician", "quality_lead")),
    ("POST", "/api/v1/analytics/seed-demo-cohort"): RoutePolicy(_r("admin"), silent="blocked", note="local profile only"),
    ("POST", "/api/v1/quality/audit"): RoutePolicy(_r("admin", "quality_lead")),
    ("GET", "/api/v1/quality/audit/latest"): RoutePolicy(_r("admin", "quality_lead")),
}
