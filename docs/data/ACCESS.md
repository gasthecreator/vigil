# Data Access Dossier (docs/data/ACCESS.md)

**Platform:** Vigil Precision Oncology Platform  
**Document Classification:** Data Governance & Regulatory Dossier  
**Governance Standard:** Master Plan §7.1, §7.2, §14 (WP1.3, WP1.5), Evidence [E13]  
**Version:** 1.0.0 (Phase 1)

---

## 1. Executive Summary & Honest Data Landscape

Real longitudinal oncology laboratory records linked to confirmed metastatic recurrence dates are scarce, highly restricted, and virtually non-existent in public sub-Saharan African cohorts [E13]. In accordance with Vigil Master Plan §7.1, our data architecture enforces a strict **5-tier data hierarchy**:

| Tier | Designation | Primary Purpose | Permitted Claim |
|---|---|---|---|
| **T-S** | Mechanistic Synthetic (`vigil-sim`) | Algorithm plumbing, mathematical stress testing, leakage verification | *"Method recovers known biological kinetics under explicit model assumptions."* **NEVER clinical validity.** |
| **T-P** | Public Registries & Trial Archives (SEER, METABRIC, TCGA, PDS, MIMIC-IV) | Demographic priors, baseline organ susceptibility (M1), generic time-series pretraining | *"Calibrated site priors and baseline survival distributions on reference populations."* |
| **T-R** | Retrospective Partner Hospital Chart Review (Nigerian Teaching Hospital) | Retrospective clinical validation of surveillance models (M2, M3, M6, M10) | *"Retrospective discrimination, calibration, and lead-time in the target deployment setting."* |
| **T-Q** | Prospective Silent-Mode Clinical Stream | Real-time false-alarm audit without clinician-facing intervention | *"Prospective alert burden, loop-closure frequency, and real-world noise resilience."* |
| **T-L** | Prospective Clinical Decision-Support Pilot | DECIDE-AI stage clinical utility evaluation | *"Decision-impact, workflow integration, and patient outcomes under informed consent."* |

This dossier details the formal application procedures, licensing agreements, data schemas, and pre-drafted submission forms for all Tier **T-P** public resources.

---

## 2. SEER Research Data (NCI Surveillance, Epidemiology, and End Results)

### 2.1 Overview & Role in Vigil
* **Provider:** National Cancer Institute (NCI), USA.
* **Role in Vigil:** Calibration of baseline demographic distributions and metastatic organ propensity priors (Model M1). Provides large-scale population estimates of de novo metastatic organ distributions (bone, liver, lung, brain) stratified by age, tumor stage, grade, and ER/PR/HER2 subtype.
* **Critical Limitation:** SEER does **not** collect serial laboratory test results, outpatient surveillance visits, or post-surgical recurrence dates [E13]. It captures stage at initial diagnosis and survival duration.

