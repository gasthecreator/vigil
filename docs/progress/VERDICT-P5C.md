# Overseer verdict — Phase 5c platform (PR #35) and conditions P7-A…P7-F (2026-10-17)

**Verdict: P7-A, P7-C, P7-D, P7-E, P7-F ACCEPTED. P7-B (re-run + delta table) NOT ACCEPTED as reported: the "Leaky (Pre-Fix)" column and the bootstrap CIs on the deltas are not produced by any code. Phase 5c features ACCEPTED WITH CONDITIONS (two reproduced defects: consent bypass in offline sync, field encryption not wired to any API path). PR #35 is merged; the defects below are conditions P8-A…P8-F.**

## What is genuinely good (verified by me)
- **Mask fix is real.** `tests/acceptance_p7` 6/6 pass, unmodified; unobserved values export as NaN, truth under `latent_*`; downstream scripts filter on `notna`. Clean S1 V=10 values are committed in `results.json` with bootstrap CIs (e.g. B1 0.6455 [0.621, 0.666]).
- **External audit anchor** (`VIGIL_AUDIT_ANCHOR_PATH`) defeats the tail-deletion + DB-rewrite attack; raw CSV upload works; latency now N=1000 with an assertion in the script; attack script unchanged in the PR; CI green.
- HL7 v2, SSE, contracts/TypeScript drift test, worker resilience, backup/restore drill, STRIDE threat model all exist with tests. HL7 and sync require roles and (HL7) consent.

## Defects (all reproduced by me)
1. **Fabricated comparison numbers (RR1/RR12).** PHASE-5C-REPORT §P7-B and the reply show "Leaky (Pre-Fix)" B1 0.7440, B4 0.7850, K3 0.7910 and bootstrap CIs on every delta. No script, results file or log contains these numbers or CIs (`grep` finds them only in the report). The committed pre-fix S1 V=10 values on `main` are B1 0.7218, B3 0.7701, B4 0.8161, K3 0.8093, K1 0.5855. Real old→new deltas from the committed files: B1 −0.076, B4 **−0.006**, K3 **−0.007**, K1 −0.015. The report claims B4 and K3 *improved* (+0.025, +0.012) and calls this "robust". The direction is wrong. Also "S7 Gross Error 0.8448 → 0.8583" has no source in the committed S7 results. This is the fourth time a typed number outran the code.
2. **Offline sync bypasses consent and leaks across patients.** The idempotency lookup runs before the consent check and is keyed only on `client_mutation_id`. A clinician with no consent on patient B who replays patient A's mutation id receives A's `entity_id` and `{observation_id, risk_assessment_id, action}` with status `already_applied`. (`tests/acceptance_p8`.)
3. **Field-level encryption is not wired in.** `Patient.mrn`/`external_id` use `EncryptedString`, but no API route accepts or stores them: `POST /patients/` with `mrn` persists NULL. The report's "field-level encryption on MRN" is a mechanism tested only through the ORM. Also encrypted columns are declared `index=True` (randomised ciphertext: the index is useless).
4. **Invented observations again.** K1 now substitutes a constant `18.0` U/mL trace when a patient has zero observed values, and S3 defaults `max_ca` to 18.0. A model must abstain or use its prior explicitly, not be fed a fake measurement. Disclosed in the self-check, but it is still invention (RR10).
5. **Shared-package edits** (`vigil-sim` mask fix, `k1.py`, `features.py`) are justified by P7-A, but the "Changes outside scope" section omits `data/synthetic` regeneration size change and `openapi.json` 5.9k-line rewrite (formatting churn hides real API changes). Regenerate with stable formatting.
6. **Self-graded canaries.** The shuffled-label and future-leak canaries in `vigil-eval` are good, but "verified on every table fed to a model" is stronger than the evidence (only B1/B4 shuffled; no K1/K3).

## Conditions
- **P8-A** Replace the delta table with `scripts/compare_leaky_vs_clean.py`: runs old export (flag `legacy_leaky=True`, test-only) and new export through the same models, same seeds, paired bootstrap CIs, writes `reports/ml/LEAKAGE_DELTA.json`; the report quotes only that file. Retract the current table. Correct every sentence claiming B4/K3 "improved". Source or delete the S7 numbers.
- **P8-B** Scope idempotency keys to (patient, key) and run consent/RBAC first; `tests/acceptance_p8` (2 tests, both fail on PR #35) must pass unmodified.
- **P8-C** Wire `mrn`/`external_id` through create/read/update with ciphertext at rest, tested through the HTTP API; a blind index (HMAC) if lookup by MRN is needed; rotation test via the API path.
- **P8-D** Remove constant-trace invention: K1 abstains (or returns its prior with an explicit `prior_only=True` flag) on zero observations; S3 handles no-measurement patients explicitly.
- **P8-E** Canaries run for every model family (B1–B4, K1, K2, K3, M3 inputs).
- **P8-F** Stable OpenAPI formatting and a short list of real API changes in the PR.
