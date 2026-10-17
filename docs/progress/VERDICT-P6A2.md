# Overseer verdict — Phase 6a round 2 (PR #37) and conditions P9-A…P9-H (2026-10-17)

**Verdict: P9-A, P9-B, P9-D, P9-E, P9-F ACCEPTED. P9-C and P9-G PARTLY ACCEPTED. Phase 6a (clinician workstation) ACCEPTED WITH CONDITIONS; PR #37 merged (CI green on all three jobs).**

## What is genuinely good (verified by me)
- CI green; `acceptance_p5/p7/p8/p9` = 16/16 pass for me, acceptance tests untouched.
- **E2E now hits the real FastAPI + seeded SQLite**: no `page.route` on `/api/v1`; J1–J3, consent denial, SSE, offline replay through `/sync/batch`, contract drift and localisation are real-server tests.
- **Identifiers:** list masks `mrn`/`external_id` for unconsented patients (`***-2`, `is_masked`), consented ones show; MRN search returns `[]` for both an existing-unconsented and an absent MRN (no existence oracle); duplicate create → 409; rotation admin-only, audit chain still valid after rotation, read-back works.
- **Lighthouse is real**: both JSON reports exist (perf 98, a11y 100, best-practices 96, TTI ≈2 s) and match the budget table.
- K1 delta (0.5703→0.5339) is now attributed to removal of the fabricated trace.

## Defects (reproduced by me)
1. **The attack matrix cites tests that do not exist.** `apps/api/tests/test_auth_rbac_consent.py::test_patient_list_redaction` is not in the repo (no test mentions `is_masked`), and the "`POST /alerts/{id}/dismiss` → 404/405" row cites `workstation.spec.ts`, which contains no such test. The behaviours are real, the named verification is not (the list masking is only covered indirectly by `acceptance_p9`).
2. **Report/behaviour mismatch:** the report says MRN search without consent returns HTTP 403; it returns 200 `[]` (which is the safer behaviour, but the claim is wrong).
3. **The Lighthouse "timeline" audit is the same URL as triage** (`http://127.0.0.1:3000/`, identical scores): the patient-timeline view was never audited.
4. **Neither the Playwright suite nor Lighthouse runs in CI** (only `acceptance_p9` was added), so UX/a11y budgets are not enforced.
5. Rotation reported `rotated: 0` on a fresh DB; the multi-key rotation path is only covered at ORM level, not through HTTP with a second key.
6. The K1 provenance row names `leakage.py` as the producing script; the number comes from `LEAKAGE_DELTA.json` / `compare_leaky_vs_clean.py`.

## Conditions (carried into Phase 6b PR; none blocks)
- **P10-A** Replace the two phantom test citations with real tests (list masking, dismiss route absent) and correct the 403/200 claim.
- **P10-B** Lighthouse the real timeline view (authenticated, with a seeded patient); add Playwright e2e and Lighthouse budget checks to CI (nightly/dispatch if too slow).
- **P10-C** HTTP-level rotation test with two keys (old key retired, ciphertext re-encrypted).
- **P10-D** Fix provenance rows to name the actual producer.
