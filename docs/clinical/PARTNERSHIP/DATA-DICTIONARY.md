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
| `days_to_death` | Integer | `index_day` $\le$ day $\le$ `days_to_last_followup` | Explicit relative day of death from diagnosis. Required when `vital_status` is `DEAD_DISEASE` or `DEAD_OTHER`; must be blank otherwise. `days_to_last_followup` is not treated as an inferred death date. | Conditional |
| `index_day` | Integer | $0 \le \text{index\_day} \le$ `days_to_last_followup` | Relative day of completion of primary treatment (surgery, or last chemotherapy or radiotherapy session, whichever is later). This is the index date of `docs/clinical/PREREGISTRATION.md` section 2; surveillance features and landmarks start here. | **Yes** |

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
| `restaging_imaging_done` | Boolean | `true`, `false` | Whether any restaging imaging (US, CT, MRI, X-ray or bone scan) was performed during follow-up, whether or not it found recurrence. Needed for the mandatory verification-bias analysis (PREREGISTRATION section 5.1); when absent that analysis is reported as not run. | No |

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

These rules are what `packages/contracts/contracts/partner/ingest.py` enforces (`scripts/run_partner_ingest.py` runs it). A rule that is not in this list is not enforced, and a rule in this list that the code does not enforce is a defect. `packages/contracts/tests/test_partner_ingest.py` checks the code against an injected-fault manifest and checks that every code below is documented.

### 7.1 Whole-file refusal (nothing is parsed; the report names columns and row numbers only)
| Code | Meaning |
|---|---|
| `MISSING_TABLE` | One of the four tables is absent. |
| `MISSING_COLUMN` | A required column of this dictionary is absent. |
| `IDENTIFIER_COLUMN` | A column outside this dictionary whose name looks like a direct identifier (name, phone, e-mail, address, date of birth, hospital number, national ID, next of kin, and similar). |
| `UNKNOWN_COLUMN` | Any other column outside this dictionary (free text is where names hide, so unknown columns are refused, not ignored). |
| `IDENTIFIER_VALUE` | Any cell, in any column, that contains an absolute date (`YYYY-MM-DD`, `DD/MM/YYYY`, an Excel date cell), an e-mail address or a phone number. |

### 7.2 Per-row rejection (the row is rejected, never repaired)
| Code | Meaning |
|---|---|
| `MISSING_REQUIRED` | A required (or conditionally required) value is empty. |
| `BAD_TYPE` | Not an integer, number, boolean or valid pseudonymous id (`[A-Za-z0-9_-]`, at most 64 characters). A decimal comma is not accepted. |
| `BAD_ENUM` | Not one of the allowed values after case and whitespace normalisation (for example `stage_ajcc = IV` is refused: de novo stage IV is out of scope). |
| `OUT_OF_RANGE` | Outside the range of Section 2-5 (age 18-105, grade 1-3, day 0-3650, value at least 0). |
| `CONFLICTING_DUPLICATE` | The same key appears more than once with different content. **All** copies are rejected; the tool does not pick a winner. |
| `ORPHAN_FK` | `patient_id` is not in `patients`. |
| `PARENT_REJECTED` | `patient_id` is in `patients` but that row was rejected. |
| `INCONSISTENT` | `index_day` after `days_to_last_followup`; `days_to_death` outside `[index_day, days_to_last_followup]` or supplied for a non-deceased patient; `recurrence_day` after `days_to_last_followup`; `recurrence_confirmed = false` with a `recurrence_day` or a metastasis site. |
| `UNKNOWN_ANALYTE` | `analyte_code` is not a LOINC code of the Vigil analyte registry. |
| `NAME_CODE_MISMATCH` | `analyte_name` does not belong to the LOINC code. |
| `UNKNOWN_UNIT` | Unit string not recognised. |
| `INCOMPATIBLE_UNIT` | Unit of a different physical dimension from the analyte (for example ALT in mg/dL). |

### 7.3 Counted, not rejected
- **Exact duplicate rows** are dropped once and counted.
- **Normalised cells** (case, surrounding whitespace, `Yes`/`Y`/`1` for true) are counted. Anything that is not an unambiguous spelling is rejected, not guessed.
- **Implausible laboratory values** (outside the physiological bounds of the registry after unit conversion) are *flagged and withheld* from the clean table pending chart audit; they are listed in the report and are not used by any analysis.
- Laboratory values are converted to the canonical unit of the analyte; the original value and unit are kept next to the canonical ones.

### 7.4 What the report contains and what it never contains
Counts per table and per code, the rejection rate against the stop rate (PREREGISTRATION PR-07), and one line per rejection: table, data-row number (header excluded), code, field, the pseudonymous id, and the value **only** when it is a number that passed type validation. A rejected free-text cell is reported as a code, never as text, because it might contain a name.

## 8. Formats and on-site HL7 conversion
- **CSV:** four files `patients.csv`, `baseline_profile.csv`, `lab_observations.csv`, `clinical_outcomes.csv`, UTF-8, header row, one table per file.
- **Excel:** one workbook with four sheets named like the tables (any case). A date-typed cell is refused as an absolute date.
- **HL7 v2 ORU^R01:** results carry absolute timestamps and the hospital's own patient identifier, both forbidden above. The converter `contracts.partner.hl7_onsite` is therefore run **inside the hospital** with (a) a map from the local patient identifier to the diagnosis date and (b) a secret of at least 16 bytes supplied at run time, from which the pseudonym `VIGIL-<12 hex>` is derived. Only the converted rows (pseudonym, relative day) leave the site; they then pass through the same ingestion as any other file. Each OBX is converted on its own, and a reason code is recorded for every result that is not converted (`UNKNOWN_ANALYTE`, `NON_NUMERIC_VALUE`, `MISSING_UNIT`, `MALFORMED_OBX`, `NO_INDEX_DATE`, `BEFORE_DIAGNOSIS`, ...). The date map and the secret are never committed and never sent.
- The de-identification procedure the data steward follows is `DEIDENTIFICATION-CHECKLIST.md`.
