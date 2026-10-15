# Clinical Data Dictionary & Extraction Specification (docs/clinical/PARTNERSHIP/DATA-DICTIONARY.md)

**Platform:** Vigil Precision Oncology Platform  
**Target Setting:** Nigerian Hospital Retrospective Chart Review & EMR Extraction  
**Standard Compliance:** HL7 FHIR R4, LOINC (Logical Observation Identifiers Names and Codes), UCUM (Unified Code for Units of Measure), CDISC SDTM v1.4  
**Version:** 1.0.0

---

## 1. Overview & Data Schema Structure

The Vigil data extraction protocol requires four linked relational tables. All calendar dates must be expressed as **relative integer days** from the patient's primary surgical resection or histological biopsy date (`day = 0`) to preserve privacy and enable temporal modeling without date leakage:

```
+------------------+         +-----------------------+
|     PATIENT      | 1 --- 1 |   BASELINE_PROFILE    |
+------------------+         +-----------------------+
         | 1                            | 1
         |                              |
         | *                            | 1
+------------------+         +-----------------------+
|  LAB_OBSERVATION |         |   CLINICAL_OUTCOME    |
+------------------+         +-----------------------+
```

---

## 2. Table 1: `PATIENTS` (Demographics & Follow-up)

| Column Name | Type | Allowed Values / Format | Description | Required |
|---|---|---|---|---|
| `patient_id` | UUID / String | Unique alphanumeric pseudonym (e.g., `VIGIL-LUTH-001`) | Pseudonymized patient identifier. Re-identification key kept at hospital. | **Yes** |
| `age_at_diagnosis` | Integer | $18 \le \text{age} \le 105$ | Patient age in years at date of confirmed histological diagnosis. | **Yes** |
| `menopausal_status` | String | `PRE`, `PERI`, `POST`, `UNKNOWN` | Menopausal status at primary presentation. | **Yes** |
| `vital_status` | String | `ALIVE`, `DEAD_DISEASE`, `DEAD_OTHER`, `LOST_TO_FOLLOWUP` | Vital status at close of study chart review. | **Yes** |
| `days_to_last_followup`| Integer | $\ge 0$ | Total documented duration of follow-up from primary diagnosis in days. | **Yes** |

---

## 3. Table 2: `BASELINE_PROFILE` (Primary Tumor Pathology & Treatment)

| Column Name | Type | Allowed Values / Codes | Clinical Specification & Standard | Required |
|---|---|---|---|---|
| `patient_id` | String | Matching `PATIENTS.patient_id` | Foreign key link to patient demographic record. | **Yes** |
| `histological_type` | String | `IDC`, `ILC`, `MUCINOUS`, `METAPLASTIC`, `OTHER` | Invasive Ductal Carcinoma (IDC), Invasive Lobular (ILC), etc. | **Yes** |
| `tumor_grade` | Integer | `1`, `2`, `3` | Nottingham Histologic Grade (Elston-Ellis modification). | **Yes** |
| `stage_ajcc` | String | `I`, `IIA`, `IIB`, `IIIA`, `IIIB`, `IIIC` | AJCC Pathologic Stage Group (7th or 8th edition). Excludes de novo IV. | **Yes** |
| `er_status` | String | `POSITIVE`, `NEGATIVE`, `EQUIVOCAL`, `UNKNOWN` | Estrogen Receptor status by immunohistochemistry ($\ge 1\%$ staining). | **Yes** |
| `pr_status` | String | `POSITIVE`, `NEGATIVE`, `EQUIVOCAL`, `UNKNOWN` | Progesterone Receptor status by immunohistochemistry. | **Yes** |
| `her2_status` | String | `POSITIVE`, `NEGATIVE`, `EQUIVOCAL`, `UNKNOWN` | HER2 status by IHC (3+ positive, 0/1+ negative) or FISH amplification. | **Yes** |
| `has_hypertension` | Boolean | `true`, `false` | Documented chronic systemic hypertension requiring medication. | **Yes** |
| `renal_history` | Boolean | `true`, `false` | History of renal impairment, glomerulonephritis, or baseline eGFR < 60. | **Yes** |
| `surgery_type` | String | `MRM`, `BCS`, `TOTAL_MASTECTOMY`, `NONE` | Modified Radical Mastectomy (MRM) vs Breast Conserving Surgery (BCS). | **Yes** |
| `chemotherapy_given`| Boolean | `true`, `false` | Received neoadjuvant or adjuvant systemic cytotoxic chemotherapy. | **Yes** |
| `endocrine_therapy` | Boolean | `true`, `false` | Received adjuvant Tamoxifen or Aromatase Inhibitors (Letrozole, etc.). | **Yes** |
| `radiotherapy_given`| Boolean | `true`, `false` | Received post-mastectomy or breast chest-wall radiation therapy. | **Yes** |

---

## 4. Table 3: `LAB_OBSERVATIONS` (Serial Longitudinal Laboratory Draws)

| Column Name | Type | Allowed Values / Codes | Clinical Specification & Standard | Required |
|---|---|---|---|---|
| `patient_id` | String | Matching `PATIENTS.patient_id` | Foreign key linking lab draw to patient. | **Yes** |
| `observation_day` | Integer | Relative days from diagnosis ($0 \le \text{day} \le 3650$) | Date of venous phlebotomy blood draw. | **Yes** |
| `analyte_code` | String | Canonical LOINC code (see Section 6) | Logical Observation Identifiers Names and Codes identifier. | **Yes** |
| `analyte_name` | String | Standard text (e.g., `ca_15_3`, `alt`, `ast`) | Standardized lowercase string identifier. | **Yes** |
| `value_numeric` | Float | Non-negative numeric value | Quantitative concentration / enzyme activity. | **Yes** |
| `unit_ucum` | String | Standard UCUM string (e.g., `[iU]/mL`, `U/L`) | Unified Code for Units of Measure canonical symbol. | **Yes** |
| `ref_low` | Float | Optional numeric float | Institutional laboratory lower reference limit. | No |
| `ref_high` | Float | Optional numeric float | Institutional laboratory upper reference limit. | No |

