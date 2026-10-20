---
id: PROP-P5-ACK-AUDIT-TEST-FIXTURE
title: Align the audit acceptance fixture with the synthetic-only scoring contract
author: Codex
date: 2026-10-20
status: ACCEPTED
plan_version_impact: NONE
---

# Proposal: use an explicit synthetic patient in alert acknowledgement audit test

## Evidence

The latest PR #79 `backend-acceptance` run (`39441970404`, job
`118694236819`) fails `tests/acceptance_p5/test_api_security.py::test_writes_are_audited`:
the audit count is 7 after observations and remains 7 after the test's
conditional acknowledgement block. That block only calls acknowledge when an
alert exists.

The test creates a patient without `synthetic`; `PatientCreate.synthetic`
defaults to `False`. `ingest_single_observation_internal` therefore disables
unvalidated M3/K2 outputs and returns `abstain("clinical_validation_unavailable")`.
No alert is created for the non-synthetic test patient, so there is no
acknowledgement request to audit. This is the intended safety boundary, not a
missing audit write: the alert acknowledgement route records
`alert.acknowledged` when an alert is actually acknowledged.

## Proposed change

Change only the P5 acceptance fixture's patient creation request to explicitly
set `"synthetic": true`. This exercises creation, consent, observation,
synthetic research alert, acknowledgement, and its audit event under the
intended test profile. Keep the `PatientCreate` default false and retain the
non-synthetic abstention behavior. Do not weaken or remove the audit assertion.

## Acceptance and limits

## Owner disposition

Accepted in the PR #79 repair thread on 2026-10-20. The fixture is changed as
proposed; the default and product behavior remain unchanged. The targeted P5
acceptance test and full CI are required before closing this finding. This
corrects fixture provenance only; it does not validate M3/K2 clinically.
