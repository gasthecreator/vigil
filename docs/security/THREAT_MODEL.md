# Vigil STRIDE Threat Model v1

**Document Version:** 1.0.0  
**Phase:** Phase 5 Exit Gate Deliverable  
**Governing Standard:** `docs/MASTER_PLAN.md` §9.3, §11.2 (Hazard Log), and §14 (WP5.2, WP5.5)  
**Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)  

---

## 1. System Overview & Trust Boundaries

The Vigil Precision Oncology Platform ingests laboratory observations, executes plausibility adjudication (M3), sequential recurrence detection (K2), and verified clinical narrative drafting (M5), coordinating clinical follow-up actions via the Follow-Up Guardian (M6).

```
                      TRUST BOUNDARY 1: External Untrusted Networks
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
     [ Hospital LIS / EHR ]                  [ Clinician PWA / Companion ]
      (HL7 v2 / FHIR R4 / CSV)                (Bearer JWT / Session Auth)
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │ TLS 1.3
                      TRUST BOUNDARY 2: API Gateway & Auth Barrier
                                     │
                    ┌────────────────┴────────────────┐
                    │       FastAPI API Service       │
                    │  (RBAC, Consent Engine, M3/M5)  │
                    └────────────────┬────────────────┘
                                     │
                      TRUST BOUNDARY 3: Core Persistence & Storage
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
 [ Relational DB ]         [ Field Encryption ]       [ External WORM Sink ]
  (Check Constraints,       (AES-128 / MultiFernet     (Audit Anchor Append-Only
   No-Dismissal Invariant)   Direct Identifiers)        Head Hash Commitments)
```

---

## 2. STRIDE Threat Analysis Matrix

Each identified threat is mapped to its architectural mitigation, residual risk assessment, and committed verification test.

| STRIDE Category | Threat ID | Threat Description & Attack Vector | Architectural Mitigation | Automated Verification Test |
|---|---|---|---|---|
| **Spoofing** | T-S1 | Caller claims privileged role via unauthenticated HTTP header (`X-Vigil-Role: admin`) | In `ENVIRONMENT != "local"`, `require_roles` strictly refuses header-based identities; requires cryptographically signed JWT. | `tests/acceptance_p5/test_api_security.py::test_production_rejects_header_claimed_roles` |
| **Spoofing** | T-S2 | Attacker signs forged JWTs using known default or weak development secret | System refuses to boot in staging/production if `JWT_SECRET_KEY` matches known default secret or is < 32 bytes. | `tests/acceptance_p5/test_api_security.py::test_default_jwt_secret_is_not_accepted_in_production` |
| **Spoofing** | T-S3 | Attacker replays stolen password or brute-forces weak credentials | Passwords hashed using salted `scrypt` with high memory/work cost ($N=2^{14}, r=8, p=1$). | `tests/acceptance_p5/test_api_security.py::test_passwords_are_hashed_with_a_slow_salted_kdf` |
| **Tampering** | T-T1 | Malicious insider or DB admin deletes the last $N$ audit rows to hide unauthorized actions | Cryptographic SHA-256 hash chaining + external off-host append-only sink (`VIGIL_AUDIT_ANCHOR_PATH`). | `tests/acceptance_p7/test_p7_contract.py::test_audit_tail_deletion_is_detected_even_if_the_whole_database_is_rewritten` |
| **Tampering** | T-T2 | Attacker tampers with stored direct patient identifiers (MRN, external IDs) at rest | Field-level encryption using AES-128-CBC + HMAC-SHA256 (`MultiFernet`) with key rotation tooling. | `apps/api/tests/test_crypto.py::test_field_level_encryption_in_sqlite` |
| **Tampering** | T-T3 | Attacker bypasses No-Dismissal Safety Invariant via legacy endpoints | Legacy lab endpoints re-routed through canonical no-dismissal pipeline; database check constraints enforce `action != 'dismissed'`. | `tests/acceptance_p5/test_api_security.py::test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline` |
| **Repudiation** | T-R1 | Clinician denies acknowledging an alert or ordering a critical repeat | Mandatory disposition and rationale recorded in immutable `AlertAcknowledgement` linked to actor ID in audit chain. | `apps/api/tests/test_api_endpoints.py`, `apps/api/tests/test_auth_rbac_consent.py` |
| **Information Disclosure** | T-I1 | Clinician or external caller reads records of a patient who has revoked or expired consent | `verify_patient_consent` is invoked prior to every read path across all roles; raises HTTP 403 if consent is absent/expired. | `tests/acceptance_p5/test_api_security.py::test_reads_require_consent_for_every_role` |
| **Information Disclosure** | T-I2 | Patient role attempts to enumerate or access other patients' records | Explicit role boundary in consent engine restricts patient users strictly to their own matched record ID. | `apps/api/tests/test_auth_rbac_consent.py::test_patient_role_cannot_read_foreign_records` |
| **Information Disclosure** | T-I3 | Sensitive cancer diagnosis or biomarker numbers disclosed on shared household phones via reminders | Privacy-safe SMS/WhatsApp templates strictly omit analyte names, values, or cancer diagnosis. | `apps/api/tests/test_phase5b_platform.py::test_reminder_worker_privacy_safe_templates` |
| **Information Disclosure** | T-I4 | Mechanistic cohort generator exports unobserved latent truth into features (data leak) | `to_observations_dataframe` outputs NaN for unobserved values; canary tests enforce zero latent column leakage. | `tests/acceptance_p7/test_p7_contract.py::test_unobserved_values_are_never_exported` |
| **Denial of Service** | T-D1 | Offline client reconnects and replays duplicate batch mutations repeatedly | Idempotency engine tracks `client_mutation_id` in `idempotency_records`; replayed mutations return `already_applied` without re-running models. | `apps/api/tests/test_sync.py::test_offline_sync_batch_successful_replay` |
| **Denial of Service** | T-D2 | Worker process is killed or power interrupted mid-execution during reminder dispatch | Transactional task processing rolls back uncommitted batches; on worker restart, pending tasks resume cleanly. | `tests/resilience/test_worker_resilience.py::test_worker_kill_and_restart_lifecycle` |
| **Elevation of Privilege** | T-E1 | Low-privilege users (e.g. nurse clerks, patients) mutate clinical observations or audit chains | FastAPI dependency injection enforces RBAC matrix (`require_roles`) on all mutating and administrative endpoints. | `apps/api/tests/test_auth_rbac_consent.py::test_role_x_endpoint_x_consent_matrix` |

---

## 3. Residual Risks & Future Work (Phase 8 Safety & Security Package)

1. **Hardware Security Module (HSM) Key Storage:** Root encryption keys (`FIELD_ENCRYPTION_KEYS`) currently reside in environment secrets; Phase 8 will add HSM / PKCS#11 / cloud KMS envelope encryption.
2. **Rate Limiting & DDOS Shielding:** IP-level rate limiting and WAF rules are documented for production reverse-proxy deployment (NGINX/Cloudflare) and will be hardened in Phase 8 on-premise installation guides.
