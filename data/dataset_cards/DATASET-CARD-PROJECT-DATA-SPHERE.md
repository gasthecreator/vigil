# Dataset Card: Project Data Sphere (PDS) Breast Cancer Comparator Arms

## 1. Dataset Summary
- **Source:** Project Data Sphere, LLC (CEO Roundtable on Cancer).
- **Tier:** `T-P (De-identified Clinical Trial Comparator Arms)`
- **Scope:** Multi-center randomized phase III oncology clinical trial comparator cohorts (standard-of-care arms), containing patient-level longitudinal laboratory flow sheets and adverse event timelines.
- **Intended Use:** Validating longitudinal laboratory kinetics, real-world protocol visit adherence, and clinical chemistry variance under controlled trial conditions.
- **Out-of-Scope Use:** Trial cohorts have strict protocol inclusion criteria (ECOG 0–1, preserved organ function) and are not representative of resource-constrained LMIC populations.

## 2. Key CDISC SDTM Domain Tables
- `DM` (Demographics): `USUBJID`, `AGE`, `SEX`, `RACE`, `ARM`, `RFSTDTC`.
- `LB` (Laboratory Test Results): `USUBJID`, `LBTESTCD`, `LBTEST`, `LBCAT`, `LBORRES`, `LBORRESU`, `LBSTRESN`, `LBSTRESU`, `LBNRIND`, `LBDTC`, `VISITNUM`.
- `AE` (Adverse Events): `USUBJID`, `AETERM`, `AESEV`, `AETOXGR`, `AESTDTC`, `AEENDTC`.
- `RS` / `TU` (Tumor Response / Identification): RECIST assessments, progression dates.

## 3. Access Protocol
- **Application Process:** Online registration, organizational verification, and electronic signing of the Project Data Sphere Data Use Agreement; human action required (H-003). Turnaround ~7 business days.
