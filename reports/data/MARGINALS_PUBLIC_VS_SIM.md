# Baseline marginals: simulator vs METABRIC vs TCGA-BRCA

> Written by `scripts/compare_marginals_public_vs_sim.py`; do not edit by hand. The simulator column is **synthetic**; the others are public registry data downloaded with `scripts/fetch_public_clinical.py` (hashes in the JSON). This is a distance measurement, not a validation.

| quantity | simulator (Nigerian priors, SYNTHETIC) | METABRIC | TCGA-BRCA |
|---|---:|---:|---:|
| patients | 5000 | 1981 | 1084 |
| age mean (sd) | 48.6 (9.3) | 61.1 (12.9) | 58.4 (13.2) |
| age 10th / 50th / 90th | 37 / 49 / 61 | 43 / 62 / 77 | 41 / 58 / 77 |
| stage I | 4.9 % (of 5000) | 34.2 % (of 1466) | 17.0 % (of 1065) |
| stage II | 20.9 % (of 5000) | 56.3 % (of 1466) | 57.8 % (of 1065) |
| stage III | 49.7 % (of 5000) | 8.0 % (of 1466) | 23.4 % (of 1065) |
| stage IV | 24.5 % (of 5000) | 0.7 % (of 1466) | 1.8 % (of 1065) |
| ER+ | 51.8 % (of 5000) | 76.1 % (of 1981) | n/a |
| PR+ | 42.2 % (of 5000) | 52.5 % (of 1980) | n/a |
| HER2+ | 18.2 % (of 5000) | 12.5 % (of 1980) | n/a |
| subtype TNBC-like | 39.5 % | 23.4 % | 18.1 % |
| subtype HER2+ | 18.2 % | 12.3 % | 8.3 % |
| subtype HR+HER2- | 42.3 % | 64.3 % | 73.7 % |
| age KS vs simulator | - | D = 0.46 | D = 0.37 |

## Loader reports (real files)

| study | patients in file | loaded | rows rejected | rejections by code:field |
|---|---:|---:|---:|---|
| METABRIC | 2509 | 1981 | 528 | {'MISSING_REQUIRED:age': 11, 'MISSING_REQUIRED:os_months': 528, 'MISSING_REQUIRED:os_status': 528} |
| TCGA-BRCA | 1084 | 1084 | 0 | none |

## Notes

- Subtype for the public cohorts is the PAM50/Claudin-low label mapped to receptor-style groups (Basal and claudin-low to TNBC-like); the simulator draws receptor-style groups directly. The mapping is approximate and is the reader's to judge.
- Stage fractions use stage-known patients only; METABRIC stage 0 is excluded from the four-way split. METABRIC and TCGA are surgical cohorts, so stage IV is rare by design; the simulator's stage IV share is a de novo metastatic presentation prior.
- TCGA-BRCA PanCancer Atlas clinical attributes carry no receptor status, so TCGA receptor rows are empty.
- Differences are expected. The simulator's priors come from the Nigerian evidence in docs/EVIDENCE.md (E7, E12; both currently graded SECONDARY), not from these cohorts; the report quantifies the gap and does not claim the simulator fits any of them.
