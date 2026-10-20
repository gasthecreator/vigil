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

The canonical-looking `k1.py` path also has unregistered assumptions: a fixed seven-visit schedule, uniform parameter bounds, a fixed CA 15-3 baseline and Gaussian noise scale, and fixed posterior normalization/calibration constants. Its `train_amortized` routine generates a simplified one-marker toy world itself, while `vigil-sim` has irregular visits, multiple analytes, site/lab shifts, censoring and partial verification. `k1.py`'s particle filter also adds fixed jitter to resampled particles. These are not automatically defects when they are explicit preregistered assumptions, but here they do not establish a model fitted to `vigil-sim`; the competing `kinetic_k1.py` path makes the public model identity ambiguous. Do not use either route's posterior, credible-interval or risk language as evidence for the registered K1 model until one canonical model is aligned with the simulator and independently checked.

### The core rerun has not regenerated all prior model evidence

EXP-CORE-ML-003 (single G1) and EXP-CORE-ML-004 (cross-generator, five replicates) were run under the then-current censoring/missingness workflow. ADR-0039 later corrected feature semantics, so both studies are now historical and stale for current model selection. EXP-CORE-ML-007 also ran once but is exploratory only because its preregistered pairwise contrast set was incomplete. EXP-CORE-ML-008 is the registered complete comparison on fresh seeds. Historical S1/S3/S9, VigilBench, K1/K2/K3/K4/K5/K6/M12 and benchmark outputs remain stale or unverified under the current contract unless their producers are rerun.

The M12 study has a separate provenance and contract defect: its frozen outputs have no corresponding access entry in the canonical `data/audit/frozen_test_access.jsonl`, and its runner predates the corrected early-censor label behavior. The old S10 log entry is not evidence for EXP-M12-001. The outputs are preserved as historical only; see `experiments/EXP-M12-001/PROVENANCE-AND-CONTRACT-AUDIT.md`.

The prompt history supports these as recurring, not hypothetical, risks: P2/P3 record hard-coded lead-time/latency fields, chance-level learned baselines, and an invalid K3 comparator; P3A/P3A2/P3A3 record formula-generated training curves, fake recovery checks, duplicate/aliased routes, hand-set blends and K1/simulator mismatch; P7 records model-visible latent-value leakage and a fabricated delta table. P15/P16 continue to require script-generated results, test access after clean commits, and reports that name what was not validated. See `docs/prompts/PROMPT-P2.md`, `PROMPT-P3.md`, `PROMPT-P3A.md`, `PROMPT-P3A2.md`, `PROMPT-P3A3.md`, `PROMPT-P7.md`, `PROMPT-P15.md` and `PROMPT-P16.md`.

### Legacy performance gates remain unresolved

The fixed synthetic AUC floors in `packages/vigil-ml/tests/test_baselines_sanity.py` fail after censor-aware labels are used. They remain unchanged under the repository rule against working around overseer-owned gates. The censor-aware gate proposal requests a replacement based on an independent, pre-registered study. Until that decision, the full changed model-gate suite is not green and this branch is not merge-ready.

## Experiment status

`EXP-CORE-ML-001` was aborted and `EXP-CORE-ML-002` was withdrawn for an access-log code-SHA mismatch. Their seed sets are retired and their metrics are not selection evidence. `EXP-CORE-ML-003` was preregistered before implementation, run from clean code SHA `5cf2faf8a16ac2f008b50257fbb1d5f060b88505`, and its result is recorded in [`experiments/EXP-CORE-ML-003/REPORT.md`](../../experiments/EXP-CORE-ML-003/REPORT.md); its access-log entry matches that SHA. The one-G1 scope and synthetic-only limits remain.

`EXP-CORE-ML-004` was preregistered before its runner, with a seed-collision issue found and corrected before test access. The runner and tests were committed at `032fd691a8724a956f8d08a56cba82d337489003`. Its one-time G1/G2/G3 test access is logged at that same SHA. The registered 1,000-resample patient-cluster bootstrap completed and generated its JSON/report; its intervals are historical because the current feature implementation differs. Previously reported B4 metrics are retained in the immutable output, but are not current model-selection evidence. They were simulator-conditional synthetic results, never real-site transport or clinical performance claims. The end-to-end run took about an hour, exposing a substantial bootstrap implementation/runtime cost that should be optimized only in a separately preregistered follow-up before future frozen-test access.

