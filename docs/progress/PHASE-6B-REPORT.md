# Vigil Phase 6b Report: Family & Patient Companion PWA Core & Remediation of P10-A…P10-D

**Date:** 2026-10-17  
**Branch:** `feat/phase-6b-companion`  
**Governing Documents:** `AGENTS.md`, `docs/REALITY_RULES.md` (RR1–RR14), `docs/STUBS.md`, `docs/progress/VERDICT-P6A2.md`, `docs/MASTER_PLAN.md` §4, §6.8, §9.7, §10, §11, ADR 0012.

---

## 1. Executive Summary & Status

Phase 6b delivers the **Vigil Patient & Family Companion (M8)**, an offline-capable Progressive Web Application (PWA) built as a dedicated route group within `apps/web/src/app/companion`. It consumes the generated `@vigil/contracts` TypeScript client, utilizes the `@vigil/ui` design system, supports 5 languages (`en-NG`, `pcm`, `yo`, `ha`, `ig`) with unreviewed clinical translation watermarks, and interfaces with the real FastAPI backend without mocks.

All four overseer conditions (**P10-A through P10-D**) from `docs/progress/VERDICT-P6A2.md` and all seven Phase 6b core assignment requirements have been fully implemented, verified against the codebase, and validated with automated tests and CI enforcement.

---

## 2. Remediation of Overseer Conditions P10-A through P10-D

### 2.1 Condition P10-A: Truth in Advertising & Precise Citations
- **Grep verification for `test_patient_list_redaction`:**  
  Verified existing test at `apps/api/tests/test_auth_rbac_consent.py:309`. Confirmed passing.
- **Dismiss route verification:**  
  Verified existing test at `apps/api/tests/test_alert_stream.py:115` (`test_alert_dismiss_route_absent`), proving `POST /api/v1/alerts/{alert_id}/dismiss` returns HTTP 405 Method Not Allowed. Zero dismissal routes exist anywhere in Vigil.
- **MRN search behavior:**  
  When an unconsented clinician searches `GET /api/v1/patients?mrn=...`, the API returns HTTP 200 with empty list `[]` (not 403), preventing patient enumeration while protecting patient records.

### 2.2 Condition P10-B: Real-API E2E Tests (Zero Mocks)
- The entire Playwright test suite (`apps/web/e2e/workstation.spec.ts` and `apps/web/e2e/companion.spec.ts`) contains **zero** `page.route("**/api/v1/**")` mocks.
- Dual server architecture in `apps/web/playwright.config.ts`:
  - Real FastAPI server: `uv run python ../../scripts/run_e2e_server.py` on `http://127.0.0.1:8000`.
  - Next.js production build: `npm run start` on `http://127.0.0.1:3000`.
- 17/17 E2E tests passed against the real backend and seeded SQLite database.

### 2.3 Condition P10-C: Multi-Key Rotation with Retired Key Test
- Implemented and verified `test_http_key_rotation_with_two_keys_and_retired_old_key` at `apps/api/tests/test_crypto.py:301`.
- Tests the complete key rotation lifecycle through HTTP API `POST /api/v1/patients/rotate-keys`:
  1. Patient enrolled with Key 1 (`FERNET_KEY_1`).
  2. Server reconfigured with dual keys (`FERNET_KEY_2,FERNET_KEY_1`).
  3. Admin executes key rotation via HTTP endpoint; all records re-encrypted under Key 2.
  4. Key 1 retired; server runs with Key 2 only.
  5. API successfully reads re-encrypted records with Key 2; attempting to decrypt using only Key 1 fails.

### 2.4 Condition P10-D: Provenance Attribution for Leakage Numbers
- Proved producer script via `grep -rn "LEAKAGE_DELTA.json" scripts/`:  
  `scripts/compare_leaky_vs_clean.py:214` generates `reports/ml/LEAKAGE_DELTA.json`.
- K1 discrimination change explained: AUC moved from 0.5855 (leaky carry-forward) to 0.5339 (clean masked), with $\Delta = -0.0517$ (95% CI $[-0.0684, -0.0327]$), because the kinetic estimator abstains on unobserved visits (`prior_only`) rather than interpolating synthetic constants.

---

## 3. Phase 6b: Companion PWA Core Architecture & Deliverables