---

## 5. Table 4: `CLINICAL_OUTCOMES` (Recurrence Milestones & Event Ground Truth)

| Column Name | Type | Allowed Values / Codes | Clinical Specification & Standard | Required |
|---|---|---|---|---|
| `patient_id` | String | Matching `PATIENTS.patient_id` | Foreign key linking outcome to patient. | **Yes** |
| `recurrence_confirmed` | Boolean | `true`, `false` | Objective clinical, radiological, or histological recurrence confirmation. | **Yes** |
| `recurrence_day` | Integer | Relative days from diagnosis (or null if false) | Date of definitive diagnostic confirmation (imaging or biopsy date). | Conditional |
| `site_bone` | Boolean | `true`, `false` | Confirmed skeletal/bone metastasis (X-ray, Bone scan, MRI, CT). | Conditional |
| `site_liver` | Boolean | `true`, `false` | Confirmed hepatic metastasis (Ultrasound, CT, MRI, biopsy). | Conditional |
| `site_lung` | Boolean | `true`, `false` | Confirmed pulmonary or pleural metastasis (CXR, CT chest). | Conditional |
| `site_brain` | Boolean | `true`, `false` | Confirmed central nervous system / intracranial metastasis (CT, MRI). | Conditional |
| `site_locoregional` | Boolean | `true`, `false` | Isolated chest wall, surgical scar, or ipsilateral regional axillary relapse. | Conditional |
| `confirmatory_modality`| String | `ULTRASOUND`, `CT_SCAN`, `MRI`, `XRAY`, `BONE_SCAN`, `BIOPSY`, `CLINICAL` | Primary imaging or diagnostic modality establishing recurrence. | Conditional |
| `dismissed_prior_signal`| Boolean | `true`, `false` | Documented lab elevation prior to diagnosis with no restaging ordered. | No |

---

## 6. Standard Analyte Vocabulary & Reference Specifications

The minimal extraction dataset maps directly to the `vigil-core` registry (`packages/vigil-core/vigil_core/analytes.py`):

| Analyte Symbol | Analyte Name | LOINC Code | Canonical UCUM Unit | Standard Ref Range | Plausibility Range | EFLM Biological Variation ($CV_i$) |
|---|---|---|---|---|---|---|
| `ca_15_3` | Cancer Antigen 15-3 | `83082-8` | `[iU]/mL` | 0.0 – 30.0 | 0.0 – 2,500.0 | 6.1% |
| `cea` | Carcinoembryonic Antigen | `83085-1` | `ug/L` | 0.0 – 5.0 | 0.0 – 5,000.0 | 12.7% |
| `alt` | Alanine Aminotransferase | `1742-6` | `U/L` | 7.0 – 56.0 | 0.0 – 2,500.0 | 19.4% |
| `ast` | Aspartate Aminotransferase | `1920-8` | `U/L` | 10.0 – 40.0 | 0.0 – 3,000.0 | 12.3% |
| `alp` | Alkaline Phosphatase | `6768-6` | `U/L` | 44.0 – 147.0 | 0.0 – 3,500.0 | 6.5% |
| `creatinine` | Serum Creatinine | `2160-0` | `mg/dL` | 0.5 – 1.2 | 0.1 – 25.0 | 4.3% |
| `wbc` | Leukocytes (Total WBC) | `6690-2` | `10*3/uL` | 4.0 – 11.0 | 0.1 – 150.0 | 10.9% |
| `hemoglobin` | Hemoglobin | `718-7` | `g/dL` | 12.0 – 16.0 | 2.0 – 26.0 | 2.8% |
| `platelets` | Platelet Count | `777-3` | `10*3/uL` | 150.0 – 450.0 | 5.0 – 2,000.0 | 9.1% |
| `albumin` | Serum Albumin | `1751-7` | `g/dL` | 3.5 – 5.5 | 0.5 – 8.0 | 3.2% |
| `total_bilirubin`| Total Bilirubin | `1975-2` | `mg/dL` | 0.1 – 1.2 | 0.0 – 50.0 | 22.0% |
| `ggt` | Gamma Glutamyl Transferase | `2324-2` | `U/L` | 9.0 – 48.0 | 0.0 – 2,000.0 | 13.8% |

---

## 7. Data Quality & Cleaning Validation Rules

Before ingestion into Vigil (`packages/contracts`), the dataset must satisfy these automated checks:
1. **Uniqueness:** `patient_id` must be unique in `PATIENTS` and `BASELINE_PROFILE`.
2. **Referential Integrity:** Every row in `LAB_OBSERVATIONS` and `CLINICAL_OUTCOMES` must have a corresponding `patient_id` in `PATIENTS`.
3. **Temporal Ordering:** `observation_day` and `recurrence_day` must be integers $\ge 0$.
4. **Physiological Boundaries:** Any `value_numeric` outside the Plausibility Range will be flagged for secondary chart audit (possible transcription error).
5. **No Direct Identifiers:** The ingestion script will immediately abort if any column contains patient names, phone numbers, or dates formatted as `YYYY-MM-DD`.
