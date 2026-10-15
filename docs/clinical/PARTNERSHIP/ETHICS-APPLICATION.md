# Institutional Health Research Ethics Committee (HREC) Application Draft (docs/clinical/PARTNERSHIP/ETHICS-APPLICATION.md)

**Target Body:** Health Research Ethics Committee (HREC), [Tertiary Partner Teaching Hospital, Nigeria]  
**National Regulatory Alignment:** National Health Research Ethics Committee (NHREC) National Code for Health Research Ethics (NCHRE), Nigeria Data Protection Act 2023 (NDPA).  
**Protocol Identification:** VIGIL-REC-2026-01  
**Submission Version:** 1.0.0 (Phase 1 Draft)

---

## 1. Administrative Information

* **Project Title:** *Retrospective Multi-Center Evaluation of Longitudinal Biomarker Surveillance for Early Detection of Metastatic Breast Cancer Recurrence in Nigerian Tertiary Oncology Centers*
* **Principal Investigator (PI):**  
  - Name: Gideon Sanni
  - Affiliation: Vigil Oncology Research Initiative (`gasthecreator/vigil`)
  - Contact: [Authorised Contact Email / Phone]
* **Local Co-Principal Investigator (Host Institution):**  
  - Name: [Consultant Radiation / Clinical Oncologist, Department of Oncology]
  - Institution: [Partner Teaching Hospital, Nigeria]
* **Co-Investigators:**  
  - [Consultant Chemical Pathologist / Head of Chemical Pathology]
  - [Consultant Surgical Oncologist / General Surgery]
* **Proposed Study Duration:** 12 Months (Retrospective data abstraction: 4 months; Computational analysis: 6 months; Reporting & publication: 2 months).
* **Funding Source:** Self-funded / Philanthropic Research Initiative; Zero commercial sponsorship; Zero financial cost to host institution or patients.

---

## 2. Plain Language Lay Summary

Breast cancer is the leading cause of cancer deaths among Nigerian women. A major tragedy in our healthcare environment is that women often present late, and even after successful initial surgery and chemotherapy, many experience recurrence (cancer returning and spreading to the liver, lungs, bones, or brain). 

Because advanced scans like CT or MRI are very expensive and patients pay out-of-pocket, doctors often order regular, affordable blood tests (liver function tests, CA 15-3, blood counts). However, in extremely busy clinics, small changes in blood test results that signal the cancer is starting to return can easily be missed or mistaken for normal lab variation until the patient becomes severely ill.

This research study analyzes historical (past) patient medical records and laboratory results from 2014 to 2024 to test an intelligent computer platform called **Vigil**. Vigil checks whether tracking small changes in blood tests over time can reliably warn doctors of cancer spread months before clinical symptoms appear. 

This study looks only at historical case files. It does not test any medication, requires no new blood draws, involves zero physical risk to any patient, and completely removes all patient names, addresses, and hospital numbers before analysis to protect patient privacy.

---

## 3. Clinical Background & Public Health Justification

1. **Sub-Saharan African Burden:** Nigerian breast cancer patients present at a younger median age (45–48 years) and with more aggressive, hormone-negative tumor biology (25–35% TNBC) compared to high-income populations [E7, E8].
2. **Economic Barriers:** Over 80% of patients finance care out-of-pocket. Routine scheduled surveillance imaging (CT/PET) is cost-prohibitive for the vast majority of patients.
3. **Surveillance Gap:** International guidelines (ASCO/ESMO) advise against serial tumor markers in asymptomatic Western patients due to high false-alarm rates when using simplistic static cutoffs [E1]. However, applying dynamic longitudinal anomaly detection that accounts for biological variation ($CV_i$) and organ-specific risk can transform routine affordable blood tests into an early warning system.
4. **Local Calibration:** To be clinically trustworthy, algorithmic decision support must be calibrated on real Nigerian clinical data rather than imported uncritically from Western datasets.

---

## 4. Study Methodology & Data Flow

* **Design:** Retrospective longitudinal chart-review cohort study.
* **Target Sample Size:** 300 to 500 patient case files of curative-intent breast cancer treated between 2014 and 2024.
* **Data Abstraction:** Trained resident doctors / data clerks will extract de-identified records onto standardized eCRF forms.
* **Variables:** Baseline pathology (stage, grade, ER/PR/HER2), serial laboratory results (CA 15-3, CEA, ALT, AST, Creatinine, CBC), and confirmed metastatic recurrence dates/sites.
* **Zero Intervention:** No clinical decisions will be altered retrospectively; the analysis is purely observational and analytical.

---

## 5. Human Subjects Protection & Ethical Risk Assessment

| Ethical Domain | Risk Assessment | Mitigation Measure |
|---|---|---|
| **Physical Harm** | **None** | Purely retrospective review of archived records; zero physical intervention. |
| **Psychological Harm** | **None** | No patient contact, questionnaires, or active recall of trauma. |
| **Confidentiality / Privacy** | **Minimal** | Removal of all direct identifiers; stochastic date-shifting; AES-256 encrypted storage. |
| **Stigmatization** | **None** | Aggregated statistical reporting; zero individual case narratives published. |

---

## 6. Formal Request & Justification for Waiver of Informed Consent

In accordance with **Section 11 (Informed Consent Waiver in Secondary Data Research)** of the National Code for Health Research Ethics (NHREC):

The Principal Investigator formally requests a **full waiver of individual informed consent** based on the following statutory criteria:
1. **Minimal Risk:** The research involves no more than minimal risk to participants. Data are entirely retrospective and anonymized.
2. **Impracticability:** The study reviews cases dating back to 2014. A substantial proportion of patients are deceased, relocated, or lost to follow-up, making direct contact impossible or causing unnecessary distress to bereaved family members.
3. **Rights & Welfare:** The waiver will not adversely affect the rights, welfare, or clinical care of the participants.
4. **Public Health Value:** The study provides vital epidemiologic and diagnostic knowledge that directly addresses the high mortality of breast cancer in Nigeria.

---

## 7. Data Security and Confidentiality Architecture

1. **On-Site Pseudonymization:** All direct identifiers (names, MRNs, phone numbers) are stripped within the hospital records department. A study UUID is assigned.
2. **Key Custody:** The linkage key mapping UUIDs to hospital numbers remains exclusively with the local Host Institution Co-PI in a password-protected, encrypted file on an offline institutional computer. The research team receives only de-identified data.
3. **Temporal Date-Shifting:** Exact calendar dates are shifted by an individual constant offset, preventing date-based re-identification while preserving exact day intervals between clinical visits.
4. **Cryptographic Protection:** All research files are encrypted using AES-256 at rest and transmitted using secure TLS 1.3 channels.

---

## 8. Institutional Benefits & Capacity Building

1. **Missed-Signal Audit (M10):** The host institution receives an un-redacted, confidential quality audit identifying historical patterns of delayed diagnostic investigation, reference interval calibration, and laboratory turnaround times.
2. **Academic Publication:** Clinical and pathology staff from the host institution will receive full co-authorship on all scientific manuscripts arising from the study.
3. **Zero Cost Burden:** All research data abstraction stipends and data infrastructure are covered by the Vigil research initiative.

---

## 9. Principal Investigator Declaration

I hereby certify that the information provided in this application is complete, truthful, and accurate. I undertake to conduct the research in strict compliance with the approved protocol, the National Code for Health Research Ethics (NHREC), the Nigeria Data Protection Act 2023, and institutional guidelines.

**Principal Investigator:** Gideon Sanni  
**Date:** October 2026  
**Signature:** __________________________________