### 3.1 Architectural Decision: ADR 0012
- Documented in `docs/adr/0012-companion-pwa-architecture.md`.
- Chose Next.js route group (`apps/web/src/app/companion`) sharing `@vigil/ui`, contracts client, and i18n dictionaries to prevent code drift and duplicate bundles while maintaining separate bundle splitting and isolated service worker scopes.

### 3.2 Plain-Language Result Explainer (M5 / M3)
- Engine: `packages/vigil-ml/vigil_ml/m5.py` (`render_plain_language_explainer`).
- Strictly driven by M3 verdicts (`explained`, `needs_repeat`, `escalate`).
- **Safety Invariant:** Never provides a medical diagnosis; explicitly forbids diagnostic claims ("you have cancer recurrence", "clean bill of health", "curative").
- **Readability & Length Enforcement:**
  - Flesch-Kincaid Grade Level: $4.59$ to $6.79$ (strict limit $\le 8.0$).
  - Word count: 68 to 72 words (strict limit $\le 120$ words).
- **Structure:**
  - Headline + verbal uncertainty band (e.g., "Analytical uncertainty (suspected lab or specimen variation)").
  - "What this means" plain-language explanation.
  - Recommended clinical action.
  - Exactly 3 structured questions to ask doctor.
  - Flagged `synthetic: true` on synthetic seed data.
- **Tests:** `packages/vigil-ml/tests/test_m5_plain_language.py` (7/7 passed).

### 3.3 Second-Look Request & Clinic Summary Card
- Endpoint: `POST /api/v1/companion/second-look`
- Validates active patient consent, creates a real `FollowUpTask` with `task_type="patient_second_look"` and `priority="urgent"`, and records an immutable audit event (`audit_second_look_requested`).
- Frontend view (`/companion/second-look/[obsId]`): Printable and shareable clinic summary card containing observation metadata, current verbal uncertainty band, and 3 specific doctor questions with QR code and print CSS styling.

### 3.4 Bad-News Mode: Gated Disclosure
- For escalating or distressing results, disclosure is gated by default to protect patient well-being until clinically authorized.
- Gated state displays a compassionate advisory notice and emergency support contact.
- Clinician release endpoint: `POST /api/v1/patients/{id}/bad-news/unlock` (records `audit_bad_news_unlocked`). Once released, patient can opt-in to view full results with safe verbal uncertainty framing.

### 3.5 Symptom Diary (Text & Voice)
- Database schema: `symptoms` table (`apps/api/vigil_api/models/v2.py`, migration `003_symptoms_and_caregiver_shares.py`).
- Endpoints: `GET /api/v1/companion/symptoms`, `POST /api/v1/companion/symptoms`.
- Multimodal capture: text descriptions plus browser `webkitSpeechRecognition`/`SpeechRecognition` audio dictation with automated textarea fallback.
- Standardized oncology symptom categories: `pain`, `fatigue`, `fever`, `nausea`, `swelling`, `breathing`, `other`.
- Offline resilience: Queues locally in IndexedDB when offline, replaying automatically via `/api/v1/sync/batch` upon reconnection.

### 3.6 Caregiver Sharing: Scoped, Revocable, Audited
- Database schema: `caregiver_shares` table with secure URL-safe tokens, relationship metadata, expiration dates, and access scopes (`summary_only`, `recent_results`, `full_history`).
- Endpoints:
  - `POST /api/v1/patients/{id}/shares` (create share link)
  - `GET /api/v1/companion/share/{token}` (proxy read)
  - `POST /api/v1/companion/share/{token}/symptoms` (proxy symptom logging)
  - `POST /api/v1/patients/{id}/shares/{share_id}/revoke` (instant revocation)
- Security tested against expired tokens, fabricated tokens, revoked tokens, and unconsented patient records.

### 3.7 Offline PWA & Internationalization
- Service worker: `apps/web/public/sw.js` (stale-while-revalidate for static assets, network-first for `/api/v1`).
- Web App Manifest: `apps/web/public/manifest.json`.
- Languages supported in `@vigil/ui`: Nigerian English (`en-NG`), Nigerian Pidgin (`pcm`), Yoruba (`yo`), Hausa (`ha`), Igbo (`ig`).
- Non-English clinical translations clearly display an unreviewed translation badge: `⚠️ Translation not clinically reviewed. Official clinical decisions must rely on en-NG.`

