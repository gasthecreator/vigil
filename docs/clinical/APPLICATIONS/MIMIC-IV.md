# Application draft: MIMIC-IV v3.1 (PhysioNet credentialed access)

> **DRAFT-UNREVIEWED. NOT SUBMITTED.** Bracketed fields are for the owner. The process (credentialed user, CITI "Data or Specimens Only Research", signed Data Use Agreement 1.5.0) was read from https://physionet.org/content/mimiciv/3.1/ on 2026-10-18. Whatever the live form asks for overrides this draft.

## Applicant
- Name: [OWNER] Affiliation: [OWNER] ORCID: [OWNER] PhysioNet account e-mail: [OWNER]
- Training: CITI "Data or Specimens Only Research" certificate, completion date [OWNER], certificate number [OWNER]
- Reference / supervisor (if the form asks): [OWNER]

## Project title
Longitudinal laboratory behaviour of tumour and organ-function markers in patients with breast cancer: plausibility bounds and kinetic priors for an open decision-support research platform (Vigil).

## Purpose and justification (one paragraph for the form)
We build and evaluate open research software that flags unexpected changes in serial laboratory results during breast-cancer follow-up. MIMIC-IV is used for three narrow things only: (1) the real distribution and plausibility bounds of routine laboratory analytes (units, outliers, transcription artefacts) to harden the unit-conversion and plausibility checks; (2) the frequency of repeated measurements per patient, to test the software on irregular sampling; (3) generic time-series pretraining that is later validated elsewhere. We do not claim, and will not claim, that results on this data say anything about outpatient breast-cancer surveillance or about African populations: MIMIC-IV is a single-centre US hospital and intensive-care dataset.

## Data requested
`hosp.patients`, `hosp.admissions`, `hosp.diagnoses_icd` (breast-cancer ICD-9/ICD-10 codes to define the cohort), `hosp.labevents`, `hosp.d_labitems` (analytes in the Vigil registry: CA 15-3 where present, CEA, ALT, AST, ALP, GGT, creatinine, haemoglobin, WBC, platelets, albumin, bilirubin). Minimum necessary: no notes, no imaging, no ICU chart events.

## Data management plan
- Stored only on encrypted disks of named project members; never on a shared drive, a public repository or a third-party cloud service.
- **No data are sent to any hosted AI or language-model service**, and no model output derived from row-level data is published; only aggregate statistics with small cells suppressed (fewer than 10 patients).
- No attempt to re-identify, no linkage to any other dataset.
- The repository never contains MIMIC rows (`data/external/` is git-ignored; the loader reads local files only). Fixtures in `data/fixtures/` are invented.
- Retention: until the project ends, then deleted; deletion recorded.

## Expected outputs
Aggregate plausibility tables and a dataset card (`data/dataset_cards/DATASET-CARD-MIMIC-IV.md`), labelled `T-P`.

## Honest limitations stated to the reviewer
Critical-care population, inpatient sampling, few CA 15-3 measurements, no recurrence dates linked to labs. Use is for infrastructure hardening, not for validating surveillance performance.

## Signature
[OWNER] Date: [OWNER]
