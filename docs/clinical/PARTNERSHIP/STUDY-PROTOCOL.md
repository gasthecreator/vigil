# Clinical Study Protocol (docs/clinical/PARTNERSHIP/STUDY-PROTOCOL.md)

**Title:** Retrospective Longitudinal Biomarker Surveillance for Early Detection of Metastatic Breast Cancer Recurrence in Nigerian Tertiary Oncology Centers  
**Short Title:** The Vigil-NG Retrospective Calibration and Missed-Signal Audit Study  
**Protocol Version:** 1.0.0  
**Date:** October 2026  
**Sponsor/Platform:** Vigil Precision Oncology Platform (`gasthecreator/vigil`)  
**Target Institutional Partners:** Tertiary Teaching Hospitals in Nigeria (e.g., Lagos University Teaching Hospital [LUTH], University College Hospital [UCH] Ibadan, Ahmadu Bello University Teaching Hospital [ABUTH] Zaria)  
**Governance Standard:** Declaration of Helsinki, National Health Research Ethics Committee (NHREC) Nigeria Code, Nigeria Data Protection Act 2023 (NDPA).

---

## 1. Background and Clinical Rationale

In sub-Saharan Africa, breast cancer presents with unique epidemiologic and pathophysiologic characteristics that contrast sharply with Western cohorts [E7, E8]:
1. **Young Age at Diagnosis:** The median age of presentation is 45–48 years, approximately 10–15 years younger than in North America and Western Europe [E7].
2. **Advanced Stage at Presentation:** Between 65% and 72% of patients present with locally advanced (Stage III) or metastatic (Stage IV) disease at initial diagnosis [E7].
3. **Aggressive Biology:** A higher prevalence of hormone receptor-negative and Triple-Negative Breast Cancer (TNBC) (25–35%), characterized by early visceral metastasis (liver, lung, brain) rather than indolent bone recurrence [E8].
4. **Out-of-Pocket Financing & Irregular Monitoring:** Because diagnostic tests are financed directly out-of-pocket by patients, surveillance blood draws occur at irregular intervals (60 to 180+ days), with frequent treatment interruptions and missed follow-up appointments.

International surveillance guidelines (ASCO, ESMO) currently do not recommend routine serial blood tumor markers (CA 15-3, CEA) in asymptomatic patients, citing low sensitivity in indolent recurrence and high false-positive rates that trigger unneeded cross-sectional imaging [E1]. However, in resource-constrained environments where routine PET-CT or contrast CT is unavailable, cost-prohibitive, or rationed, clinicians routinely order affordable serum panels (LFTs, CA 15-3, CEA) as a pragmatic surrogate.

Tragically, subtle biomarker trajectories indicating early hepatic or bone metastasis are frequently overlooked or dismissed as analytical noise in overburdened clinics until overt symptomatic relapse occurs. 

**Vigil** is designed to provide automated, longitudinal change detection, adjudicating biological variation ($CV_i$) and analytical imprecision ($CV_a$) against baseline tumor characteristics to alert clinicians to occult recurrence months before symptomatic crisis [E1, E2].

---

## 2. Study Objectives

### 2.1 Primary Objective
To determine the diagnostic accuracy (time-dependent ROC-AUC, sensitivity, specificity, positive predictive value, and negative predictive value) and clinical lead time of the Vigil longitudinal surveillance engine in detecting imaging-confirmed or biopsy-confirmed metastatic breast cancer recurrence in a retrospective cohort of Nigerian patients.

### 2.2 Secondary Objectives
1. **Missed-Signal Audit (M10):** Quantify the prevalence of documented, significant serial biomarker elevations that were dismissed or not investigated during routine clinic visits prior to overt metastatic diagnosis.
2. **Lead-Time Estimation:** Measure the elapsed duration (in days and months) between the first Vigil alert trigger ($p > 0.75$ / calibrated RCV threshold) and the date of definitive clinical restaging [E1].
3. **Alert Burden & False-Alarm Rate:** Evaluate the longitudinal false-positive rate under real-world out-of-pocket test intervals and determine the clinical workload burden (alerts per patient-year).
4. **Organ Propensity Prior Calibration (M1):** Calibrate the multivariable baseline metastasis model against observed Nigerian metastatic tropism (liver vs. bone vs. lung vs. brain) [E8].

---

## 3. Study Design and Setting

* **Study Design:** Multi-center retrospective longitudinal cohort study using electronic medical records (EMR) and archived physical clinical case files.
* **Study Setting:** Tertiary academic medical centers with dedicated oncology clinics, chemotherapy infusion suites, and diagnostic pathology/chemical pathology laboratories in Nigeria.
* **Study Period:** Retrospective identification of patients diagnosed and treated between January 1, 2014, and December 31, 2024, with follow-up through June 30, 2026.

---

## 4. Patient Eligibility Criteria

