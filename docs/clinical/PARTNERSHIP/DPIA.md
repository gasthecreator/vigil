# Data Protection Impact Assessment (DPIA) (docs/clinical/PARTNERSHIP/DPIA.md)

**Regulatory Framework:** Nigeria Data Protection Act 2023 (NDPA 2023), Sections 28, 34, 35 [E14]  
**Target Project:** Vigil Precision Oncology Platform — Retrospective Nigerian Clinical Calibration Study  
**Document Status:** Final Operational Assessment (Phase 1)  
**Data Protection Officer (DPO) / Compliance Reviewer:** Legal & Regulatory Scaffolding, Vigil Initiative  
**Date:** October 2026

---

## 1. System & Processing Overview

### 1.1 Project Description
The Vigil project evaluates an intelligent decision-support algorithm designed to detect metastatic breast cancer recurrence from longitudinal blood tests (e.g., transaminases, CA 15-3, creatinine, CEA). To ensure algorithmic safety and clinical validity in Nigerian populations, the project requires retrospective secondary analysis of historical patient records (2014–2024) from partner tertiary hospital centers.

### 1.2 Nature and Scope of Data Processing
* **Data Category:** Special Category / Sensitive Personal Data (Health and Medical Records under Section 34 of NDPA 2023).
* **Population:** Adult breast cancer patients ($N \approx 300\text{--}500$) who underwent curative-intent surgery and outpatient follow-up.
* **Volume:** Low-to-moderate volume (structured tabular records; approximately 3,000–8,000 discrete laboratory observations).
* **Geographical Scope:** Healthcare institutions within the Federal Republic of Nigeria. Processing occurs on dedicated encrypted local hardware.

---

## 2. Assessment of Necessity, Proportionality, and Lawful Basis

### 2.1 Lawful Basis for Processing Sensitive Health Data
Under Section 25 and Section 35(1) of the Nigeria Data Protection Act 2023, processing of sensitive health data without individual consent is lawful under the following statutory exceptions:
1. **Section 35(1)(d) - Public Health and Scientific Research:** The processing is necessary for reasons of public interest in the area of public health, scientific research, and health system quality improvement.
2. **Section 35(1)(e) - Archival and Statistical Purposes:** The processing is strictly proportionate to the research aim, respects the essence of the right to data protection, and provides suitable and specific technical safeguards for the fundamental rights of the data subject.

### 2.2 Proportionality & Data Minimization
* **Minimal Dataset Enforced:** As documented in `DATA-DICTIONARY.md`, only clinical variables strictly necessary for mathematical modeling (tumor stage, receptor status, quantitative analyte values, visit day offsets, and recurrence dates) are extracted.
* **Prohibited Data Elements:** Names, residential addresses, hospital medical record numbers, national identification numbers (NIN), phone numbers, email addresses, biometric data, employer information, and billing/financial records are strictly excluded from extraction.

---

## 3. Risk Identification and Threat Assessment

| Threat / Risk Vector | Likelihood | Impact | Overall Inherent Risk |
|---|---|---|---|
| **R-1: Direct Re-Identification** (Matching patient records using unique names or identifiers) | High (if unmitigated) | Severe | **HIGH** |
| **R-2: Quasi-Identifier Linkage Attack** (Inferring identity by cross-referencing age, exact visit dates, and rare clinical diagnosis) | Medium | Moderate | **MEDIUM** |
| **R-3: Data Breach in Transit or at Rest** (Interception of unencrypted CSV/Excel files) | Medium | Severe | **HIGH** |
| **R-4: Re-identification Key Compromise** (Unauthorized access to the master linkage file linking UUIDs to hospital MRNs) | Low | Severe | **MEDIUM** |
| **R-5: Unintended Secondary Commercial Exploitation** | Low | High | **MEDIUM** |

---

## 4. Technical Safeguards & Risk Mitigation Controls

```
[Hospital EMR / Physical Charts]
             │
             ▼
[On-Site Extraction & De-Identification]
   ├── Strip all 18 direct identifiers
   ├── Assign cryptographically random UUID
   ├── Apply constant stochastic Date-Shift ([-365, +365] days)
   └── Store Linkage Key on offline hospital computer (Sole access: Host PI)
             │
             ▼
[Encrypted De-Identified Data Package]
   ├── AES-256 encryption at rest
   ├── SHA-256 checksum manifest
   └── Secure TLS 1.3 transfer to research workspace
             │
             ▼
[Vigil Algorithmic Calibration & Leakage Suite]
   ├── Zero re-identification queries
   ├── Shuffled-label canary verification
   └── No cloud upload of raw medical records
```

### 4.1 De-Identification & Date-Shifting Safeguards
1. **On-Site Stripping:** No personal names or hospital registration numbers leave the premises of the partner healthcare facility.
2. **Date-Shifting Algorithm:** Every patient record receives an individual random integer offset ($k_i \in [-365, +365]$). All clinical milestones and laboratory draw dates are shifted by exactly $k_i$ days. This mathematically destroys calendar date linkage attacks while perfectly preserving longitudinal rates of change ($d(\text{analyte})/dt$) and clinical lead time.
3. **Segregation of Key Custody:** The pseudonymization linkage table is retained exclusively on an offline, password-protected computer in the hospital's Medical Records Department under the personal custody of the local Co-PI.

### 4.2 Technical and Cryptographic Controls
1. **Encryption Standards:** De-identified datasets are encrypted at rest using AES-256-GCM.
2. **Access Control:** Role-Based Access Control (RBAC) restricts dataset access strictly to named researchers who have signed non-disclosure agreements.
3. **Integrity Verification:** Datasets are tracked via SHA-256 manifests (`packages/contracts`); any file tampering or schema alteration causes immediate ingestion failure.
4. **Air-Gapped Local Execution:** In compliance with NDPA cross-border transfer requirements (Section 41–43), all clinical calibration scripts run locally on authenticated endpoints with zero transmission of patient records to third-party cloud AI vendors.

---

## 5. Residual Risk Evaluation Post-Mitigation

| Risk ID | Mitigation Measures Implemented | Residual Likelihood | Residual Impact | Residual Risk |
|---|---|---|---|---|
| **R-1** | Full on-site de-identification | Negligible | Low | **LOW** |
| **R-2** | Stochastic date-shifting, age binning, cell suppression | Low | Low | **LOW** |
| **R-3** | AES-256 encryption, TLS 1.3, strict RBAC | Very Low | Low | **LOW** |
| **R-4** | Offline key custody by hospital Co-PI | Very Low | Moderate | **LOW** |
| **R-5** | DUA binding terms; open non-commercial code | Negligible | Low | **LOW** |

---

## 6. Stakeholder Consultation and Regulatory Sign-Off

* **Clinical Oncology Lead:** Confirmed that data minimization retains necessary diagnostic markers without compromising clinical validity.
* **Hospital Medical Records Department:** Reviewed and approved on-site extraction and pseudonymization workflows.
* **Institutional Health Research Ethics Committee (HREC):** Protocol and DPIA submitted as integral part of ethical clearance.

### 6.1 Compliance Declaration
The Vigil Oncology Research Initiative certifies that this Data Protection Impact Assessment satisfies all statutory requirements of the **Nigeria Data Protection Act 2023**. The technical safeguards implemented reduce privacy and confidentiality risks to the lowest reasonable level.

**Compliance Officer / Principal Investigator:** Gideon Sanni  
**Date:** October 2026
