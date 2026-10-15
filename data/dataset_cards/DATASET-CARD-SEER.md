# Dataset Card: SEER Breast Cancer Distant Metastasis Cohort

## 1. Dataset Summary
- **Source:** Surveillance, Epidemiology, and End Results (SEER) Program, National Cancer Institute (NCI).
- **Tier:** `T-P (Public Registries / External Retrospective)`
- **Scope:** Female invasive breast cancer cases with documented distant metastatic sites (bone, liver, lung, brain), molecular subtypes, and survival time.
- **Intended Use:** Informing baseline site propensity distributions (M1 / Task T1) and subtype-stratified recurrence hazards.
- **Out-of-Scope Use:** Cannot support longitudinal marker trajectory modeling as SEER does not record serial laboratory values or pre-clinical recurrence dates.

## 2. Data Dictionary & Field Specifications
- `SEER_ID`: De-identified unique patient identifier.
- `AGE_DX`: Age at initial breast cancer diagnosis.
- `YEAR_DX`: Year of diagnosis.
- `HISTOLOGY`: ICD-O-3 histology code.
- `STAGE_GROUP`: AJCC stage at diagnosis (Stage I–IV).
- `SUBTYPE`: Breast subtype derived from ER, PR, and HER2 IHC/FISH status (HR+/HER2-, HER2-enriched, TNBC).
- `MET_BONE`: Distant bone metastasis at initial diagnosis (Yes/No/Unknown).
- `MET_LIVER`: Distant liver metastasis at initial diagnosis (Yes/No/Unknown).
- `MET_LUNG`: Distant lung metastasis at initial diagnosis (Yes/No/Unknown).
- `MET_BRAIN`: Distant brain metastasis at initial diagnosis (Yes/No/Unknown).
- `SURVIVAL_MONTHS`: Duration from diagnosis to death or last follow-up.
- `VITAL_STATUS`: Alive or deceased.

## 3. Provenance & Access Protocol
- **Access Authority:** National Cancer Institute SEER Research Data Agreement.
- **Application Process:** Signed institutional SEER*Stat Research Data Agreement; human action required (H-002).
- **Validation Fixture:** Schema-compliant synthetic fixture verified against official SEER 17/22 registry data dictionary.
