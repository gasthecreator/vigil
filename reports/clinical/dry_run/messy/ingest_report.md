# Partner ingestion report

| table | rows in | clean | rejected | flagged |
|---|---:|---:|---:|---:|
| patients | 61 | 54 | 7 | 0 |
| baseline_profile | 62 | 52 | 9 | 0 |
| lab_observations | 2402 | 2151 | 249 | 1 |
| clinical_outcomes | 61 | 51 | 10 | 0 |

Rejection rate 0.106 against stop rate 0.100: **EXCEEDS the stop rate. Stop and review the extraction with the partner.**

| rejection code | rows |
|---|---:|
| BAD_ENUM | 2 |
| BAD_TYPE | 2 |
| CONFLICTING_DUPLICATE | 4 |
| INCOMPATIBLE_UNIT | 1 |
| INCONSISTENT | 3 |
| MISSING_REQUIRED | 2 |
| NAME_CODE_MISMATCH | 1 |
| ORPHAN_FK | 2 |
| OUT_OF_RANGE | 4 |
| PARENT_REJECTED | 252 |
| UNKNOWN_ANALYTE | 1 |
| UNKNOWN_UNIT | 1 |

Exact duplicates dropped: 2. Cells normalised (case, spelling): 23. Complete-case patients (patient + baseline + outcome): 49 of 60.
