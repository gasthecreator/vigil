# Dataset Card: MIMIC-IV Oncology Laboratory Cohort

## 1. Dataset Summary
- **Source:** PhysioNet / Beth Israel Deaconess Medical Center / MIT Laboratory for Computational Physiology.
- **Tier:** `T-P (Dense Clinical Laboratory Series)`
- **Scope:** Intensive care and hospital admission records for adult cancer patients identified by ICD-9/ICD-10 malignant neoplasm diagnosis codes (e.g., `174.*`, `C50.*`).
- **Intended Use:** Validating dense laboratory time-series dynamics, cross-analyte correlation structures (e.g., AST/ALT ratios, albumin/calcium binding), and pre-training representations for self-supervised sequence encoders.
- **Out-of-Scope Use:**
  > [!WARNING] ICU Selection Bias
  > MIMIC-IV reflects acute intensive care encounters with severe acute illness, sepsis, shock, and organ failure. It is NOT an outpatient surveillance cohort and MUST NOT be used for estimating outpatient recurrence probabilities.

## 2. Key Database Tables & Relational Schema
- `patients`: `subject_id`, `gender`, `anchor_age`, `anchor_year`, `dod`.
- `admissions`: `hadm_id`, `admittime`, `dischtime`, `hospital_expire_flag`.
- `diagnoses_icd`: `icd_code`, `icd_version` (ICD-9 codes 140–208, ICD-10 codes C00–C96).
- `labevents`: `labevent_id`, `itemid`, `charttime`, `valuenum`, `valueuom`, `flag`.
- `d_labitems`: Dictionary mapping `itemid` to LOINC, fluid, and category.

## 3. Access Protocol
- **Credentialing:** CITI "Data or Specimens Only Research" training certification + PhysioNet credentialed account with signed DUA (PhysioNet Credentialing; human action H-004).
