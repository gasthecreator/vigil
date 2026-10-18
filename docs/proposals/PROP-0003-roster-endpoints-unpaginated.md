---
id: PROP-0003
title: Roster endpoints return every patient (unpaginated) and the triage queue does not filter by consent or facility
author: Executor (final-build Tier 0)
date: 2026-10-18
status: DRAFT
plan_version_impact: NONE (MASTER_PLAN 9.5 budget interpretation; safety review)
---

# PROP-0003: Roster endpoints are unpaginated; triage queue scoping needs review

## 1. Problem Statement
(a) `GET /api/v1/patients/` and `GET /api/v1/patients/triage` return the whole roster in one response (`db.query(Patient).all()`), with no pagination. MASTER_PLAN 9.5 states "triage queue p95 < 400 ms" at 10^5 patients; a single response that serialises 10^5 items cannot be expected to meet that, and no test measures it.
(b) `get_triage_queue` (`apps/api/vigil_api/api/endpoints/patients.py`) is guarded by `require_roles(...)` only. In the code I read, it does not call `verify_patient_consent` / `has_active_consent` and does not filter by `facility_id`, whereas the patient list masks identifiers for patients without consent and single-patient reads call `verify_patient_consent`. I did not change this and I have not written a test of the intended behaviour, because the intended behaviour (is a risk score for a non-consenting or other-facility patient visible in the queue?) is a policy decision.

## 2. Evidence Base
Code reading of the two handlers (line numbers shift; search `def get_triage_queue`). Soak: with 200 patients throughput was 41.72 req/s against 157 req/s for 10 patients in comparable short runs (`/tmp` smoke run, not committed; the committed canonical soak is `reports/load/SOAK_TEST_HTTP_RESULTS.json`), consistent with per-request cost proportional to roster size.

## 3. Proposed Change
(a) Cursor pagination with a stable sort on the triage urgency key; a load test at 10^4 patients (10^5 only if it fits on this host) against the pagination parameters; the 9.5 row measured at the size it claims or restated by the overseer. (b) The overseer decides the policy; then a route-level test as every role, with forged facility ids, in `tests/security/`.

## 4. Considered Alternatives
- **Leave unpaginated, restate the budget for small clinics.** Pros: no API change. Cons: the budget text no longer matches the plan.

## 5. Evaluation & Verification Criteria
Security tests as every role against the chosen policy; load test at the stated scale with committed script-written results.

## 6. Kill / Rollback Criterion
If pagination breaks the e2e triage view or the contract tests, revert and file the failing case.

## 7. Impact on Master Plan
Possibly 9.5 wording; overseer-owned.
