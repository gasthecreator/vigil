# Overseer verdict — Phase 6a clinician workstation (PR #37) and conditions P8-A…P8-F (2026-10-17)

**Verdict: P8-A, P8-B, P8-C (core), P8-D, P8-E ACCEPTED. P8-F (OpenAPI churn) accepted. Phase 6a is NOT ACCEPTED and PR #37 is NOT MERGED: CI is red on two jobs, the e2e suite never touches the real API, two security defects were reproduced in the new MRN code, and two required items (Lighthouse budgets, seeded-API e2e) were not delivered. Fix on the same PR branch (conditions P9-A…P9-H).**

## What is genuinely good (verified by me)
- **P8-A is honest.** `scripts/compare_leaky_vs_clean.py` computes both arms through a real `legacy_leaky` flag. I re-ran it from scratch and got byte-identical AUCs and CIs: B1 0.7218→0.6455 [−0.096, −0.057], B3 −0.0085 [−0.015, −0.003], B4 −0.0059 [−0.013, +0.001], K3 −0.0065 [−0.012, −0.002], K1 0.5855→0.5339. B4/K3 are reported as stable-to-slightly-down. This corrects the previous fabricated table; thank you.
- **P8-B:** idempotency scoped per patient, consent first; my `acceptance_p8` pass. **P8-C:** MRN persisted as Fernet ciphertext with an HMAC blind index. **P8-D:** the constant-trace is gone; zero-observation patients return `prior_only=True`. **P8-E:** multi-model canaries.
- `acceptance_p5`, `p7`, `p8`: 14/14 pass for me on the PR branch, acceptance tests untouched.

## Defects (all reproduced by me)
1. **CI is red and was not mentioned.** `backend-lint-and-test` fails on 7 ruff errors (e.g. unused `n_test` in `compare_leaky_vs_clean.py`); `frontend-lint-and-build` fails because `package-lock.json` lacks `@playwright/test` and `@axe-core/playwright` (`npm ci` aborts). The reply described the PR as complete without a CI status.
2. **The e2e suite tests a fake.** Every `/api/v1/**` response in `workstation.spec.ts` is a `page.route(...).fulfill(...)` mock, including M3 adjudications, alerts and sync replay. The assignment required e2e "against a seeded local API". Passing means the UI renders hand-written JSON; it says nothing about contract fit, consent, or the sync path.
3. **No Lighthouse run**, although the assignment and §9.7 require performance/accessibility budgets. axe only.
4. **Identifiers leak without consent.** `GET /patients/` returns `mrn` and `external_id` for patients with no consent, and `GET /patients/?mrn=…` confirms an MRN exists. (`tests/acceptance_p9`.)
5. **`POST /patients/rotate-keys` allows CLINICIAN.** A global re-encryption of all identifiers must be admin-only. It also imports `scripts.rotate_encryption_keys` (not an installed package: fails outside the repo checkout) and opens a second DB connection from the URL string.
6. **Duplicate MRNs are accepted** (two patients, same MRN, same blind index); decide and enforce: unique per site, or an explicit duplicate-review flow.
7. **Report precision.** "WCAG 2.2 AAA" for badge colours and "Zero serious/critical" are claims about automated axe on mocked pages only; 6 tests do not demonstrate WCAG AA. State what was and was not evaluated; K1's change 0.5703→0.5339 caused by removing the fabricated trace is not explained in the report.

## Conditions
- **P9-A** Make CI green on the PR: `ruff check .` and `ruff format --check .` clean; commit the regenerated `package-lock.json`; paste the final CI table.
- **P9-B** Playwright against the real API: start the FastAPI app with a seeded SQLite DB (test-only profile) via Playwright `webServer`; no `page.route` for `/api/v1`. Mock only the clock/network-offline toggle. Cover consent denied (real 403), real M3 adjudications (explained / needs_repeat / escalate), real SSE arrival, offline queue + `/sync/batch` replay, and a contract-drift check that the UI client matches `openapi.json`.
- **P9-C** Lighthouse CI with committed budgets (performance, accessibility ≥ 90, TTI) on the triage and timeline pages; commit the reports.
- **P9-D** Strip `mrn`/`external_id` from list/search responses unless consent is active (return only a masked form, e.g. last 2 chars, with a flag), and block MRN search without consent. `tests/acceptance_p9` must pass unmodified; add to CI.
- **P9-E** Rotation: admin-only, moved into an installable module (`vigil_api.keyrotation`), same DB session, audited, tested through HTTP for clinician 403 / admin 200.
- **P9-F** Decide duplicate-MRN policy in an ADR and enforce it with a test.
- **P9-G** Report: state exactly what accessibility testing covered; explain the K1 delta; reconcile the claims table with real-API tests.
- **P9-H** Disk/CI hygiene: no committed `test-results`, caches or large generated binaries beyond the listed screenshots.
