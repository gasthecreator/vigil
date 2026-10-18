# Vigil Precision Oncology — Predetermined Change Control Plan (PCCP)

> [!WARNING]
> **DRAFT — UNREVIEWED REGULATORY ARTIFACT**
> This document is an engineering draft prepared for pre-market governance alignment.
> It has NOT been reviewed, audited, or approved by the Responsible Regulatory Official or Competent Authority (e.g., US FDA Center for Devices and Radiological Health [CDRH]).
> NOT AUTHORIZED FOR REGULATORY SUBMISSION OR CLINICAL CHANGE MANAGEMENT.

---

## 1. Scope & Regulatory Framework
This Predetermined Change Control Plan (PCCP) establishes the pre-specified boundaries, verification criteria, and governance procedures for post-market modifications to AI/ML and optimization models within the Vigil SaMD platform.

This plan adheres to:
* **FDA Guidance:** *Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence/Machine Learning (AI/ML)-Enabled Device Software Functions* (April 2023).
* **ISO/IEC 62304 / ISO 14971:** Medical device software lifecycle and risk management.
* **Good Machine Learning Practice (GMLP):** Joint principles by US FDA, Health Canada, and UK MHRA.

---

## 2. Description of Anticipated Modifications

The following modifications are pre-specified within the scope of this PCCP:

| Modification ID | Component | Description of Modification | Trigger Condition |
|---|---|---|---|
| **MOD-01** | **M3 Anomaly Adjudication** | Laboratory assay reference range and noise variance re-calibration | Introduction of new clinical analyzer hardware or standardized assay kits (e.g. Roche Cobas vs Abbott Architect). |
| **MOD-02** | **K2 Recurrence Detector** | Sequential Bayes prior distribution and transition probability updates | Post-market epidemiological shift in recurrence kinetics or local cohort subtype prevalence (e.g., higher TNBC frequency). |
| **MOD-03** | **M7 Continuity Solver** | Linac uptime parameters, breakdown rate ($\lambda$), and repair distribution (MTTR) updates | Empirical site-specific telemetry indicating machine service life changes or maintenance contract adjustments. |
| **MOD-04** | **M5 Narrative Explainer** | Template refinements, clinical lexicon expansion, and multi-language localization (e.g., Yoruba, Hausa, Igbo translations) | Clinician user feedback and comprehension audits. |

---

## 3. Modification Protocol & Verification Acceptance Bounds

Every model modification must satisfy strict quantitative acceptance criteria on frozen gold-standard evaluation datasets before release:

### 3.1 Quantitative Performance Bounds
1. **K2 Recurrence Detection Sensitivity:**
   - Lead time advantage $\ge 90$ days prior to conventional radiologic detection.
   - Sensitivity for true biochemical relapse $\ge 0.85$ (95% CI lower bound $\ge 0.80$).
   - False positive alert rate $\le 0.10$ per patient-year.
2. **M3 Plausibility Specificity:**
   - False alarm suppression rate $\ge 0.90$ on confirmed pre-analytical spikes.
   - Zero misclassification of true consecutive double-positive elevations.
3. **M7 Scheduling Realised Harm Invariant:**
   - Realised interruption harm under stochastic simulation must not exceed baseline heuristic ($< 0.020$ mean harm per patient).
   - Any solver modification that exhibits an objective-vs-realised harm correlation $r < 0.50$ remains explicitly badged `"unvalidated in simulation"` in both UI and API.

---

## 4. Retraining, Testing & Deployment Workflow

```
  [ Performance Drift / Trigger ]
                 │
                 ▼
  [ 1. Retraining Pipeline (Dev Seeds Only) ]
                 │
                 ▼
  [ 2. Frozen Evaluation Set Validation (Zero Data Leakage) ]
                 │
                 ▼
  [ 3. Automated Regression & Contract Tests (acceptance_p*) ]
                 │
                 ▼
  [ 4. Clinical Governance & ADR Filing (ADR-Required) ]
                 │
                 ▼
  [ 5. Staged Canary / Shadow Deployment (Parallel Execution) ]
                 │
                 ▼
  [ 6. Production Rollout with Cryptographic Audit Anchoring ]
```

---

## 5. Safeguards & Emergency Rollback Procedures
1. **Zero Silent Changes:** No dynamic in-situ learning occurs on live client hardware. All model weights and parameters are static, versioned, and verified at startup.
2. **Deterministic Rollback:** In the event of anomalous clinical alert distributions, high false-alarm rates, or solver infeasibilities post-deployment:
   - System automatically reverts to the previous validated parameter set via feature flag toggle or automated rollback migration.
   - Clinical users and administrators receive automated advisory alerts.
3. **Audit Ledger Logging:** Every parameter adjustment, model version switch, and rollback is recorded immutably in the hash-chained `AuditLedgerRecord`.
