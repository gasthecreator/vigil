# Partner evaluation report: SYNTHETIC DRY RUN - NOT A RESULT

> Written by `scripts/run_partner_evaluation.py`; do not edit by hand. Status: **STOPPED** (rejection rate 0.106 exceeds PR-07 = 0.1; review the extraction with the partner (PREREGISTRATION section 5.6)).

**SYNTHETIC. The data are invented. This run rehearses the code path; it is not a result and says nothing about performance on real patients.**

Parameters: PROPOSED values of PREREGISTRATION.md (not ratified); PR-04 supplied on the command line. Bootstrap: 2000 resamples over patients, seed 20261018. Partition key identifier: `SYNTHETIC-DRYRUN-KEY`.

## Data quality (PREREGISTRATION section 5.6)

| table | rows in | clean | rejected | flagged |
|---|---:|---:|---:|---:|
| patients | 61 | 54 | 7 | 0 |
| baseline_profile | 62 | 52 | 9 | 0 |
| lab_observations | 2402 | 2151 | 249 | 1 |
| clinical_outcomes | 61 | 51 | 10 | 0 |

Rejection rate 0.106 against stop rate 0.1. Rejections by code: {'BAD_ENUM': 2, 'BAD_TYPE': 2, 'CONFLICTING_DUPLICATE': 4, 'INCOMPATIBLE_UNIT': 1, 'INCONSISTENT': 3, 'MISSING_REQUIRED': 2, 'NAME_CODE_MISMATCH': 1, 'ORPHAN_FK': 2, 'OUT_OF_RANGE': 4, 'PARENT_REJECTED': 252, 'UNKNOWN_ANALYTE': 1, 'UNKNOWN_UNIT': 1}. Complete-case patients: 49.

## What this report does not claim

No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.
