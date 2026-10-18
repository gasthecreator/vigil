# Vigil STRIDE Threat Model v2

**Document Version:** 2.0.0  
**Phase:** Phase 8a Governance & Safety Package Deliverable  
**Governing Standard:** `docs/MASTER_PLAN.md` §3, §9.3, §11, §14 (WP8.1 Item 2)  
**Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)  

---

## 1. System Overview & Trust Boundaries

The Vigil Precision Oncology Platform ingests laboratory observations, executes plausibility adjudication (M3), sequential recurrence detection (K2), verified clinical narrative drafting (M5), radiotherapy continuity scheduling (M7), caregiver companion delegation (M8), and audit validation (M10), while strictly coordinating follow-up actions via the Follow-Up Guardian (M6).

```
                      TRUST BOUNDARY 1: External Untrusted Networks
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
     [ Hospital LIS / EHR ]                  [ Clinician PWA / Companion ]
      (HL7 v2 / FHIR R4 / CSV)                (Bearer JWT / Scoped Caregiver Token)
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │ TLS 1.3
                      TRUST BOUNDARY 2: API Gateway & Auth Barrier
                                     │
                    ┌────────────────┴────────────────┐
                    │       FastAPI API Service       │
                    │   - RBAC (8 Canonical Roles)    │
                    │   - Patient Consent Verification│
                    │   - Blind Index Lookup Engine   │
                    │   - Stack Trace & Error Hygiene │
                    └────────────────┬────────────────┘
                                     │
                      TRUST BOUNDARY 3: Clinical Engine & Optimizers
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
  [ M3 Plausibility & K2 ]     [ M7 Continuity Solver ]    [ M10 Audit Engine ]
  (Sequential Bayes / Bi-exp)  (CP-SAT Rolling IP / Harm)  (Decoupled Validation)
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                      TRUST BOUNDARY 4: Core Persistence & Storage
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
  [ Relational DB ]         [ Field Encryption ]       [ External WORM Sink ]
   (Check Constraints,       (AES-128 / MultiFernet     (Audit Anchor Append-Only
    No-Dismissal Invariant)   Direct Identifiers)        Head Hash Commitments)
```

---

## 2. Security Roles & Principle of Least Privilege

Vigil enforces least privilege across eight explicit security roles:

1. **`clinician`**: Full clinical read/write, alerts adjudication, disclosure release, course management, solver confirmation.
2. **`nurse_clerk`**: Operational intake, lab observation entry, HL7 feed ingestion, follow-up contact logging. Forbidden from releasing disclosure unlocks or solving schedules.
3. **`quality_lead`**: Quality audits, cohort calibration, population metrics, read-only audit log inspection. Forbidden from mutating patient care records.
4. **`admin`**: System configuration, facility management, key rotation, user provisioning.
5. **`patient`**: Access strictly bounded to the patient's own profile, consented observations, and released clinical narratives. Roster enumeration and foreign patient access strictly blocked.
6. **`caregiver`**: Delegated read-only summary or symptom reporting bounded to a specific consented patient via cryptographically hashed share token. Excluded from unreleased bad-news disclosures.
7. **`unauthenticated`**: Blocked from all clinical endpoints (HTTP 401 Unauthorized).
8. **`attacker`**: Forged tokens, invalid roles, or SQLi/buffer overflow payloads (HTTP 401/403/422).

---

## 3. Comprehensive STRIDE Threat Analysis Matrix (v2.0.0)

