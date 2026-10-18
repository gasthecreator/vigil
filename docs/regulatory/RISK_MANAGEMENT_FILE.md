# Vigil Precision Oncology — Risk Management File (RMF)

> [!WARNING]
> **DRAFT — UNREVIEWED REGULATORY ARTIFACT**
> This document is an engineering draft prepared for pre-market governance alignment.
> It has NOT been reviewed, audited, or approved by a Risk Management Officer, Quality Director, or Notified Body / Regulatory Authority.
> NOT AUTHORIZED FOR REGULATORY SUBMISSION OR CLINICAL COMPLIANCE FILING.

---

## 1. Scope & Standards Compliance
This Risk Management File (RMF) documents the systematic identification, analysis, control, and monitoring of risks associated with the Vigil Precision Oncology Platform throughout its product lifecycle.

**Governing Standards:**
* **ISO 14971:2019 / EN ISO 14971:2019:** Medical devices — Application of risk management to medical devices.
* **ISO/TR 24971:2020:** Medical devices — Guidance on the application of ISO 14971.
* **IEC 62304:2006+AMD1:2015:** Medical device software — Software life cycle processes (Assigned Software Safety Class: **Class B**).
* **IEC 82304-1:2016:** Health software — Part 1: General requirements for product safety.

---

## 2. Risk Evaluation & Acceptability Matrix

Risks are evaluated using a 5×5 Severity and Probability matrix before and after implementation of risk controls:

### Severity Categories:
1. **Negligible:** Inconvenience, slight delay without clinical impact.
2. **Minor:** Temporary discomfort, minor diagnostic delay, reversible harm.
3. **Serious:** Substantial treatment delay, unnecessary invasive biopsy, moderate distress.
4. **Critical:** Severe progression of disease due to missed recurrence, prolonged treatment interruption.
5. **Catastrophic:** Death or irreversible terminal progression.

### Probability Categories:
- **P1 (Improbable):** $< 10^{-5}$ per patient-year
- **P2 (Remote):** $10^{-5} \text{ to } 10^{-4}$ per patient-year
- **P3 (Occasional):** $10^{-4} \text{ to } 10^{-2}$ per patient-year
- **P4 (Probable):** $10^{-2} \text{ to } 10^{-1}$ per patient-year
- **P5 (Frequent):** $> 10^{-1}$ per patient-year

```
Severity     │  P1 (Improbable)  P2 (Remote)  P3 (Occas.)  P4 (Prob.)  P5 (Freq.)
─────────────┼──────────────────────────────────────────────────────────────────
Catastrophic │      Medium          High         High         Unacc.     Unacc.
Critical     │      Low            Medium        High         High       Unacc.
Serious      │      Low             Low         Medium        High       High
Minor        │      Negligible      Low          Low         Medium      Medium
Negligible   │      Negligible   Negligible      Low          Low        Low
```

---

## 3. Linkage to Master Hazard Log (`HAZARD_LOG.md`)

The comprehensive risk analysis is operationalized and maintained in the Vigil Hazard Log (`docs/safety/HAZARD_LOG.md`). All 22 clinical hazards (H1 through H22) are governed by automated test assertions verified in CI via `scripts/verify_hazard_log.py`:

| Hazard ID | Clinical Scenario & Root Cause | Inherent Risk | Risk Control Mitigation | Post-Mitigation Risk | Verification Test in AST |
|---|---|---|---|---|---|
| **H1** | Silent dismissal of true recurrence alert | Critical (P3) | Database check constraints prohibit `action = 'dismissed'`. Mandatory disposition & rationale required. | Low (P1) | `test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline` |
| **H2** | False positive alert from single assay spike | Serious (P4) | M3 Sequential Bayes filters single-point spikes, ordering repeat verification draws. | Low (P2) | `test_p8_contract.py` |
| **H3** | Stale or unmonitored pending follow-up task | Critical (P3) | Automated escalation triggers after 14 days of task inactivity. | Low (P1) | `test_escalation_after_grace_period` |
| **H4** | Caregiver panics from raw bad-news disclosure | Serious (P4) | Server-side bad-news gate withholds escalate-level findings until clinician unlocks. | Low (P1) | `test_p11_bad_news_server_side_enforcement` |
| **H5** | Scheduling algorithm starves urgent curative cases | Critical (P4) | CP-SAT solver incorporates non-linear interruption penalty and explicit fairness bounds. | Medium (P2) | `test_m7_fairness_gap_bound` |
| **H6** | Attacker tampers with linac capacity / schedule | Critical (P2) | Server strictly derives delays and urgency; ignores client-injected harm values. | Low (P1) | `test_forged_body_fuzzing_on_mutating_routes` |
| **H7** | Data leakage: unobserved latent state in features | Serious (P3) | Mechanistic pipeline outputs NaN for unobserved values; canary checks enforce zero leakage. | Negligible (P1) | `test_unobserved_values_are_never_exported` |
| **H8** | Audit trail deletion hides unauthorized changes | Critical (P2) | Cryptographically chained SHA-256 audit ledger with external WORM append-only anchor. | Low (P1) | `test_audit_tail_deletion_is_detected...` |
| **H9** | Unconsented clinical surveillance access | Critical (P3) | Strict server-side verification of active, non-withdrawn consent on every read route. | Low (P1) | `test_reads_require_consent_for_every_role` |
| **H10** | Offline synchronization replay / data duplication | Serious (P3) | Idempotency engine tracks `client_mutation_id` and rejects duplicates. | Negligible (P1) | `test_offline_sync_replay_and_idempotency` |
| **H11** | Worker process crash leaves tasks unhandled | Serious (P3) | Atomic database transactions with rollback and idempotent retry on worker restart. | Low (P1) | `test_worker_kill_and_restart_lifecycle` |
| **H12** | Plaintext bearer token leakage in caregiver list | Serious (P3) | Scoped tokens hashed at rest (SHA-256); listing endpoint returns `share_token: null`. | Negligible (P1) | `test_companion_token_never_exposed...` |
| **H13** | Explainer narrative hallucinates clinical guidance | Critical (P3) | M5 narrative drafting is strictly grounded in verified rule-based templates and audit context. | Low (P1) | `test_explainer_clinical_context` |
| **H14** | Multi-facility tenant data spill in quality audits | Critical (P2) | Audit queries strictly filtered by facility UUID; cross-tenant access blocked. | Low (P1) | `test_cross_facility_isolation` |
| **H15** | Silent loss of follow-up after repeated outreach | Serious (P4) | Automated flag `lost_to_follow_up_after_N_attempts` mandates community health referral. | Low (P2) | `test_lost_to_follow_up_escalation` |
| **H16** | Biomarker assay unit mismatch (U/mL vs ng/mL) | Critical (P3) | Ingestion normalizer enforces strict LOINC-mapped unit conversion and range validation. | Low (P1) | `test_hl7_ingestion_malformed_and_loinc_fuzzing` |
| **H17** | Withdrawn patient included in quality analytics | Serious (P3) | Server-side extraction pipeline strictly skips patients without active consent (ADR 0017). | Low (P1) | `test_p13_quality_audit_consent_filtering` |
| **H18** | Solver status timeout without clinical notification | Serious (P3) | Fallback heuristics immediately engage on CP-SAT timeout with explicit audit logging. | Low (P1) | `test_solver_fallback_on_timeout` |
| **H19** | Privacy breach via descriptive SMS reminder | Serious (P4) | Templates omit all cancer terms, analyte names, and medical details. | Low (P1) | `test_reminder_worker_privacy_safe_templates` |
| **H20** | Confounded observational causal inference bias | Serious (P4) | Sensitivity analysis bounds unmeasured confounding via E-values and negative controls. | Low (P2) | `test_causal_bias_e_value_bounds` |
| **H21** | Attacker tampers with direct patient IDs at rest | Critical (P2) | Field-level `MultiFernet` encryption (AES-128-CBC) protects all stored identifiers. | Low (P1) | `test_field_level_encryption_in_sqlite` |
| **H22** | M7 CP-SAT solver harm gap under downtime | Critical (P4) | Prominently badged `"unvalidated in simulation"` in UI and API; study published in full. | Low (P2) | `test_unvalidated_status_badge` |

---

## 4. Overall Benefit-Risk Conclusion
All identified hazards have been reduced as low as reasonably practicable (ALARP) through design controls, automated invariants, and clinician-in-the-loop safeguards. The clinical benefit of early recurrence detection and organized continuity management substantially outweighs the residual risk.