## Verification limits

Historical package verification before the partner adapter correction: 477 passed and two fixed AUC gates failed; the simulator wheel build was blocked by package-index unavailability. These results are superseded by the later full-suite run below. No claim is made that historical Phase 2, K1, or later model reports have been regenerated under the corrected label/feature contract.


## EXP-CORE-ML-007 status

EXP-CORE-ML-007 ran once at SHA `7efc7f7bf716f988a464a2e02a72dd13d44c65a2`; its output is preserved in its generated JSON/report. Post-access audit found the preregistered contrasts against B0/B2 were absent and the dataset-name strings referred to EXP-004. The append-only access log contains three metadata corrections tied to original timestamps and actual EXP-007 seed tuples. The study is exploratory only and cannot support model selection. EXP-CORE-ML-008 preregisters the complete paired contrast set on new seeds. Its runner reports B3/B4 paired deltas against B0, B1, and B2, includes a contract regression for every comparator/metric, and uses exact EXP-008 access names. Its four non-data-access runner tests pass; no EXP-008 test cohort has been generated.


## EXP-CORE-ML-008 status

EXP-CORE-ML-008 ran once at SHA `7db2ca0e5e38078d48e78ff3f0255d970a9b4736` on new seeds after preregistration. Its exact G1/G2/G3 access records match the result SHA and caller. All 72 paired contrasts vs B0/B1/B2 have 1,000 valid patient-cluster resamples. The B4 synthetic G3 IPCW AUC is 0.7907 (95% CI 0.7782–0.8036) and Brier is 0.1008 (0.0966–0.1049); its ECE is 0.0478, with B4-minus-B1 ECE +0.0170 (0.0131–0.0254), a calibration-error tradeoff. All values are synthetic, generator-conditional, and not a clinical or real-site optimum. The saved-JSON report regenerates byte-for-byte.

The full registered baseline comparison is now present, but package C remains open: two legacy fixed AUC assertions and the K3 shuffled-outcome canary are red; overseer proposal dispositions are pending; the C closure requirements for decision curves, alert burden, subgroup and runtime evidence have not been met.

## Additional simulator-profile finding (Q-7 B)

The active baseline profile `balanced_synthetic_v1` did not declare its facility, verification, or measurement-missingness assumptions; those values were selected by literal fallbacks in `generators.py`. Consequently, the EXP-CORE-ML-008 profile hash alone does not describe its complete synthetic data-generating assumptions. Preserve its result as historical and do not use it as current selection evidence. A new `balanced_synthetic_core_v3` profile now declares those settings plus baseline symptom probabilities, visit-interval distribution, and financial-friction range. A source patch reads the latter settings from the profile while retaining compatibility defaults for historical profiles. The v3 profile has not been used to generate evaluation results; it requires a new preregistered experiment before any model comparison. Other mechanistic constants (including burden-to-analyte coupling, symptom thresholds, treatment effects, and generator-specific kinetic parameters) remain to be inventoried and either explicitly configured or justified as model equations in package B.


## Latest verification after downstream adapter repair

The full repository suite completed with 910 passed, 18 skipped, 3 failed, and 0 errors (loopback enabled for resilience tests). The three failures are `test_k3_joint_model_canaries` (K3 shuffled-outcome AUC 0.6136378551 against the unchanged 0.60 ceiling), `test_k3_joint_model_distinct_from_single_threshold` (AUC 0.7108199278 against the unchanged 0.72 floor), and `test_gbm_reaches_at_least_single_threshold_auc` (B1 AUC 0.5488445517 against the unchanged 0.65 floor). The latter two are fixed-score gates covered by the pending censor-aware-gate proposal; the canary is covered by its separate pending proposal. No acceptance assertion was changed. The partner adapter now passes explicit competing-event type and administrative-censor day to the stricter feature contract; all 23 partner-analysis tests pass and the synthetic dry-run reports were regenerated. All 15 M12 tests pass, including fail-closed unknown-label/empty-cohort guards. The simulator profile change has 13 focused tests passing. EXP-008 runner tests pass, including saved-JSON byte parity. Ruff, byte-compilation, and `git diff --check` pass. These checks do not close packages A–I: Q-7 remains open for the scientific and historical evidence requirements listed in the repair plan.