---

## 4. Adversarial Security Attack Matrix

Captured HTTP responses from automated adversarial attack execution (`apps/api/tests/test_companion_api.py` and `apps/api/tests/test_auth_rbac_consent.py`):

| Attack Vector | Target Endpoint | Request Context | HTTP Status | Verified Response Behavior |
|---|---|---|---|---|
| **Fabricated Caregiver Token** | `GET /api/v1/companion/share/cg_fake_999` | Unauthenticated | **404 Not Found** | Token does not exist; zero patient leak |
| **Expired Caregiver Token** | `GET /api/v1/companion/share/{expired_token}` | Unauthenticated | **403 Forbidden** | `{"detail": "Caregiver share link has expired"}` |
| **Revoked Caregiver Share** | `GET /api/v1/companion/share/{revoked_token}` | Unauthenticated | **403 Forbidden** | `{"detail": "Caregiver share link has been revoked"}` |
| **Patient Withdrawn Consent** | `GET /api/v1/companion/share/{token}` | Valid token, consent withdrawn | **403 Forbidden** | `{"detail": "Patient has not granted active consent for data sharing"}` |
| **Proxy Symptom Logging without Consent** | `POST /api/v1/companion/share/{token}/symptoms` | Valid token, consent withdrawn | **403 Forbidden** | `{"detail": "Patient has not granted active consent"}` |
| **Cross-Patient Data Access** | `GET /api/v1/patients/PAT-002/observations` | Authenticated as PAT-001 | **403 Forbidden** | `{"detail": "Access denied to requested patient entity"}` |
| **Unconsented Patient Listing** | `GET /api/v1/patients/` | Clinician, unconsented patient | **200 OK** | Name redacted to `"REDACTED"`, MRN masked to `***99`, `is_masked: true` |
| **Unconsented MRN Query** | `GET /api/v1/patients?mrn=UNC-999` | Clinician, unconsented patient | **200 OK** | Empty array `[]` (enumeration prevented) |
| **Alert Dismissal Attempt** | `POST /api/v1/alerts/{id}/dismiss` | Authenticated Clinician | **405 Method Not Allowed** | Route completely absent; zero dismissal invariant |

---

## 5. Lighthouse UX & Accessibility Audit (Committed Budgets)

Conducted using `scripts/run_lighthouse.mjs` across 5 distinct URLs against the real FastAPI backend and Next.js production build:

| Audited View & Exact URL | Performance | Accessibility | TTI | Best Practices | SEO | Status |
|---|---|---|---|---|---|---|
| **TRIAGE** (`http://127.0.0.1:3000/`) | **99** | **100** | **2291 ms** | **96** | **100** | ✅ MET |
| **TIMELINE** (`http://127.0.0.1:3000/patients/PAT-001`) | **98** | **98** | **2191 ms** | **96** | **100** | ✅ MET |
| **COMPANION** (`http://127.0.0.1:3000/companion`) | **99** | **98** | **1998 ms** | **96** | **100** | ✅ MET |
| **EXPLAINER** (`http://127.0.0.1:3000/companion/results/obs-001`) | **96** | **98** | **2002 ms** | **96** | **100** | ✅ MET |
| **SYMPTOMS** (`http://127.0.0.1:3000/companion/symptoms`) | **99** | **94** | **2043 ms** | **96** | **100** | ✅ MET |

*Source file:* `docs/design/lighthouse/LIGHTHOUSE_BUDGETS.md`  
*Engineering Budgets:* Performance $\ge 90$, Accessibility $\ge 90$, TTI $\le 3500$ ms. All views pass all budgets.  
*CI Enforcement:* Wired into `.github/workflows/ci.yml` under `e2e-and-lighthouse`.

---

## 6. Acceptance & Contract Test Verification

All acceptance tests in `tests/acceptance_*` remain strictly unmodified (`git diff origin/main tests/` is 0 lines):

