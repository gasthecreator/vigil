---
id: PROP-0004
title: The authorization table in tests/security/test_penetration_suite.py disagrees with the running server on nine routes
author: Executor (final-build Tier 1)
date: 2026-10-18
status: DRAFT
plan_version_impact: NONE (test maintenance; safety review)
---

# PROP-0004: Penetration-suite policy table is inaccurate on nine routes

## Evidence
`OPENAPI_RBAC_POLICY` in `tests/security/test_penetration_suite.py` is checked for route coverage over all routes but for role behaviour on eleven routes only (`test_openapi_authorization_matrix`, "Sample test representative subset"). `tests/security/test_route_policy_full_matrix.py` calls every route as every role. The older table and the running server disagree on the nine routes in `KNOWN_DIFFERENCES` of that file:

| Route | Older table allows | Server allows (and why that is the better reading) |
|---|---|---|
| `GET /api/v1/alerts/stream` | clinician, nurse_clerk, quality_lead, admin | plus patient, caregiver. The route has explicit patient/caregiver handling (patient_id required, consent checked) and `apps/api/tests/test_alert_stream.py::test_sse_stream_patient_role_restrictions`. Bad news is now withheld on it (H17). |
| `GET /api/v1/continuity/ledger` | clinician, quality_lead, admin | plus nurse_clerk (code: `require_roles` with four roles). Unchanged; worth a ruling. |
| `GET /api/v1/fhir/Observation/{id}` | clinician, nurse_clerk, quality_lead, admin | plus patient, caregiver (own record, consent-gated export of raw data). |
| `GET /api/v1/follow-up/reminders/receipts` | adds quality_lead | admin, clinician, nurse_clerk only. |
| `GET /api/v1/quality/audit/latest` | adds clinician | admin, quality_lead only. |
| `POST /api/v1/alerts/{alert_id}/acknowledge` | clinician, admin | clinician, quality_lead. `apps/api/tests/test_auth_rbac_consent.py` asserts quality_lead 200 and admin 403. |
| `POST /api/v1/analytics/seed-demo-cohort` | clinician, quality_lead, admin | admin only (and local profile only), per the docstring. |
| `POST /api/v1/follow-up/reminders/run` | clinician, admin | plus nurse_clerk. |
| `POST /api/v1/follow-up/{task_id}/transition` | clinician, nurse_clerk, admin | clinician, nurse_clerk, quality_lead (admin excluded). |

## Request
Rule on each row: which reading is intended. If the server is right, correct the older table (the declared table `vigil_api/route_policy.py` already follows the server). If the older table is right, the server needs a change and a test already fails to show it (set the row in `ROUTE_POLICY` to the older roles and run `tests/security/test_route_policy_full_matrix.py`).

## What was done meanwhile
Nothing in the older file was edited. `ROUTE_POLICY` follows the server for these nine routes; `test_differences_from_the_penetration_suite_table_are_exactly_the_recorded_ones` fails if a new disagreement appears or one of these is resolved without updating the record.
