# Dataset Card: METABRIC (Molecular Taxonomy of Breast Cancer International Consortium)

## 1. Dataset Summary
- **Source:** cBioPortal for Cancer Genomics (Curtis et al., Nature 2012; Pereira et al., Nat Commun 2016).
- **Tier:** `T-P (Public Clinical / Genomic)`
- **Scope:** Clinical, pathological, and genomic survival data for 1,980 primary breast cancer patients with long-term follow-up (>20 years).
- **Intended Use:** Validating baseline risk profiling models (M1), subtype-specific relapse hazard shapes, and Nottingham Prognostic Index (NPI) baselines.
- **Out-of-Scope Use:** Does not contain serial longitudinal laboratory draws.

## 2. Key Clinical Variables
- `PATIENT_ID`: Unique patient accession.
- `AGE_AT_DIAGNOSIS`: Age in years.
- `ER_STATUS`: Estrogen receptor status (Positive/Negative).
- `PR_STATUS`: Progesterone receptor status.
- `HER2_STATUS`: HER2 status.
- `CLAUDIN_SUBTYPE` / `PAM50`: Intrinsic molecular subtype (LumA, LumB, Her2, Basal, Normal-like).
- `NOTTINGHAM_PROGNOSTIC_INDEX`: Histological prognostic index score.
- `TUMOUR_STAGE`: Primary tumor stage.
- `OS_MONTHS`: Overall survival duration.
- `OS_STATUS`: Overall vital status.
- `RFS_MONTHS`: Relapse-free survival duration.
- `RFS_STATUS`: Relapse event indicator.

## 3. Access Protocol
- **Repository:** cBioPortal open access / European Genome-phenome Archive (EGA).
- **Licensing:** Open academic research terms; attribution required.
