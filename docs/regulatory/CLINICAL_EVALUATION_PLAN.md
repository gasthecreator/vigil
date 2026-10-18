# Vigil Precision Oncology — Clinical Evaluation Plan (CEP)

> [!WARNING]
> **DRAFT — UNREVIEWED REGULATORY ARTIFACT**
> This document is an engineering draft prepared for pre-market governance alignment.
> It has NOT been reviewed, audited, or approved by a Clinical Affairs Director, Principal Investigator, or Notified Body / Regulatory Authority.
> NOT AUTHORIZED FOR REGULATORY SUBMISSION OR CLINICAL TRIAL EXECUTION.

---

## 1. Regulatory Context & Scope
This Clinical Evaluation Plan (CEP) defines the continuous process for collecting, appraising, and analyzing clinical data to demonstrate the safety, clinical performance, and clinical benefit of the Vigil Precision Oncology Platform.

**Governing Standards:**
* **EU Medical Device Regulation (MDR 2017/745):** Article 61 & Annex XIV (Clinical Evaluation and Post-Market Clinical Follow-Up).
* **MDCG 2020-1:** Guidance on Clinical Evaluation (MDR) / Performance Evaluation (IVDR) of Medical Device Software.
* **MEDDEV 2.7/1 revision 4:** Guidelines on Medical Devices — Clinical Evaluation.
* **IMDRF SaMD N41:** Software as a Medical Device: Clinical Evaluation.

---

## 2. Clinical State of the Art (SOTA) & Clinical Background

### 2.1 Clinical Need & Context
In invasive breast cancer surveillance, conventional follow-up relies primarily on annual mammography and symptom-driven physical examinations. In resource-constrained settings (e.g. Sub-Saharan Africa), access to routine cross-sectional imaging (CT, PET-CT) is severely restricted by equipment scarcity, cost, and geographic disparity.

Serial blood-based tumor markers (CA 15-3 and CEA) provide an accessible, low-cost surveillance modality. However, adoption has historically been limited by:
1. **Biological and Analytical Noise:** Pre-analytical errors, assay drift, and benign inflammatory spikes create false alarms.
2. **Delayed Clinical Action:** Disconnected laboratory workflows result in weeks of delay between lab draws and clinician review.
3. **Radiotherapy Interruptions:** Severe linear accelerator downtime (MTTR 3–14 days) leads to uncontrolled tumor repopulation and excess recurrence harm.

### 2.2 SOTA Benchmarks & Guidelines
* ASCO Clinical Practice Guidelines (Post-Treatment Surveillance in Breast Cancer).
* NCCN Clinical Practice Guidelines in Oncology: Breast Cancer.
* Published kinetic studies demonstrating a 3–6 month biochemical lead-time over symptomatic relapse.

---

## 3. Clinical Objectives & Measurable Performance Endpoints

| Endpoint Category | Specific Endpoint Metric | Target Threshold | Method of Verification |
|---|---|---|---|
| **Clinical Performance** | Biochemical Recurrence Lead Time | $\ge 90$ days earlier than symptomatic presentation | Retrospective paired cohort comparison against radiologic confirmation. |
| **Diagnostic Accuracy** | Sensitivity for Relapse | $\ge 85.0\%$ (95% CI $\ge 80.0\%$) | Gold-standard clinical biopsy / PET-CT confirmation. |
| **False Alert Burden** | False Alarm Rate (Suppressed Noise) | $\le 0.10$ alerts per patient-year | M3 Bayesian noise adjudication vs raw threshold rule. |
| **Care Coordination** | 14-Day Diagnostic Follow-Up Completion | $\ge 80.0\%$ of escalated alerts resolved $\le 14$ days | M6 Follow-Up Guardian electronic workflow timestamps. |
| **Treatment Continuity** | Unplanned Radiation Gap Harm Reduction | Demonstration of non-inferiority to urgency heuristic in prospective setting | Realised interruption days and gap harm audits. |

---

## 4. Clinical Evidence Generation Strategy

```
  Phase A: Retrospective In-Silico Validation
  - Mechanistic synthetic cohorts (M1/M2/S8) + historical de-identified registry data
  - Verify absence of data leakage and validate algorithmic sensitivity
         │
         ▼
  Phase B: Silent Shadow Clinical Evaluation
  - Parallel background execution alongside standard of care across 2 pilot cancer centers
  - Clinicians blinded to Vigil alerts; compare time-to-detection vs standard practice
         │
         ▼
  Phase C: Prospective Pragmatic Multi-Center Clinical Trial
  - Interventional decision-support study with human-in-the-loop clinician confirmation
  - Primary outcome: Lead time to intervention and 14-day diagnostic adherence
         │
         ▼
  Phase D: Post-Market Clinical Follow-Up (PMCF)
  - Continuous real-world monitoring of false-alarm rates, alert overrides, and subgroup fairness
```

---

## 5. Benefit-Risk Determination
The anticipated clinical benefits of Vigil include earlier detection of localized, salvageable recurrence and minimized treatment delays in high-risk cancers. The clinical risks (primarily false-positive anxiety and unnecessary diagnostic workups) are systematically mitigated by the M3 plausibility gate, server-side bad-news withholding, and mandatory clinician adjudication.
