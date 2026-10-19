# Core ML quality rerun — 2026-10

## Scope and evidence boundary

This pass follows `docs/MASTER_PLAN.md`, `docs/ML_PROGRAM.md`, the phase prompts under `docs/prompts/`, and the binding simulator/evaluation contracts. It focuses on synthetic cohort generation, landmark labels, feature handling, baseline fitting, leakage checks, survival metrics, and the K1/K3 engine paths. There is no real clinical longitudinal cohort in the repository, so this work cannot retrain or optimize a clinically valid model. The new experiment is synthetic research only.

## Remediated in this branch

- Landmark labels now distinguish recurrence, competing events, and early censoring. Unknown outcomes remain missing and learned classifiers require explicit IPCW weights.
- Simulator population assumptions are moved from code literals into versioned profiles. The balanced profile is explicitly synthetic and is not a country-population estimate.
- Unavailable measurements and derived features remain missing, with availability indicators. B3, B4, and the fast landmark logistic baseline fit median imputers on training data only.
- The shuffled-label canary now fits imputation within each cross-validation training fold, preventing held-out feature distributions from informing preprocessing.
- IPCW AUC evaluation uses a sorted weighted concordance calculation. Undefined AUC/Brier results return NaN instead of plausible-looking chance/zero scores.
- The fast landmark class description now identifies the fitted prediction path as a logistic research baseline. It refuses prediction before fit and preserves missingness instead of inserting assumed clinical values.
- The Bayesian K3 posterior-check helper no longer inserts a fixed normality p-value or a default marker trace. Its output still does not establish a valid Bayesian joint model (see unresolved items).

## Unresolved model validity findings

### K3 Bayesian joint model is not the registered model

`packages/vigil-ml/vigil_ml/joint_model.py::BayesianJointModelK3` uses fixed marker centering, fixed priors and hazard constants, and a row-level linear sampler without patient random effects, splines/GP trajectories, competing-risk likelihood, or the registered shared-parameter structure. Its fast sibling predicts with a regularized logistic classifier; the empirical-Bayes state utility is not part of prediction. Neither path meets `docs/ML_PROGRAM.md` §3.3's K3 definition. The old class name, convergence output, and synthetic PPC test must not be read as evidence that the planned joint model was implemented or validated. A separate proposal records the replacement path.

### K1 has a second, incompatible inference path

`packages/vigil-ml/vigil_ml/kinetic_k1.py` still maps absent fields to assumed constants and then `nan_to_num(..., nan=0.0)`. `HybridKineticModelK1.fit` derives a pseudo-burden target with a fixed multiplier and a growth regularizer around a fixed value. This differs from `packages/vigil-ml/vigil_ml/k1.py`, whose runtime path accepts `K1Observations` and can return prior-only output. The existing audit retracted K1 performance claims; these paths need a separate, registered consolidation and simulation-based validation before any K1 retraining claim.

### Legacy performance gates remain unresolved

The fixed synthetic AUC floors in `packages/vigil-ml/tests/test_baselines_sanity.py` fail after censor-aware labels are used. They remain unchanged under the repository rule against working around overseer-owned gates. The censor-aware gate proposal requests a replacement based on an independent, pre-registered study. Until that decision, the full changed model-gate suite is not green and this branch is not merge-ready.

## Experiment status

`EXP-CORE-ML-001` was aborted and `EXP-CORE-ML-002` was withdrawn for an access-log code-SHA mismatch. Their seed sets are retired and their metrics are not selection evidence. `EXP-CORE-ML-003` has a preregistration committed before implementation, a new seed set, separate calibration, six grouped shuffled-label canaries, and a clean-tree SHA guard. It must be run only after the implementation is committed and the checkout is clean.

## Verification limits

The final package command `./.venv/bin/pytest packages/vigil-core/tests packages/vigil-eval/tests packages/vigil-ml/tests packages/vigil-sim/tests tests/clinical/test_partner_analysis.py` completed with 477 passed and two failures: `test_gbm_reaches_at_least_single_threshold_auc` and `test_k3_joint_model_distinct_from_single_threshold`. Both are the pre-existing fixed-performance gate failures covered by `PROP-CORE-ML-CENSOR-AWARE-GATE.md`; their thresholds remain unchanged. The synthetic partner dry-run was regenerated with `./.venv/bin/python scripts/run_partner_dry_run.py`, and `test_committed_dry_run_reports_reproduce_byte_for_byte` passes. Ruff, byte-compilation, and `git diff --check` pass. The simulator wheel build could not be verified because the package index was unreachable while resolving the build backend. No claim is made that historical Phase 2, K1, or later model reports have been regenerated under the corrected label/feature contract.