| STRIDE Category | Threat ID | Threat Description & Attack Vector | Architectural Mitigation | Automated Verification Test |
|---|---|---|---|---|
| **Spoofing** | T-S1 | Caller claims privileged role via unauthenticated HTTP header (`X-Vigil-Role: admin`) | In `ENVIRONMENT != "local"`, `require_roles` strictly refuses header-based identities; requires cryptographically signed JWT. | `tests/acceptance_p5/test_api_security.py::test_production_rejects_header_claimed_roles` |
| **Spoofing** | T-S2 | Attacker signs forged JWTs using known default or weak development secret | System refuses to boot in staging/production if `JWT_SECRET_KEY` matches known default secret or is < 32 bytes. | `tests/acceptance_p5/test_api_security.py::test_default_jwt_secret_is_not_accepted_in_production` |
| **Spoofing** | T-S3 | Attacker replays stolen password or brute-forces weak credentials | Passwords hashed using salted `scrypt` with high memory/work cost ($N=2^{14}, r=8, p=1$). | `tests/acceptance_p5/test_api_security.py::test_passwords_are_hashed_with_a_slow_salted_kdf` |
| **Spoofing** | T-S4 | Cross-patient companion access or forged caregiver bearer tokens | Caregiver bearer tokens are hashed with SHA-256 at rest; query checks token hash and verifies scoped patient linkage. | `tests/security/test_penetration_suite.py::test_cross_patient_companion_token_isolation` |
| **Spoofing** | T-S5 | Unauthenticated actor pushes forged HL7 v2 messages | `/api/v1/hl7/oru-r01` protected by `require_roles(CLINICIAN, NURSE_CLERK, ADMIN)` and validates patient identity. | `tests/security/test_penetration_suite.py::test_hl7_ingestion_malformed_and_loinc_fuzzing` |
| **Tampering** | T-T1 | Malicious insider or DB admin deletes the last $N$ audit rows to hide unauthorized actions | Cryptographic SHA-256 hash chaining + external off-host append-only sink (`VIGIL_AUDIT_ANCHOR_PATH`). | `tests/acceptance_p7/test_p7_contract.py::test_audit_tail_deletion_is_detected_even_if_the_whole_database_is_rewritten` |
| **Tampering** | T-T2 | Attacker tampers with stored direct patient identifiers (MRN, external IDs) at rest | Field-level encryption using AES-128-CBC + HMAC-SHA256 (`MultiFernet`) with key rotation tooling. | `apps/api/tests/test_crypto.py::test_field_level_encryption_in_sqlite` |
| **Tampering** | T-T3 | Attacker bypasses No-Dismissal Safety Invariant via legacy endpoints | Legacy lab endpoints re-routed through canonical no-dismissal pipeline; database check constraints enforce `action != 'dismissed'`. | `tests/acceptance_p5/test_api_security.py::test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline` |
| **Tampering** | T-T4 | Client forges machine assignment, delay, or harm on `/schedule/confirm` | Server strictly derives delay, clinical urgency, and harm; client payload parameters are ignored or validated against DB state. | `tests/security/test_penetration_suite.py::test_forged_body_fuzzing_on_mutating_routes` |
| **Tampering** | T-T5 | SQL injection or parameter tampering in observation or patient payloads | Pydantic v2 strict typing + SQLAlchemy parameterized ORM queries; buffer limits enforced. | `tests/security/test_penetration_suite.py::test_forged_body_fuzzing_on_mutating_routes` |
| **Repudiation** | T-R1 | Clinician denies acknowledging an alert or ordering a critical repeat | Mandatory disposition and rationale recorded in immutable `AlertAcknowledgement` linked to actor ID in audit chain. | `tests/acceptance_p8/test_p8_contract.py::test_p8_disposition_audit_trail` |
| **Repudiation** | T-R2 | Nurse clerk or clinician denies bad-news disclosure unlock | `POST /patients/{id}/disclosure/unlock` records clinician identity, unlock reason, and timestamp in audit chain. | `tests/acceptance_p11/test_p11_contract.py::test_p11_bad_news_server_side_enforcement` |
| **Repudiation** | T-R3 | Patient denies consent grant or withdrawal | `ConsentRecord` table tracks immutable lifecycle with `granted_at`, `withdrawn_at`, scope, and hash-chained audit logging. | `tests/security/test_penetration_suite.py::test_consent_lifecycle_matrix_over_http` |
| **Information Disclosure** | T-I1 | Clinician or external caller reads records of a patient who has revoked or expired consent | `verify_patient_consent` is invoked prior to every read path across all roles; raises HTTP 403 if consent is absent/expired. | `tests/acceptance_p5/test_api_security.py::test_reads_require_consent_for_every_role` |
| **Information Disclosure** | T-I2 | Patient or caregiver attempts to enumerate roster or access foreign patient records | Explicit role boundary in consent engine restricts patient users strictly to their own matched record ID; roster listing requires staff roles. | `tests/security/test_penetration_suite.py::test_openapi_authorization_matrix` |
| **Information Disclosure** | T-I3 | Sensitive cancer diagnosis or biomarker numbers disclosed on shared household phones via reminders | Privacy-safe SMS/WhatsApp templates strictly omit analyte names, values, or cancer diagnosis. | `apps/api/tests/test_phase5b_platform.py::test_reminder_worker_privacy_safe_templates` |
| **Information Disclosure** | T-I4 | Mechanistic cohort generator exports unobserved latent truth into features (data leak) | `to_observations_dataframe` outputs NaN for unobserved values; canary tests enforce zero latent column leakage. | `tests/acceptance_p7/test_p7_contract.py::test_unobserved_values_are_never_exported` |
| **Information Disclosure** | T-I5 | Caregiver bearer tokens exposed in plaintext in API list responses | Tokens hashed at rest; API returns raw token exactly once on issuance; listing returns `share_token: null` and `token_preview`. | `tests/security/test_penetration_suite.py::test_companion_token_never_exposed_in_plaintext_listing` |
| **Information Disclosure** | T-I6 | Caregiver or patient views high-risk escalate assessment before clinician consultation | Bad-news gate returns HTTP 403 `disclosure_locked` on explainer routes and withholds `latest_risk` on caregiver summary until clinician unlocks. | `tests/acceptance_p11/test_p11_contract.py::test_p11_bad_news_server_side_enforcement` |
| **Information Disclosure** | T-I7 | Database error, syntax failure, or internal crash leaks file paths or SQL schema | Global exception handling in FastAPI sanitizes responses; zero internal stack trace or SQL text returned to client. | `tests/security/test_penetration_suite.py::test_error_message_leakage_and_stack_trace_hygiene` |
| **Denial of Service** | T-D1 | Offline client reconnects and replays duplicate batch mutations repeatedly | Idempotency engine tracks `client_mutation_id` in `idempotency_records`; replayed mutations return `already_applied` without re-running models. | `tests/security/test_penetration_suite.py::test_offline_sync_replay_and_idempotency` |
| **Denial of Service** | T-D2 | Worker process is killed or power interrupted mid-execution during reminder dispatch | Transactional task processing rolls back uncommitted batches; on worker restart, pending tasks resume cleanly. | `tests/resilience/test_worker_resilience.py::test_worker_kill_and_restart_lifecycle` |
| **Denial of Service** | T-D3 | Malformed HL7 message crashes parser or hangs service | Ingestion pipeline uses bounded parsing, robust error handling, and validates segment structure gracefully with HTTP 422. | `tests/security/test_penetration_suite.py::test_hl7_ingestion_malformed_and_loinc_fuzzing` |
| **Elevation of Privilege** | T-E1 | Low-privilege users (e.g. nurse clerks, patients) mutate clinical observations or audit chains | FastAPI dependency injection enforces RBAC matrix (`require_roles`) on all mutating and administrative endpoints. | `tests/security/test_penetration_suite.py::test_openapi_authorization_matrix` |
| **Elevation of Privilege** | T-E2 | Nurse clerk attempts to release bad-news disclosure unlock | Endpoint requires `require_roles(CLINICIAN, ADMIN)`; nurse clerk receives HTTP 403 Forbidden. | `tests/acceptance_p11/test_p11_contract.py::test_p11_bad_news_server_side_enforcement` |
| **Elevation of Privilege** | T-E3 | Attacker uses expired or revoked caregiver token to submit symptoms | Revocation status and expiration timestamp checked on every companion endpoint prior to mutation. | `tests/security/test_penetration_suite.py::test_companion_token_expiry_and_revocation_enforcement` |

---

## 4. Residual Risks & Next Steps (Phase 8b - 9)

1. **Hardware Security Module (HSM) Key Storage:** Root encryption keys (`FIELD_ENCRYPTION_KEYS`) currently reside in environment secrets; Phase 8b/9 will evaluate cloud KMS envelope encryption (ADR 0018).
2. **Rate Limiting & DDOS Shielding:** IP-level rate limiting and WAF rules are documented for production reverse-proxy deployment (NGINX/Cloudflare) and will be hardened in on-premise installation scripts.
3. **Automated Penetration Regression:** `tests/security/test_penetration_suite.py` runs in CI on every PR to prevent regression of authorization, consent, companion token, and error hygiene controls.
