# EXP-CORE-ML-012 protocol deviation and invalidation

**Status: invalidated before its registered analysis.** The frozen preregistration remains unchanged as the historical record. No `ACCESS_LOG.json`, registered `results.json`, or registered `REPORT.md` was produced for EXP-CORE-ML-012.

## Deviation

During implementation verification on 2026-10-20, `experiments/EXP-CORE-ML-012/test_run.py::test_small_replicate_contract_and_report_are_deterministic` called `one_replicate(0, profile)` with the registered replicate-0 cohort seeds and a reduced cohort size of 24. It generated the same deterministic first 24 patient records for each of G1, G2, and G3 that would occur in the registered replicate-0 cohorts. The test computed the replicate diagnostics in memory; it did not write or retain the simulated records or diagnostic result. The test was executed more than once with the same seeds and therefore repeated the same prefix rather than creating independent draws.

The generated prefixes were:

- G1: seed `20571201`, patient IDs `VIG-PT-00001` through `VIG-PT-00024`.
- G2: seed `20681201`, patient IDs `VIG-PT-00001` through `VIG-PT-00024`.
- G3: seed `20791201`, patient IDs `VIG-PT-00001` through `VIG-PT-00024`.

Because those prefixes overlap the frozen replicate-0 seed allocation, EXP-CORE-ML-012 cannot provide its preregistered five-replicate result without reusing accessed deterministic data. No portion of the partial output is used in another experiment, tuning, or report. Its runner and test were moved to EXP-CORE-ML-013, where the cohort test uses separately reserved test-only seeds and the study uses a fresh seed allocation.

## Corrective controls

- The original EXP-CORE-ML-012 `PREREG.md` was not edited.
- The EXP-CORE-ML-013 preregistration freezes the new seed allocation, exact source commit, and source hashes before any new study-cohort generation.
- Test-only cohort seeds are distinct from the EXP-CORE-ML-013 registered seeds.
- EXP-CORE-ML-013's runner refuses dirty worktrees and pre-existing access/result/report artifacts, and writes the access record before its first cohort generation.
