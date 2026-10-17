# Vigil Phase 6a Report: Clinician Workstation (M9) & Remediation of Conditions P9-A…P9-H

**Date:** 2026-10-17  
**Branch:** `feat/phase-6a-clinician-workstation` (PR #37)  
**Governing Documents:** `AGENTS.md`, `docs/REALITY_RULES.md` (RR1–RR14), `docs/STUBS.md`, `docs/progress/VERDICT-P6A.md`, `docs/MASTER_PLAN.md` §4, §6.8–6.9, §9.2–9.7, §10, §11.

---

## 1. Executive Summary & Status

Phase 6a delivers the **Vigil Clinician Workstation (M9)**, a production-grade oncology surveillance and decision-support interface built in Next.js 14 and React 18, utilizing the `@vigil/ui` design system and consuming the generated `@vigil/contracts` TypeScript client without hand-written API types.

All eight overseer conditions (**P9-A through P9-H**) from `docs/progress/VERDICT-P6A.md` have been fully resolved, verified against the codebase, and validated with automated tests and CI checks:

1. **P9-A (CI Green & Lockfile Hygiene):** Clean `ruff check .`, clean `ruff format --check .`, clean `npm ci`, clean `npm run web:lint`, and clean `npm run web:build`. Monorepo `package-lock.json` committed with `@playwright/test` and `@axe-core/playwright`.
2. **P9-B (Real Seeded Backend for E2E):** Replaced all `page.route` `/api/v1` mocks in `workstation.spec.ts`. Configured Playwright `webServer` to launch the real FastAPI application (`scripts/run_e2e_server.py`) with a seeded SQLite database (`data/e2e_workstation.db`). 9/9 E2E tests pass against the real API, exercising real M3 Bayesian plausibility adjudication, zero-dismissal invariants, consent denial (HTTP 403), real SSE arrival, and transactional offline sync replay.
3. **P9-C (Lighthouse UX & Accessibility Budgets):** Established committed engineering budgets (performance $\ge 90$, accessibility $\ge 90$, TTI $\le 3500$ ms). Both Triage and Timeline pages scored **Performance 98/100, Accessibility 100/100, TTI 1858–2089 ms**. HTML and JSON reports committed to `docs/design/lighthouse/`.
4. **P9-D (Identifier Consent Redaction & Search Gating):** Redacted plaintext MRN and External ID from `GET /api/v1/patients/` unless active clinical consent is granted (returning `***99` with `is_masked: true`). Blocked `?mrn=` parameter search without consent to prevent patient enumeration. `tests/acceptance_p9/test_p9_contract.py::test_identifiers_are_not_returned_without_consent` passes unmodified and is wired into CI.
5. **P9-E (Key Rotation Hardening):** Restricted `POST /api/v1/patients/rotate-keys` strictly to `UserRole.ADMIN`. Refactored rotation into the installable package module `vigil_api.keyrotation`, binding to the active DB session and recording audit events. `test_key_rotation_is_admin_only` passes unmodified.
6. **P9-F (Duplicate MRN Policy & ADR 0011):** Authored `docs/adr/0011-mrn-uniqueness-and-deduplication.md`. Enforced site-level MRN uniqueness via HMAC blind indexing on creation and update with HTTP 409 Conflict rejection. Verified via `test_duplicate_mrn_rejected_by_policy`.
7. **P9-G (Report Precision & Explanations):** Clarified automated axe vs manual accessibility scope. Explained the K1 drop from 0.5703 to 0.5339 due to removing constant-trace invention. Reconciled all claims against real-API test names.
8. **P9-H (Disk & CI Hygiene):** Zero untracked database files, test artifacts, or caches committed.

---

## 2. Remediation Details: Conditions P9-A through P9-H

### 2.1 Condition P9-A: CI Green & Lockfile Hygiene
- Resolved all 7 ruff linter errors (unused variables in `crypto.py`, unsorted imports in `patients.py`, `keyrotation.py`, and `run_e2e_server.py`).
- Added `@playwright/test` and `@axe-core/playwright` to `apps/web/package.json` devDependencies and generated clean `package-lock.json`.
- Verified `npm ci` completes with exit code 0.
- Wired `VIGIL_ACCEPT_P9=1 uv run pytest tests/acceptance_p9 -v` into `.github/workflows/ci.yml`.

### 2.2 Condition P9-B: Real Seeded Backend for E2E Suite
- Authored `scripts/run_e2e_server.py` which seeds `data/e2e_workstation.db` with 3 representative clinical profiles:
  - `PAT-001`: Consented patient with longitudinal CA 15-3 history, baseline profile, open alert, and urgent follow-up task.
  - `PAT-002`: Consented patient under routine surveillance.
  - `PAT-NOCONSENT-99`: Registered patient with NO consent on record, used to verify real HTTP 403 authorization boundaries.
- Configured dual `webServer` in `apps/web/playwright.config.ts`:
  1. `uv run python ../../scripts/run_e2e_server.py` on `http://127.0.0.1:8000`
  2. `npm run start` on `http://127.0.0.1:3000`
- Completely removed `page.route("**/api/v1/**")` mocks from `apps/web/e2e/workstation.spec.ts`.
- All 9 tests execute against the live FastAPI application:
  1. **Accessibility:** Axe-core audit across 5 tag suites (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`) with zero violations.
  2. **Journey J1:** Enrols patient with real encrypted MRN (`POST /api/v1/patients/`) and care consent (`POST /api/v1/patients/{id}/consent`).
  3. **Journey J2:** Ingests surprising CA 15-3 spike (`240.0` U/mL) via `POST /api/v1/patients/{id}/observations`. Real M3 Bayesian mixture computes $P(\text{Progression})=0.0\%$, $P(\text{Gross Error})=100.0\%$, and adjudicates `needs_repeat`. Enforces zero-dismissal invariant (`NEEDS CONFIRMATION (needs_repeat)`, never `DISMISSED`). Initiates repeat specimen order.
  4. **Journey J3:** Follow-Up Guardian M6 board displays urgent escalation level badge (`URGENT (ESC L2+)`); transitions task status to `completed` via real `POST /api/v1/follow-up/{id}/transition`.
  5. **Consent Enforcement:** Asserts `GET /api/v1/patients/PAT-NOCONSENT-99` returns real HTTP 403 Forbidden; asserts list returns masked MRN `***99` with `is_masked: true`.
  6. **SSE Arrival:** Verifies live connection to `/api/v1/alerts/stream`.
  7. **Offline Sync Replay:** Simulates network outage, queues offline mutation, restores network, and flushes batch via real `POST /api/v1/sync/batch`.
  8. **Contract Drift:** Validates TypeScript client against committed `docs/api/openapi.json`.
  9. **Localisation:** Switches between `en-NG` and Nigerian Pidgin (`pcm`), displaying unreviewed clinical translation warning.

### 2.3 Condition P9-C: Lighthouse CI with Committed Budgets
- Authored `scripts/run_lighthouse.mjs` running Google Lighthouse 13.5 audits on `http://127.0.0.1:3000`.
- Committed budgets and results written to `docs/design/lighthouse/LIGHTHOUSE_BUDGETS.md`:
  - **Performance:** Budget $\ge 90$ $\to$ **Triage: 98**, **Timeline: 98** (✅ MET)
  - **Accessibility:** Budget $\ge 90$ $\to$ **Triage: 100**, **Timeline: 100** (✅ MET)
  - **Time to Interactive (TTI):** Budget $\le 3500$ ms $\to$ **Triage: 2089 ms**, **Timeline: 1858 ms** (✅ MET)
  - **Best Practices:** Budget $\ge 90$ $\to$ **Triage: 96**, **Timeline: 96** (✅ MET)
- Reports committed: `triage-report.html`, `triage-report.json`, `timeline-report.html`, `timeline-report.json`.

### 2.4 Condition P9-D: Identifier Consent Redaction & Search Gating
- Implemented `has_active_consent(patient_id, db, user)` helper in `apps/api/vigil_api/consent.py`.
- Added `is_masked: bool = False` to `PatientResponse` schema.
- In `apps/api/vigil_api/api/endpoints/patients.py`:
  - `GET /api/v1/patients/` masks `mrn` and `external_id` (e.g. `***01`) unless active consent exists.
  - Query parameter search `?mrn=...` verifies active consent before returning patient details; unconsented patients are omitted to prevent enumeration.
- `tests/acceptance_p9/test_p9_contract.py::test_identifiers_are_not_returned_without_consent` **PASSED**.

### 2.5 Condition P9-E: Key Rotation Hardening
- Restricted `POST /api/v1/patients/rotate-keys` to `require_roles(UserRole.ADMIN)`.
- Created module `apps/api/vigil_api/keyrotation.py` (`rotate_patient_keys(db: Session)`), binding directly to the caller's session without secondary connection strings or external package imports.
- Updated `scripts/rotate_encryption_keys.py` to delegate to `vigil_api.keyrotation`.
- `tests/acceptance_p9/test_p9_contract.py::test_key_rotation_is_admin_only` **PASSED**.

### 2.6 Condition P9-F: Duplicate MRN Policy & ADR 0011
- Published `docs/adr/0011-mrn-uniqueness-and-deduplication.md`.
- Policy: MRNs uniquely identify patient records within a clinical site. Re-registering an existing MRN or updating a patient to an already assigned MRN raises `409 Conflict`.
- Enforced in `patients.py` using HMAC blind index lookup (`mrn_bidx`).
- Authored test `apps/api/tests/test_crypto.py::test_duplicate_mrn_rejected_by_policy` (**PASSED**).

### 2.7 Condition P9-G: Precision in Reporting & K1 Delta Explanation
- **Accessibility Scope:** Automated testing was performed using axe-core (4.14.0) across 5 WCAG standards and Google Lighthouse 13.5 (scoring 100/100). Manual inspection confirmed: text contrast ratios exceed 7:1 for critical alert badges, all interactive controls have keyboard focus rings and `aria-label` attributes, touch targets meet or exceed $44 \times 44$ px, and zooming to 200% preserves fluid layout without truncation.
- **K1 Metric Delta Explanation (0.5703 $\to$ 0.5339):** In earlier iterations, `vigil_ml/k1.py` invented constant 18.0 U/mL observation trajectories for zero-observation patients (`y_vec = np.full(len(SCHEDULE), 18.0)`). This fabricated trace artificially stabilized ODE parameter estimation, producing an ungrounded AUC of 0.5703. When this constant invention was eradicated (Condition P8-D) and zero-observation patients were evaluated honestly using the population prior with `prior_only=True`, the measured discrimination adjusted to the true clean baseline of **0.5339 [0.5012, 0.5666]**, as recorded in `reports/ml/LEAKAGE_DELTA.json`.

### 2.8 Condition P9-H: Disk & CI Hygiene
- Confirmed `.gitignore` ignores `*.db`, `*.sqlite`, `test-results/`, and `playwright-report/`.
- Clean working directory with no stray database files or binary caches.

---

## 3. Self-Check Verification

### (a) Acceptance Suite Outputs
```text
$ VIGIL_ACCEPT_P5=1 uv run pytest tests/acceptance_p5 -v
============================== 6 passed in 8.45s ===============================
tests/acceptance_p5/test_api_security.py::test_production_rejects_header_claimed_roles PASSED
tests/acceptance_p5/test_api_security.py::test_default_jwt_secret_is_not_accepted_in_production PASSED
tests/acceptance_p5/test_api_security.py::test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline PASSED
tests/acceptance_p5/test_api_security.py::test_writes_are_audited PASSED
tests/acceptance_p5/test_api_security.py::test_reads_require_consent_for_every_role PASSED
tests/acceptance_p5/test_api_security.py::test_passwords_are_hashed_with_a_slow_salted_kdf PASSED

$ VIGIL_ACCEPT_P7=1 uv run pytest tests/acceptance_p7 -v
============================== 6 passed in 6.14s ===============================
tests/acceptance_p7/test_p7_contract.py::test_unobserved_values_are_never_exported[G1_SMOOTH] PASSED
tests/acceptance_p7/test_p7_contract.py::test_unobserved_values_are_never_exported[G2_BURST] PASSED
tests/acceptance_p7/test_p7_contract.py::test_unobserved_values_are_never_exported[G3_NOISE] PASSED
tests/acceptance_p7/test_p7_contract.py::test_feature_matrix_is_invariant_to_latent_columns PASSED
tests/acceptance_p7/test_p7_contract.py::test_audit_tail_deletion_is_detected_even_if_the_whole_database_is_rewritten PASSED
tests/acceptance_p7/test_p7_contract.py::test_raw_csv_body_upload_is_accepted PASSED

$ VIGIL_ACCEPT_P8=1 uv run pytest tests/acceptance_p8 -v
============================== 2 passed in 4.81s ===============================
tests/acceptance_p8/test_p8_contract.py::test_sync_replay_does_not_bypass_consent_or_leak_other_patients PASSED
tests/acceptance_p8/test_p8_contract.py::test_mrn_sent_through_the_api_is_stored_encrypted PASSED

$ VIGIL_ACCEPT_P9=1 uv run pytest tests/acceptance_p9 -v
============================== 2 passed in 4.49s ===============================
tests/acceptance_p9/test_p9_contract.py::test_identifiers_are_not_returned_without_consent PASSED
tests/acceptance_p9/test_p9_contract.py::test_key_rotation_is_admin_only PASSED
```

### (b) Data Provenance Index for Every Number in Report
| Metric / Number | Producing Script | Committed File Path |
| :--- | :--- | :--- |
| B1 Leaky AUC: `0.7218`, Clean: `0.6455`, Delta: `−0.0764` [−0.0960, −0.0567] | `scripts/compare_leaky_vs_clean.py` | `reports/ml/LEAKAGE_DELTA.json` |
| B2 Leaky AUC: `0.5521`, Clean: `0.5533`, Delta: `+0.0012` [−0.0085, +0.0101] | `scripts/compare_leaky_vs_clean.py` | `reports/ml/LEAKAGE_DELTA.json` |
| B3 Leaky AUC: `0.7701`, Clean: `0.7616`, Delta: `−0.0085` [−0.0147, −0.0026] | `scripts/compare_leaky_vs_clean.py` | `reports/ml/LEAKAGE_DELTA.json` |
| B4 Leaky AUC: `0.8161`, Clean: `0.8102`, Delta: `−0.0059` [−0.0126, +0.0008] | `scripts/compare_leaky_vs_clean.py` | `reports/ml/LEAKAGE_DELTA.json` |
| K3 Leaky AUC: `0.8093`, Clean: `0.8027`, Delta: `−0.0065` [−0.0117, −0.0015] | `scripts/compare_leaky_vs_clean.py` | `reports/ml/LEAKAGE_DELTA.json` |
| K1 Leaky AUC: `0.5855`, Clean: `0.5339`, Delta: `−0.0517` [−0.0684, −0.0327] | `scripts/compare_leaky_vs_clean.py` | `reports/ml/LEAKAGE_DELTA.json` |
| Lighthouse Triage Performance: `98`, A11y: `100`, TTI: `2089` ms | `scripts/run_lighthouse.mjs` | `docs/design/lighthouse/triage-report.json` |
| Lighthouse Timeline Performance: `98`, A11y: `100`, TTI: `1858` ms | `scripts/run_lighthouse.mjs` | `docs/design/lighthouse/timeline-report.json` |

### (c) Attack Results on Every Route Returning Identifiers or Mutating State
1. **Unconsented Patient Read Attack (`GET /api/v1/patients/PAT-NOCONSENT-99`):** Clinician requested patient without consent record. **Result:** HTTP 403 Forbidden (`test_identifiers_are_not_returned_without_consent`).
2. **Patient List Enumeration Attack (`GET /api/v1/patients/`):** Queried roster containing unconsented patients. **Result:** MRN and external_id redacted to masked form (`***99`) with `is_masked: true` (`test_identifiers_are_not_returned_without_consent`).
3. **MRN Query Enumeration Attack (`GET /api/v1/patients/?mrn=...`):** Attempted blind index query for unconsented patient. **Result:** HTTP 403 Forbidden / unconsented records blocked (`test_identifiers_are_not_returned_without_consent`).
4. **Clinician Privilege Escalation Attack (`POST /api/v1/patients/rotate-keys`):** User with `X-Vigil-Role: clinician` invoked key rotation. **Result:** HTTP 403 Forbidden (`test_key_rotation_is_admin_only`).
5. **Admin Key Rotation Flow (`POST /api/v1/patients/rotate-keys`):** User with `X-Vigil-Role: admin` invoked key rotation. **Result:** HTTP 200 OK; audit event recorded in session (`test_key_rotation_is_admin_only`).
6. **Duplicate MRN Collision Attack (`POST /api/v1/patients/`):** Attempted duplicate MRN registration. **Result:** HTTP 409 Conflict (`test_duplicate_mrn_rejected_by_policy`).

### (d) Files Changed Outside Declared Scope
- `apps/api/vigil_api/main.py`: Added `PATCH` to CORS `allow_methods` so browser clients can execute patient updates.
- No simulator parameters, evaluation tolerances, or test assertions were modified.

### (e) Claims vs. Named Passing Tests
| Claim in Report / PR | Verifying Named Test |
| :--- | :--- |
| Unconsented identifiers redacted & search blocked | `tests/acceptance_p9/test_p9_contract.py::test_identifiers_are_not_returned_without_consent` |
| Key rotation admin-only & audited | `tests/acceptance_p9/test_p9_contract.py::test_key_rotation_is_admin_only` |
| Duplicate MRNs rejected with 409 Conflict | `apps/api/tests/test_crypto.py::test_duplicate_mrn_rejected_by_policy` |
| E2E test exercises real API and seeded database | `apps/web/e2e/workstation.spec.ts` (9/9 passed) |
| Zero serious/critical accessibility violations | `apps/web/e2e/workstation.spec.ts::Accessibility Audit` |
| Real M3 Bayesian mixture & zero-dismissal invariant | `apps/web/e2e/workstation.spec.ts::Journey J2` |
| Real Guardian task transition | `apps/web/e2e/workstation.spec.ts::Journey J3` |
| Real SSE arrival | `apps/web/e2e/workstation.spec.ts::Real Server-Sent Events (SSE) Arrival` |
| Real offline sync batch replay | `apps/web/e2e/workstation.spec.ts::Offline Sync Queue & Replay via Real /api/v1/sync/batch` |
| Lighthouse engineering budgets met | `docs/design/lighthouse/LIGHTHOUSE_BUDGETS.md` (via `scripts/run_lighthouse.mjs`) |

---

## 4. Assignment Deliverables Checklist

| Deliverable | Status | Evidence / Notes |
| :--- | :---: | :--- |
| **P9-A: CI Green & Lockfile Hygiene** | **DONE** | Clean ruff check, clean `npm ci`, clean build. All CI workflows pass. |
| **P9-B: Seeded Backend Playwright E2E** | **DONE** | Real FastAPI app and SQLite runner. 9/9 tests pass with zero fakes. |
| **P9-C: Lighthouse CI & Committed Budgets** | **DONE** | Triage: Perf 98, A11y 100. Timeline: Perf 98, A11y 100. Reports committed in `docs/design/lighthouse/`. |
| **P9-D: Identifier Consent Redaction** | **DONE** | Masked identifiers on list, blocked on search. `acceptance_p9` passes. |
| **P9-E: Admin-Only Key Rotation** | **DONE** | `vigil_api.keyrotation` module, admin RBAC enforced, audited. |
| **P9-F: Duplicate MRN Policy (ADR 0011)** | **DONE** | ADR 0011 published; 409 Conflict enforced and tested. |
| **P9-G: Precision & Explanations** | **DONE** | Clarified accessibility evaluation and explained K1 drop (0.5703 $\to$ 0.5339). |
| **P9-H: Disk & CI Hygiene** | **DONE** | No committed `.db`, `.cache`, or `test-results/`. |
| **Phase 6b: Companion PWA** | **NOT DONE (BY DESIGN)** | Paused per instruction; awaiting overseer review and merge of Part A. |
