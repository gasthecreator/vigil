# Vigil Platform — Data Protection Impact Assessment (DPIA)

> [!WARNING]
> **DRAFT — UNREVIEWED REGULATORY ARTIFACT**
> This document is an engineering draft prepared for pre-market governance alignment.
> It has NOT been reviewed, audited, or approved by a Data Protection Officer (DPO), Legal Counsel, or Supervisory Authority (e.g., Nigeria Data Protection Commission [NDPC], European Data Protection Board [EDPB]).
> NOT AUTHORIZED FOR OPERATIONAL COMPLIANCE OR REGULATORY FILING.

---

## 1. Executive Summary & Legal Framework
This Data Protection Impact Assessment (DPIA) evaluates the data processing activities of the Vigil Precision Oncology Platform in compliance with:
* **Nigeria Data Protection Act (NDPA 2023):** Sections 24–39 (Principles of Personal Data Processing, Rights of Data Subjects, Processing Sensitive Personal Data, Data Protection Impact Assessment).
* **EU General Data Protection Regulation (GDPR 2016/679):** Article 9 (Special Categories of Data), Article 25 (Data Protection by Design and by Default), Article 35 (Data Protection Impact Assessment).
* **HIPAA Security & Privacy Rules (45 CFR Part 160/164):** Technical and administrative safeguards for Electronic Protected Health Information (ePHI).

---

## 2. Description of Processing & Data Flows

### 2.1 Processed Data Categories
1. **Direct Identifiers (PII):** Medical Record Numbers (MRN), National Identification / Hospital IDs, Patient full names, contact telephone numbers (SMS/WhatsApp).
2. **Special Category / Sensitive Personal Health Data:** Age, cancer staging, receptor status (ER, PR, HER2), serial serum biomarker kinetics (CA 15-3, CEA), symptom severity logs, radiotherapy fraction courses, treatment delay intervals.
3. **Operational & Audit Telemetry:** Clinician user IDs, electronic signatures / timestamps, alert disposition rationale, access logs, machine downtime events.

### 2.2 End-to-End Data Flow Architecture
```
  [ Patient / Clinic ] ──(TLS 1.3 / JWT)──> [ API Gateway & Consent Check ]
                                                        │
                      ┌─────────────────────────────────┴─────────────────────────────────┐
                      ▼                                                                   ▼
       [ Blind Index Engine ]                                              [ Crypto Vault (MultiFernet) ]
      (HMAC-SHA256 Blind Index)                                            (AES-128-CBC Direct Identifiers)
                      │                                                                   │
                      └─────────────────┬─────────────────────────────────────────────────┘
                                        ▼
                         [ Relational Database (Encrypted) ]
                                        │
                                        ▼
                        [ Hash-Chained Audit Ledger ] ──> [ WORM Sink ]
```

---

## 3. Lawful Basis for Processing
1. **Primary Care Surveillance:** Explicit, documented patient consent (NDPA §28(1)(a), GDPR Art. 9(2)(a)). Consent is granular, recorded in immutable `ConsentRecord`, and verifiable over HTTP.
2. **Direct Medical Care / Vital Interests:** Processing necessary for medical diagnosis and treatment by healthcare professionals bound by clinical confidentiality (NDPA §28(1)(c), GDPR Art. 9(2)(h)).
3. **Retrospective Quality Assurance:** Conditioned strictly upon active patient consent (ADR 0017). Patients who revoke or withdraw consent are programmatically excluded from retrospective quality audit pipelines.

---

## 4. Privacy Risk Identification & Architectural Mitigations

| Risk ID | Threat Scenario | Likelihood | Impact | Inherent Risk | Architectural Mitigations | Residual Risk |
|---|---|---|---|---|---|---|
| **PR-1** | Database compromise leaks plaintext patient MRNs and identities | Medium | Critical | High | Field-level symmetric encryption (`MultiFernet` AES-128-CBC + HMAC) on direct identifiers. Deterministic HMAC-SHA256 blind indexing for query lookups without exposing plaintext. | Low |
| **PR-2** | Unconsented clinical surveillance or access after patient withdrawal | Medium | High | High | Server-side consent gate (`verify_patient_consent`) enforced on every read route. Immediate HTTP 403 on revoked/expired consent across all roles. | Very Low |
| **PR-3** | Unauthorized caregiver or family member accesses foreign patient data | Low | High | Medium | Scoped bearer tokens hashed with SHA-256 at rest; zero-plaintext in API listings; automatic 30-day expiry; instant revocation via patient or clinician. | Low |
| **PR-4** | Malicious DB admin alters or erases access history to conceal data exfiltration | Low | Critical | High | Cryptographically chained SHA-256 audit ledger (`AuditLedgerRecord`) anchored to external WORM append-only sink. | Very Low |
| **PR-5** | Disclosure of sensitive cancer diagnosis via automated SMS/WhatsApp notifications | Medium | High | High | Privacy-safe templates strictly exclude disease names, analyte values, or medical terms. Message only prompts clinic appointment check-in. | Low |
| **PR-6** | Premature disclosure of alarming escalate-level biomarker spikes causing patient distress | Medium | Medium | Medium | Bad-news server-side gate: Explainer routes return HTTP 403 `disclosure_locked` and caregiver summary withholds risk interpretation until clinician unlocks. | Low |

---

## 5. Data Subject Rights Implementation
* **Right to Withdraw Consent:** Implemented via `POST /api/v1/patients/{id}/consent` with `granted: false`. Propagation takes effect immediately over HTTP across all dependent services.
* **Right to Access & Portability:** Standardized JSON and FHIR R4 resource export capabilities.
* **Right to Rectification:** Clinician audit-logged amendment of observations with recorded rationale.

---

## 6. DPIA Conclusion & Sign-Off Requirement
The technical architecture of Vigil provides defense-in-depth safeguards that reduce all identified privacy risks to an acceptable residual level. Formal deployment requires sign-off from the facility Data Protection Officer and clinical governance board.
