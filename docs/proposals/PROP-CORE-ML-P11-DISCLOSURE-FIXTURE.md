---
id: PROP-CORE-ML-P11-DISCLOSURE-FIXTURE
title: Reconcile P11 disclosure acceptance fixture with explicit synthetic provenance
author: Q-7 executor
date: 2026-10-20
status: UNDER REVIEW
plan_version_impact: MASTER_PLAN §5.3 and §14 P11
---

# Proposal: reconcile the P11 disclosure acceptance fixture with synthetic provenance

## Observed conflict

The frozen P11 acceptance test creates a patient without a `synthetic` field and then expects an escalated model explanation to appear after a clinician disclosure release. The Q-7 change makes patient provenance default to `synthetic=false`. For such a patient, the unvalidated M3/K2 research score is suppressed; the explanation endpoint returns an abstention with no score-derived escalation before and after release. The clinician release is persisted and returns HTTP 200, while a nurse request returns HTTP 403. Therefore the test's final assertion cannot establish release persistence using the expected word `escalate` for this fixture.

## Evidence

- Unchanged overseer-owned test: `tests/acceptance_p11/test_p11_contract.py::test_bad_news_is_withheld_by_the_server_until_a_clinician_releases_it`.
- Reproduction on Q-7: the test fails only at `release did not persist for both routes`; route responses before and after release contain `verdict=abstain`, `synthetic=false`, and an insufficient-history explanation. Nurse is denied (403) and clinician release succeeds (200).
- Current relevant behavior: `PatientCreate` defaults to non-synthetic; M3/K2 score routes remain research-only for non-synthetic patients. Changing that default or restoring score generation to satisfy this assertion would falsify provenance or expose unvalidated scores.
- The latest PR #79 CI run (`39417463523`, claims-and-governance job `118609860052`, merged test commit `9bce4ff14d7da866635543010bb1411b32bb5082`) reproduces the same final assertion failure after 67 cited safety tests pass. This confirms that the verifier failure is the frozen P11 fixture mismatch, not a newly failing hazard-link or claims-policy check.

## Requested disposition

Keep the acceptance test unchanged until overseer review. Revise its fixture and assertion so it tests the intended disclosure contract with explicit provenance and a persisted high/escalate result. Options include marking the synthetic fixture explicitly and verifying its result is withheld until release, or directly seeding a valid persisted sensitive result so the disclosure gate is tested independently of model inference. Keep the nurse-denial and clinician-only persistence assertions.

## Boundary

This proposal does not claim P11 disclosure safety is fully verified for real clinical outputs, and does not authorize weakening the disclosure gate, changing provenance defaults, or editing the acceptance test. Until an overseer-owned fixture is corrected, the P11 gate remains unresolved on this branch.