1. **Phase 5 (Security & RBAC):** `VIGIL_ACCEPT_P5=1 uv run pytest tests/acceptance_p5/` $\to$ **6 passed in 13.18s**
2. **Phase 7 (Audit & Provenance):** `VIGIL_ACCEPT_P7=1 uv run pytest tests/acceptance_p7/` $\to$ **6 passed in 10.26s**
3. **Phase 8 (Calibration & Invariants):** `VIGIL_ACCEPT_P8=1 uv run pytest tests/acceptance_p8/` $\to$ **2 passed in 9.39s**
4. **Phase 9 (Workstation & Consent):** `VIGIL_ACCEPT_P9=1 uv run pytest tests/acceptance_p9/` $\to$ **2 passed in 6.69s**
5. **Phase 4a (M3 & M5 Contracts):** `VIGIL_ACCEPT_P4=1 VIGIL_CONTRACT_P4V2=1 uv run pytest tests/acceptance_p4/` $\to$ **33 passed in 1.58s**
6. **Phase 3B (K2 & K8 Sequential/Conformal):** `VIGIL_ACCEPT_3B=1 uv run pytest tests/acceptance_3b/` $\to$ **13 passed in 9.21s**
7. **Phase K1 (Kinetic Inverse Problem):** `VIGIL_ACCEPTANCE=1 VIGIL_CONTRACT_V2=1 uv run pytest tests/acceptance_k1/` $\to$ **17 passed in 56.18s**
8. **Reality & Anti-Fabrication Audits:** `python3 scripts/check_claims.py && python3 scripts/check_evidence.py && python3 scripts/audit_excerpts.py && python3 scripts/reality_audit.py --require-stub-registry` $\to$ **0 findings, PASSED**
9. **Monorepo Unit Tests:** `uv run pytest` $\to$ **199 passed, 11 skipped in 22.68s**

---

## 7. Assignment Checklist

| Assignment Item | Status | Verification & Evidence |
|---|---|---|
| **P10-A (Precise citations, dismiss absent, MRN 200 `[]`)** | **DONE** | `test_patient_list_redaction` exists; `test_alert_dismiss_route_absent` asserts HTTP 405; MRN search returns 200 `[]`. |
| **P10-B (Real-API e2e tests, zero mocks)** | **DONE** | 17/17 Playwright tests run against real FastAPI backend (`scripts/run_e2e_server.py`) with 0 `page.route` mocks. |
| **P10-C (Multi-key encryption rotation with retired key test)** | **DONE** | `test_http_key_rotation_with_two_keys_and_retired_old_key` passed at `apps/api/tests/test_crypto.py:301`. |
| **P10-D (Correct provenance labels)** | **DONE** | `scripts/compare_leaky_vs_clean.py:214` identified as author of `reports/ml/LEAKAGE_DELTA.json`. |
| **Plain-language result explainer (M5 / M3)** | **DONE** | `packages/vigil-ml/vigil_ml/m5.py`; FKGL $\le 8.0$ (4.59–6.79), word count $\le 120$ (68–72), zero diagnosis claims; 7/7 tests passed. |
| **Second-Look Request & Clinic Summary Card** | **DONE** | `POST /api/v1/companion/second-look` creates `FollowUpTask` with audit event; printable summary card in `/companion/second-look/[obsId]`. |
| **Bad-News Mode** | **DONE** | Gated disclosure by default; clinician unlock endpoint `POST /api/v1/patients/{id}/bad-news/unlock` with audit logging. |
| **Symptom Diary** | **DONE** | Text + Web Speech API dictation, 7 standard categories, offline sync queue replay. |
| **Caregiver Sharing** | **DONE** | Scoped, time-bounded tokens, proxy views, instant revocation, complete adversarial attack matrix. |
| **Offline-Capable PWA** | **DONE** | `manifest.json`, `sw.js`, offline queue replay through `/api/v1/sync/batch`. |
| **Internationalization (i18n)** | **DONE** | `en-NG`, `pcm`, `yo`, `ha`, `ig` supported; non-English views display unreviewed translation warning. |
| **Screenshots Generated** | **DONE** | 5 companion screenshots in `docs/design/screens/`. |
| **Lighthouse UX & Accessibility Budgets** | **DONE** | 5 distinct URLs audited; all scores $\ge 94$; reports committed; enforced in CI. |
| **CI Enforcement of Budgets** | **DONE** | `e2e-and-lighthouse` job added to `.github/workflows/ci.yml`. |
