# Dataset Card: TCGA-BRCA (Breast Invasive Carcinoma, PanCancer Atlas clinical tables)

> Facts below were read from the NCI GDC API on 2026-10-18 (`docs/evidence/excerpts/P2_gdc_tcga_brca_project.md`, audited by `scripts/audit_excerpts.py`) and from cBioPortal study `brca_tcga_pan_can_atlas_2018`, or are computed by `scripts/compare_marginals_public_vs_sim.py`. The earlier fixture of this repository used legacy field names (`bcr_patient_barcode`, ...) that the cBioPortal tables do not have; the loader now reads the real layout.

## 1. Summary
- **Source:** GDC project `TCGA-BRCA` ("Breast Invasive Carcinoma"), 1098 cases in the GDC project record; the PanCancer Atlas clinical table on cBioPortal has 1084 patients (`reports/data/MARGINALS_PUBLIC_VS_SIM.md`).
- **Tier:** `T-P`. **Intended use:** stage and survival marginals for the baseline-risk module; subtype mix.
- **Not suitable for:** serial laboratory data (none), receptor-status analyses from this table (the PanCancer Atlas clinical attributes carry no ER/PR/HER2 status; subtype is the PAM50 label), African-population claims, or recurrence-date analysis (`DFS_MONTHS` and `DFS_STATUS` give a duration and a status).

## 2. Attributes the loader uses (verified against `/api/studies/brca_tcga_pan_can_atlas_2018/clinical-attributes`)
`AGE`, `SEX`, `SUBTYPE`, `OS_MONTHS`, `OS_STATUS`, `AJCC_PATHOLOGIC_TUMOR_STAGE` (`STAGE X` is read as unknown), `DFS_MONTHS`, `DFS_STATUS` (`1:Recurred/Progressed` / `0:DiseaseFree`), `GRADE` (sample file).

## 3. Download (commands only; nothing is committed)
```bash
uv run python scripts/fetch_public_clinical.py          # writes data/external/ (git-ignored) and MANIFEST.json with SHA-256
uv run python scripts/compare_marginals_public_vs_sim.py
```
Or the study archive `brca_tcga_pan_can_atlas_2018` from the cBioPortal datahub, read with `contracts.loaders.cbioportal.load_study("TCGA-BRCA", patient_file, sample_file)`.

## 4. Loader behaviour and rejection codes
Same policy as METABRIC: a failing row is rejected with a code (`MISSING_REQUIRED`, `BAD_TYPE`, `OUT_OF_RANGE`, `BAD_ENUM`, `DUPLICATE_PATIENT`, `NO_SAMPLE_ROW`) and counted; the report holds no cell values. The table includes 12 male patients; they are kept and carry `sex = MALE`.

## 5. Terms of use and what may be claimed
GDC and TCGA data-use terms apply to the person who downloads; the owner must confirm them before any commercial use (`docs/HANDOVER.md`, H-002). Results carry the label `T-P`.
