# EXP-CORE-ML-010: Development-fit verification propensity validation

## Status and scope

This protocol is committed before the runner or results. It validates a
verification propensity fitted on a synthetic development split and applied to
an independent synthetic test split. It does not select a recurrence model,
establish clinical performance, validate a real verification mechanism, or
support use with partner data.

## Question and estimand

Does a development-fit logistic verification model, using training-only
imputation plus an explicit missingness indicator, recover the finite test
cohort's complete-data sensitivity, specificity, prevalence, Brier score, and
ROC AUC under the registered MCAR/MAR mechanism? Does it remain biased when
verification depends on the unobserved outcome (MNAR)? The estimand is the
test cohort's full synthetic metric for a fixed score at threshold 0.5.

## Synthetic design

- Conditions: MCAR, MAR, MNAR; 100 independent replicates per condition.
- Each replicate has 2,500 independent development patients and 2,500
  independent test patients.
- Seed: `20261101 + condition_offset + replicate` for development and
  `20261101 + 500000 + condition_offset + replicate` for test; condition
  offsets are MCAR `0`, MAR `100000`, MNAR `200000`; replicate is 0–99.
- In each split, draw `X ~ Normal(0,1)`, then
  `Y ~ Bernoulli(logistic(-1 + 1.2 X))`, then marker `M = X + Normal(0,0.5)`,
  then a marker-observation indicator with probability
  `logistic(-1 + 0.5 X)`. Replace unobserved M with missing.
- The fixed risk score is `logistic(-1 + 1.2 X)` and threshold is `0.5`.
- For propensity fitting/prediction, define `M_missing = 1` when M is absent;
  impute M with the median of observed development M only; use `[X, M_imputed,
  M_missing]` as predictors. A split with no observed development marker
  aborts; never substitute a literal value for the median.
- Verification probabilities: MCAR `0.60`; MAR
  `logistic(-0.5 + X + 0.4 M_imputed + 0.4 M_missing)`; MNAR adds
  `1.0 * (2Y - 1)` to the MAR linear predictor. Generate verification after
  the feature vector and outcome using NumPy `default_rng(seed)`.
- Fit `sklearn.linear_model.LogisticRegression(max_iter=500)` on development
  verification status and development features only. Apply that model to test
  features. Do not fit or recalibrate the propensity model using test
  verification status or outcomes.
- The evaluation receives test risk scores, test verification indicators,
  labels only for verified patients, and development-fitted test propensities.
  Full test labels are used only for the synthetic reference metric.

## Analysis

- Compare complete-case and development-fit IPW against the full test-cohort
  reference for sensitivity, specificity, prevalence, Brier, and AUC.
- Report all 100 replicate rows per condition, including errors, verification
  counts, minimum test propensity, maximum inverse weight, and effective sample
  size. Summaries are mean estimate, mean error, error SD, and 2.5th/97.5th
  error percentiles. Do not suppress undefined values or conditions.
- Every IPW result must be defined; otherwise the run is recorded as failed and
  these seeds are not rerun. No pass threshold or hypothesis test is used.
- The MNAR condition is a negative identification control. It must be reported
  as biased if it is biased; do not alter the condition, model, or features
  after results are observed.

## Integrity and limits

- Commit the runner before execution. It must refuse a dirty worktree or
  pre-existing access/results/report outputs, and record exact source,
  preregistration, runner, evaluator, and lock hashes in `ACCESS_LOG.json`.
- Generate `results.json` and `REPORT.md` once; report must be a deterministic
  rendering of the saved JSON. Unit tests cover formulas, seed separation,
  train-only imputation, propensity source separation, report parity, and
  overwrite refusal without running the 300 registered cohort pairs.
- This evaluates one correctly specified, transport-stable synthetic
  verification model. It does not prove real-world exchangeability, positivity,
  mechanism stability between development and test, or MAR. Partner analysis
  still requires clinical/statistical ratification, valid data, and its own
  frozen preregistration before any real-data access.
