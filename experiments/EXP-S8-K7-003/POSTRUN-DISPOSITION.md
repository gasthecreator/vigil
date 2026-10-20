# EXP-S8-K7-003 post-run validity disposition

**Disposition:** NONCONFORMING; do not use as evidence of estimator recovery.  
**Date:** 2026-10-20  
**Run status:** Completed once; outputs and original preregistration remain immutable.

## Findings

1. The fold-seed mapping `s + 1,000,000` for point estimates and `s + 1,000,001 + b` for bootstrap replicate `b` is not disjoint across purposes. For adjacent cohort seeds, the point fold seed for seed `s + 1` equals bootstrap fold seed 0 for seed `s`. Thus the preregistered statement that namespaces were disjoint is false.
2. Bootstrap sampling draws rows with replacement and passes those rows to ordinary `StratifiedKFold`. Repeated copies of one source patient are treated as different units and can be assigned to different folds. The same patient's outcome can therefore contribute to nuisance fitting in one fold and an ostensibly held-out copy in another, violating patient-level cross-fitting.

These are design defects, not reasons to tune or replay the consumed seeds. They invalidate the preregistered cross-fitting contract and any scientific interpretation of its H1 recovery/coverage criterion. The saved result file, report, completion manifest, preregistration, and access log are retained unchanged. Their checks establish byte/hash and arithmetic consistency only; the H1 label in the historical report is superseded by this disposition and must not be cited.

## Corrective action

EXP-S8-K7-004 has a new registration and fresh seed range. Its implementation must use purpose-separated, collision-checked seed mappings and group-aware stratified folds keyed by original source-patient identity in both point and bootstrap estimates. The corrected implementation, property tests, and source-bound pre-run access record must be committed before the one-time run. No K7-003 data are regenerated.
