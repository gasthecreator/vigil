# Proposal: separate frozen-cohort access from result reproduction

## Problem

EXP-K1-004 records a one-time G3 access and refuses to run again when `ACCESS_LOG.json` exists. This protects the no-tuning rule. At the same time, the repository standard requires reported results to be regenerable from a clean checkout. The current reproduction script performs the original one-time run but cannot reproduce a committed result from a clean checkout containing its access log and reports.

## Evidence base

The full synthetic result is recorded in `experiments/EXP-K1-004/results.json`; its SHA-256 matches the completed access log. The run used source commit `bbc1eded06ee9445e8a49c2a0e30324d46b45f42`, protocol 1.10, and one G3 transfer access. The runner's current guard correctly blocks a second execution.

## Proposed change

For future studies, separate cohort generation from metric reproduction. Commit immutable, content-addressed generated cohorts (or sufficient deterministic generation manifests) before evaluation; make the analysis command consume those frozen inputs without re-running selection or fitting. Record distinct access and replay events. The replay path should verify the original source/config/data hashes and refuse any changed estimator or tuning path.

## Q-7 safety repair

The current `reproduce_k1_exp004.sh` calls `train_k1_amortized.py` before the runner checks the one-time access log. That ordering can overwrite the committed neural artifacts and training record, then fail at the access guard. The trainer now refuses to run when EXP-K1-004 training/results/access artifacts already exist; a regression test confirms the call exits without changing the training record or weights. This prevents destructive replay but does not make the experiment reproducible. Keep the proposal's cohort-replay decision open.

## Evaluation and rollback

Verify a clean-checkout replay reproduces all registered metrics and patient-bootstrap intervals while preserving the original frozen access record. If deterministic replay changes any metric or cannot prove input identity, keep the committed result as authoritative and do not claim regeneration.

## Decision needed

Overseer review is needed on the acceptable meaning of “one access” for deterministic replay. Do not bypass the existing access-log guard in EXP-K1-004.