### 4.1 Inclusion Criteria
1. Female or male patients aged $\ge 18$ years at initial diagnosis.
2. Histologically confirmed invasive carcinoma of the breast (stages I, II, or III at initial surgical management).
3. Completed curative-intent primary treatment (surgery with or without adjuvant/neoadjuvant chemotherapy, radiotherapy, or endocrine therapy).
4. Minimum of 12 months of documented post-treatment clinical follow-up.
5. Minimum of three ($\ge 3$) documented outpatient laboratory visits with blood chemistry or tumor markers post-completion of primary therapy.

### 4.2 Exclusion Criteria
1. De novo stage IV metastatic disease at initial presentation.
2. Second primary non-breast malignancy diagnosed within 5 years prior to breast cancer diagnosis (excluding non-melanoma skin cancer or carcinoma in situ of the cervix).
3. Absence of primary histological and receptor records (ER, PR, HER2 status unknown).
4. Fewer than three post-treatment laboratory records.

---

## 5. Data Collection and Variable Extraction

Data will be abstracted from physical medical records and laboratory information systems (LIS) using a standardized electronic Case Report Form (eCRF) mapped directly to `packages/contracts/contracts/clinical.py`:

1. **Demographics & Baseline Pathology:** Age, menopausal status, histological subtype, tumor grade, pathologic TNM stage, ER status, PR status, HER2 status, primary surgery type, systemic therapy regimens.
2. **Longitudinal Laboratory Observations:** Exact blood draw dates, assay platform / lab manufacturer (where recorded), quantitative values, and canonical units for:
   - Cancer Antigen 15-3 (`ca_15_3`, U/mL)
   - Carcinoembryonic Antigen (`cea`, ng/mL)
   - Alanine Aminotransferase (`alt_level`, U/L)
   - Aspartate Aminotransferase (`ast_level`, U/L)
   - Alkaline Phosphatase (`alp_level`, U/L)
   - Serum Creatinine (`creatinine`, mg/dL or $\mu\text{mol/L}$)
   - Complete Blood Count: Total White Blood Count, Absolute Neutrophil Count, Hemoglobin, Platelets.
3. **Clinical Milestones & Outcomes:**
   - Date of suspected recurrence (symptom onset or clinical suspicion).
   - Date and modality of definitive confirmatory diagnostic imaging (abdominal ultrasound, chest CT, bone scan, MRI, biopsy).
   - Anatomical site(s) of distant recurrence: Bone, Liver, Lung, Brain, Distant Lymph Nodes, Pleura/Peritoneum.
   - Date of last known clinical contact and vital status (alive, died from breast cancer, died from non-cancer cause, lost to follow-up).

---

## 6. De-Identification, Privacy, and Data Governance

In strict compliance with the **Nigeria Data Protection Act 2023 (NDPA)** [E14] and international HIPAA Safe Harbor principles:
1. **Identifier Stripping:** All direct personal identifiers (Patient Full Name, Hospital Medical Record Number [MRN], Phone Number, Physical Address, Next-of-Kin details) are removed at the hospital site before transmission.
2. **Pseudonymization:** A cryptographically secure pseudorandom UUID (`patient_id`) is assigned to each record. The re-identification key is stored in an encrypted offline physical drive at the partner institution, accessible solely to the local Principal Investigator.
3. **Date Shifting:** All calendar dates are shifted by an individual, constant stochastic integer offset ($[-365, +365]$ days) generated per patient. Crucially, **all relative time intervals** between laboratory tests, chemotherapy cycles, and recurrence events are preserved to the exact day.
4. **Encrypted Custody:** Data extraction forms are exported as AES-256 encrypted CSV/Parquet files and transferred via secure authenticated channels.

---

## 7. Statistical Analysis and Validation Plan

1. **Survival & Anomaly Discrimination:** Evaluated using time-dependent ROC-AUC at 6, 12, and 24 months post-test landmark timepoints.
2. **Calibration:** Assessed using Hosmer-Lemeshow style decile calibration plots, Brier score, and expected calibration error (ECE).
3. **Decision Curve Analysis (DCA):** Net benefit evaluated across clinical decision thresholds ranging from 5% to 30% risk of recurrence.
4. **Lead-Time Calculation:** Difference in days between Vigil alert trigger ($p > 0.75$) and clinical diagnostic confirmation. Censored at date of last follow-up for non-recurring patients.
5. **Handling of Missing Data:** Documented explicitly per analyte. Imputation will use forward-fill with decay and indicator masks for Informative Missingness (MNAR), as specified in Master Plan §6.13.

---

## 8. Ethical Approval and Informed Consent Waiver

Because this study involves purely retrospective review of archived medical records, imposes zero physical risk to patients, extracts exclusively de-identified data, and many historical patients are deceased or untraceable, **a formal waiver of individual informed consent** is requested from the Institutional Health Research Ethics Committee (HREC) in accordance with the National Code for Health Research Ethics (NHREC).
