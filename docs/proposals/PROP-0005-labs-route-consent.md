---
id: PROP-0005
title: A Phase 5 acceptance test requires POST /patients/{id}/labs to ingest for a patient without consent
author: Executor (final-build Tier 1)
date: 2026-10-18
status: DRAFT
plan_version_impact: NONE (acceptance-test fixture; safety review)
---

# PROP-0005: `/labs` consent check versus `tests/acceptance_p5`

## Evidence
- `POST /api/v1/patients/{id}/observations` calls `verify_patient_consent` and answers 403 for a patient with no active consent (`apps/api/tests/test_labs_consent_gap.py::test_control_observations_route_refuses_a_patient_without_consent`). The legacy `POST /api/v1/patients/{id}/labs` does not call it, so the same draw is ingested, scored and may raise an alert for a patient who never consented or who withdrew consent. Hazard H21 says consent is verified "on all clinical routes"; for this route that was not true before this work and is still not true.
- I added `verify_patient_consent` to `/labs` during Tier 1. It made `tests/acceptance_p5/test_api_security.py::test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline` fail (`VIGIL_ACCEPT_P5=1 uv run pytest tests/acceptance_p5`: `legacy /labs accepted a CA 15-3 of 500 and created nothing: {'status': 403, 'obs': 0, ...}`). That test creates a patient with `POST /patients/` (which records no consent), posts a lab draw as `nurse_clerk`, and requires either removal of the route (404/405/410) or an ingested observation with an alert or task and an audit event.
- The test's intent (no write path may swallow a surprising result) is not in conflict with consent: its fixture simply never grants consent because `/labs` never asked for it.

## What I did
The consent check on `/labs` is **not** enforced: I reverted it so the acceptance suite stays as the overseer wrote it, and left a comment at the route. The role gate on `/labs` (clinician, nurse_clerk, admin) stays. `apps/api/tests/test_labs_consent_gap.py` pins the gap: a passing control and two `xfail(strict=True)` tests (no consent; consent withdrawn) that state the required behaviour. `docs/safety/HAZARD_LOG.md` H24 records it as OPEN.

## Request (any one closes it)
1. Amend the acceptance test so its patient is consented first (preferred: the intent is unchanged), then add `verify_patient_consent` back to `submit_lab_result` and remove the two `xfail` markers; or
2. Remove the legacy `/labs` route altogether (the test accepts 404/405/410) and migrate its callers (`apps/api/tests/test_api_endpoints.py`, `test_e2e_simulation.py`, `test_phase5b_platform.py`, the web app); or
3. Rule that unconsented draws on `/labs` are acceptable (I would not, given H21).

Until one of these lands, do not describe consent enforcement as covering all clinical write routes.
