# Dataset Card: TCGA-BRCA (The Cancer Genome Atlas Breast Invasive Carcinoma)

## 1. Dataset Summary
- **Source:** NCI Genomic Data Commons (GDC) / The Cancer Genome Atlas (TCGA) Research Network.
- **Tier:** `T-P (Public Clinical / Genomic)`
- **Scope:** 1,098 female breast cancer patients with comprehensive clinical annotation, pathological staging, and follow-up event dates.
- **Intended Use:** Cross-checking recurrence event timing distributions, receptor status prognostic effects, and clinical covariate interactions.
- **Out-of-Scope Use:** Does not contain serial routine clinical chemistry or tumor marker trajectories.

## 2. Key Clinical Variables
- `bcr_patient_barcode`: Official TCGA patient identifier (e.g. `TCGA-A2-A0T0`).
- `age_at_initial_pathologic_diagnosis`: Age at diagnosis.
- `gender`: Biological sex.
- `ajcc_pathologic_tumor_stage`: AJCC pathologic stage group.
- `er_status_by_ihc`: Estrogen receptor IHC status.
- `pr_status_by_ihc`: Progesterone receptor IHC status.
- `her2_status_by_ihc`: HER2 IHC status.
- `days_to_last_followup`: Elapsed days from initial diagnosis to last clinical contact.
- `days_to_death`: Elapsed days from initial diagnosis to death (if deceased).
- `days_to_new_tumor_event_after_initial_treatment`: Elapsed days to documented recurrence / new tumor event.
- `new_neoplasm_event_type`: Site or nature of new tumor event (distant metastasis, locoregional recurrence).

## 3. Access Protocol
- **Repository:** GDC Data Portal open-access tier (clinical files require no dbGaP authorization).