### 2.2 Access Procedure & Licensing
1. **Account Registration:** Register for an NCI SEER account via [seer.cancer.gov/data/access.html](https://seer.cancer.gov/data/access.html).
2. **Data-Use Agreement (DUA):** Agree to the electronic Research Data Agreement:
   - Prohibition against individual re-identification or linkage to other identifiable databases.
   - Commitment to institutional data security and encrypted storage.
   - Agreement to acknowledge NCI SEER in all technical reports and publications.
3. **Software Tooling:** Submit application requesting SEER*Stat software access or direct binary ASCII data matrix downloads.
4. **Turnaround Time:** Typically automated or 1–3 business days.

### 2.3 Verified Schema & Ingestion Contract
* **Documentation Verified:** *SEER Research Data Record Description (1975–2020)*.
* **Target Fields:**
  - `Patient ID` (masked identifier)
  - `Age at diagnosis`
  - `Year of diagnosis`
  - `Derived AJCC Stage Group` (7th/8th edition)
  - `Breast Subtype (2010+)` (HR+/HER2-, HR+/HER2+, HR-/HER2+, Triple Negative)
  - `SEER Combined Mets at DX-bone` (Yes / No / Unknown)
  - `SEER Combined Mets at DX-liver` (Yes / No / Unknown)
  - `SEER Combined Mets at DX-lung` (Yes / No / Unknown)
  - `SEER Combined Mets at DX-brain` (Yes / No / Unknown)
  - `Survival months` and `Vital status recode`
* **Software Loader:** Verified by Pydantic v2 schema in `packages/contracts/contracts/loaders/seer_loader.py` with test fixture in `data/fixtures/seer_sample.csv`.
* **Action Status:** Pre-drafted. Pending human account confirmation (`H-002`).

---

## 3. METABRIC (Molecular Taxonomy of Breast Cancer International Consortium)

### 3.1 Overview & Role in Vigil
* **Provider:** Cancer Research UK / BC Cancer Agency via cBioPortal / Synapse (`syn1688369`).
* **Role in Vigil:** Genomic and clinical validation of subtype-stratified disease-free survival (DFS) and overall survival (OS). Supports training of baseline organ susceptibility models.
* **Critical Limitation:** Captures primary tumor genomics (microarray/copy number) and clinical relapse events, but **no** serial routine blood draws or biochemical trajectories.

### 3.2 Access Procedure & Licensing
1. **Access Level:** Open-access clinical tables via cBioPortal (`brca_metabric`) and Synapse.
2. **Terms of Use:** Academic non-commercial research use under the METABRIC publication policy.
3. **Turnaround Time:** Immediate (direct HTTPS API / download).

### 3.3 Verified Schema & Ingestion Contract
* **Documentation Verified:** Curtis et al., *Nature* 2012 / Pereira et al., *Nature Communications* 2016 clinical supplements.
* **Target Fields:**
  - `PATIENT_ID`
  - `AGE_AT_DIAGNOSIS`
  - `CLAUDIN_SUBTYPE` / `PAM50_SUBTYPE`
  - `ER_STATUS` / `PR_STATUS` / `HER2_STATUS`
  - `TUMOR_STAGE`
  - `VITAL_STATUS`
  - `OS_MONTHS` / `OS_STATUS`
  - `RFS_MONTHS` / `RFS_STATUS` (Relapse-Free Survival)
* **Software Loader:** Pydantic v2 ingestion contract implemented in `packages/contracts/contracts/loaders/metabric_loader.py` with unit tests passing on `data/fixtures/metabric_sample.csv`.

---

## 4. TCGA-BRCA (The Cancer Genome Atlas - Breast Invasive Carcinoma)

### 4.1 Overview & Role in Vigil
* **Provider:** National Cancer Institute (NCI) Genomic Data Commons (GDC) / PanCancer Atlas.
* **Role in Vigil:** Multi-omic clinical reference for recurrence-free intervals, clinical staging, and molecular subtyping.
* **Critical Limitation:** Recurrence event timestamps are recorded as relative days from primary surgical resection; zero outpatient serial surveillance blood labs.

### 4.2 Access Procedure & Licensing
1. **Access Level:** Open Access for de-identified clinical phenotypes, staging, and survival tables. Controlled Access (dbGaP) only required for raw BAM sequence reads.
2. **Licensing:** Creative Commons Zero (CC0) / Open Access public domain.
3. **Turnaround Time:** Immediate download via GDC API or cBioPortal.

### 4.3 Verified Schema & Ingestion Contract
* **Documentation Verified:** GDC Data Dictionary: `Case`, `Diagnosis`, `Demographic`, and `Follow-up` entities.
* **Target Fields:**
  - `bcr_patient_barcode`
  - `age_at_initial_pathologic_diagnosis`
  - `ajcc_pathologic_stage`
  - `er_status_by_ihc`, `pr_status_by_ihc`, `her2_status_by_ihc`
  - `days_to_last_followup`, `days_to_death`, `vital_status`
  - `days_to_new_tumor_event_after_initial_treatment`
  - `new_neoplasm_event_type` (Distant Metastasis / Locoregional)
  - `new_tumor_event_additional_surgery_metastasis_site`
* **Software Loader:** Ingestion contract in `packages/contracts/contracts/loaders/tcga_loader.py` with test fixture `data/fixtures/tcga_sample.csv`.

---

## 5. Project Data Sphere (PDS)

### 5.1 Overview & Role in Vigil
* **Provider:** Project Data Sphere, LLC (CEO Roundtable on Cancer).
* **Role in Vigil:** Provides historical control arms from prospective phase III oncology clinical trials. Essential for evaluating real-world longitudinal biomarker trends in trial-grade monitored populations.
* **Critical Limitation:** Analyte availability is protocol-specific. Some trials capture CEA/CA 15-3 while others only record standard safety chemistry (ALT, AST, Creatinine).

### 5.2 Access Procedure & Licensing
1. **Registration:** Submit research application at [projectdatasphere.org](https://www.projectdatasphere.org).
2. **Research Plan:** Detail the non-commercial validation of surveillance algorithms and automated quality checks.
3. **DUA Requirements:** Execution of PDS Data Use Agreement prohibiting re-identification and third-party redistribution.
4. **Turnaround Time:** 2–4 weeks institutional review.
5. **Action Status:** Pre-drafted application dossier ready for human sign-off (`H-003`).

### 5.3 Verified Schema & Ingestion Contract
* **Documentation Verified:** CDISC SDTM (Study Data Tabulation Model) v1.4 Standards:
  - `DM` (Demographics): `USUBJID`, `AGE`, `SEX`, `ARM`
  - `LB` (Laboratory Test Results): `USUBJID`, `LBTESTCD`, `LBORRES`, `LBORRESU`, `LBDY` (study day)
  - `RS` (Response / Disease Status): `USUBJID`, `RSTESTCD`, `RSORRES`, `RSDY`
* **Software Loader:** Implemented in `packages/contracts/contracts/loaders/pds_loader.py` with fixture `data/fixtures/pds_sample.csv`.

---

## 6. MIMIC-IV v2.2 (PhysioNet)

### 6.1 Overview & Role in Vigil
* **Provider:** MIT Laboratory for Computational Physiology via PhysioNet.
* **Role in Vigil:** Dense, high-frequency irregular time-series of blood analytes (transaminases, creatinine, blood counts) to pretrain neural sequence architectures (GRU-D / state-space models) and validate biological variation filters.
* **Critical Limitation:** ICU and acute inpatient population. Severe selection bias toward critically ill patients; not an outpatient breast cancer surveillance cohort. Must be explicitly documented in all model cards.

### 6.2 Access Procedure & Credentialing
1. **Human Subjects Training:** Complete CITI Program course *"Data or Specimens Only Research"* (Record ID required).
2. **Credentialed PhysioNet Account:** Submit proof of institutional affiliation and CITI certification.
3. **DUA Execution:** Sign PhysioNet Credentialed Health Data Use Agreement:
   - Strict ban on re-identification and sharing login credentials.
   - Must report all publications using the PhysioNet citation standard.
4. **Turnaround Time:** 1–2 weeks following CITI completion.
5. **Action Status:** Pending human training and credential submission (`H-004`).

### 6.3 Verified Schema & Ingestion Contract
* **Documentation Verified:** MIMIC-IV Clinical Database v2.2 Schema (`hosp` and `icu` modules).
* **Target Tables:**
  - `patients`: `subject_id`, `gender`, `anchor_age`, `anchor_year`
  - `admissions`: `subject_id`, `hadm_id`, `admittime`, `dischtime`, `hospital_expire_flag`
  - `diagnoses_icd`: ICD-9 (174.x) and ICD-10 (C50.x) codes for malignant breast neoplasm cohort filtering
  - `labevents`: `subject_id`, `hadm_id`, `itemid`, `charttime`, `valuenum`, `valueuom`
* **Software Loader:** Implemented in `packages/contracts/contracts/loaders/mimic_loader.py` with test fixture `data/fixtures/mimic_sample.csv`.

---

## 7. Action Matrix & Human Responsibility Ledger

| Resource | Status | Technical Artifact | Human Next Step |
|---|---|---|---|
| **SEER** | Blocked on Human Account | `contracts/loaders/seer_loader.py` | Submit DUA at seer.cancer.gov (`H-002`) |
| **METABRIC** | Ready / Open Access | `contracts/loaders/metabric_loader.py` | Ingest via cBioPortal API during Phase 2 |
| **TCGA-BRCA** | Ready / Open Access | `contracts/loaders/tcga_loader.py` | Ingest GDC open tables during Phase 2 |
| **Project Data Sphere** | Blocked on DUA Application | `contracts/loaders/pds_loader.py` | Sign and submit PDS application (`H-003`) |
| **MIMIC-IV** | Blocked on CITI Training | `contracts/loaders/mimic_loader.py` | Complete CITI course & request PhysioNet access (`H-004`) |

*All software loaders in `packages/contracts` are fully implemented, strictly typed with Pydantic v2, and covered by automated test suites.*
