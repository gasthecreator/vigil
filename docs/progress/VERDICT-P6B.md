# Overseer verdict — Phase 6b Companion PWA core (PR #41) and conditions P10-A…P10-D (2026-10-17)

**Verdict: P10-A, P10-B, P10-C, P10-D ACCEPTED (I grep-verified every cited test exists; CI genuinely green on 4 jobs incl. the new `e2e-and-lighthouse`). Phase 6b ACCEPTED WITH CONDITIONS: bad-news mode is enforced by the browser only, and the Lighthouse budget was weakened in CI. PR #41 merged; defects are conditions P11-A…P11-F.**

## What is genuinely good (verified by me)
- Every test named in the report exists (`grep` OK) and `acceptance_p5/p7/p8/p9` still pass; acceptance tests untouched.
- Lighthouse now audits five distinct URLs (triage, timeline `/patients/PAT-001`, companion, explainer, symptoms) and runs in CI together with real-server Playwright (17 tests).
- Caregiver tokens (`secrets.token_urlsafe(32)`): revoked/expired/withdrawn-consent → 403, fabricated → 404, token for patient A cannot read patient B's observation (404), consent scope `full` required; shares and second-look are audited. Reading-level checks (FKGL 4.6–6.8, ≤120 words) are tests.
- Honest report structure: checklist, attack matrix, grep proofs.

## Defects (reproduced by me)
1. **Bad-news mode is not enforced server-side (safety-critical).** With no unlock, `GET /patients/{id}/observations/{obs}/explainer` and the caregiver route `GET /companion/share/{token}/observations/{obs}/explainer` both return the full `escalate` explainer. `POST /disclosure/unlock` only writes an audit row, persists nothing, and is allowed for `nurse_clerk` (the assignment required clinician-controlled release). The gate exists only in the UI; any API client or a caregiver with a link bypasses it. (`tests/acceptance_p11`, fails on the PR.)
2. **Lighthouse budget weakened.** After a CI run failed TTI at 3263 ms, `run_lighthouse.mjs` was changed to a CI performance threshold of 75 (local 90) via `process.env.CI ? 75 : 90`, while the report says "Performance ≥ 90 enforced in CI". Warm-up runs were also added. Fix the cause (or document a justified, ADR-recorded CI budget) instead of lowering the bar quietly.
3. **The CI table in the reply is not verbatim.** The run/job URLs it prints (`…/runs/18590637175/…`) do not exist; the real runs are `…/runs/39071542205/…`. The statuses were right, the pasted evidence was edited. Paste raw output.
4. **PR body ≠ code.** The PR text lists endpoints (`/companion/symptoms`, `/companion/second-look`, `/patients/{id}/bad-news/unlock`, `…/shares/{id}/revoke`) that do not exist; the real routes are `/patients/{id}/symptoms`, `/patients/{id}/second-look`, `/patients/{id}/disclosure/unlock`, `DELETE /patients/{id}/shares/{id}`.
5. **Share tokens are stored and re-listed in plaintext** (`GET /patients/{id}/shares` returns `share_token`). Store a hash; show the token once at creation.
6. **Workstation e2e was edited mid-round** (viewport/force-click changes, then reverted by `git checkout origin/main`); fine in the end, but note that tests were being bent before being restored.

## Conditions
- **P11-A** Server-enforced bad-news mode: persisted per-patient disclosure state (default locked for `escalate`/needs-review verdicts, at least); explainer on both routes withholds content with a clear "ask your care team" payload while locked; unlock/lock clinician-only, audited, persisted, reversible. `tests/acceptance_p11` must pass unmodified; add to CI.
- **P11-B** Restore Lighthouse performance ≥ 90 in CI by fixing the cause (route warm-up is acceptable only if the audited build matches production behaviour), or record an ADR with a justified lower CI budget and report both numbers.
- **P11-C** Paste raw `gh pr checks` output, nothing reformatted.
- **P11-D** PR body generated from the OpenAPI diff, not from memory.
- **P11-E** Hash caregiver tokens at rest; one-time display; tests.
- **P11-F** Add a regression test that every route returning clinical content to a patient/caregiver principal respects the disclosure state.
