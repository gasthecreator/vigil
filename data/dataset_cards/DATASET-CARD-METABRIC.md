# Dataset Card: METABRIC (Molecular Taxonomy of Breast Cancer International Consortium)

> Facts below were read from the public cBioPortal API on 2026-10-18 (`docs/evidence/excerpts/P1_cbioportal_metabric_study.md`, audited by `scripts/audit_excerpts.py`) or are computed by `scripts/compare_marginals_public_vs_sim.py` from the downloaded tables. An earlier version of this card said "1,980 patients" and listed attribute names that do not exist in the real files; both are corrected here.

## 1. Summary
- **Source:** cBioPortal study `brca_metabric` ("Breast Cancer (METABRIC, Nature 2012 & Nat Commun 2016)"). Citations given by the study record: Pereira et al. Nat Commun 2016, Rueda et al. Nature 2019, Curtis et al. Nature 2012.
- **Tier:** `T-P` (public registry). **Size:** 2509 patients and samples; 1980 samples have mRNA microarray data. Clinical survival fields are present for 1981 patients after loading (`reports/data/MARGINALS_PUBLIC_VS_SIM.md`); 528 patients have no overall-survival fields and are rejected by the loader.
- **Intended use:** subtype-stratified baseline hazards and marginals for the baseline-risk module; checking that the simulator is not mistaken for a fit to a Western cohort (`reports/data/MARGINALS_PUBLIC_VS_SIM.md`).
- **Not suitable for:** anything that needs serial laboratory draws (there are none), African-population claims (the cohort is not African), or recurrence-date analysis (relapse is a status and a duration, not a date of a confirming test).

## 2. Attributes the loader uses (verified against `/api/studies/brca_metabric/clinical-attributes`)
Patient file: `AGE_AT_DIAGNOSIS`, `SEX`, `CLAUDIN_SUBTYPE`, `OS_MONTHS`, `OS_STATUS` (`1:DECEASED` / `0:LIVING`), `RFS_MONTHS`, `RFS_STATUS` (`1:Recurred` / `0:Not Recurred`), `INFERRED_MENOPAUSAL_STATE`, `NPI` (the Nottingham prognostic index; the attribute is `NPI`, not `NOTTINGHAM_PROGNOSTIC_INDEX`).
Sample file: `ER_STATUS`, `PR_STATUS`, `HER2_STATUS`, `GRADE`, `TUMOR_STAGE` (values `0` to `4`).

## 3. Download (commands only; nothing is committed)
```bash
uv run python scripts/fetch_public_clinical.py          # writes data/external/ (git-ignored) and MANIFEST.json with SHA-256
uv run python scripts/compare_marginals_public_vs_sim.py
```
Or the study archive from the cBioPortal datahub (`brca_metabric`), whose `data_clinical_patient.txt` and `data_clinical_sample.txt` the loader (`contracts.loaders.cbioportal.load_study("METABRIC", patient_file, sample_file)`) reads directly (the `#` metadata lines are skipped).

## 4. Loader behaviour and rejection codes
A row that fails validation is rejected, counted and never repaired; the report holds no cell values. Codes: `MISSING_REQUIRED` (age, overall-survival months or status absent), `BAD_TYPE`, `OUT_OF_RANGE` (age outside 18 to 115, negative months), `BAD_ENUM` (status not `0:`/`1:`), `DUPLICATE_PATIENT`, `NO_SAMPLE_ROW`. Unknown receptor, stage or relapse values stay unknown.

## 5. Terms of use and what may be claimed
Terms are those of the study and of cBioPortal; the person who downloads is bound by them, and the owner must confirm they allow the intended use before any commercial use (`docs/HANDOVER.md`, H-002). Results on this cohort carry the label `T-P` and say nothing about performance in Nigeria.
