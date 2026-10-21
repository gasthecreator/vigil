# EXP-CORE-ML-009: Verification-bias estimator validation

## Status and scope

This synthetic method-validation protocol is committed before its runner or
results. It evaluates the current complete-case and inverse-probability-of-
verification (IPW) estimators against known synthetic population metrics. It is
not a model-selection, clinical-performance, population-calibration, or
simulator-realism study. It does not validate latent recurrence in real data.

## Question and estimand

Across three registered verification mechanisms, how closely do complete-case
and the current `evaluate_ipw_verification` implementations recover the full
synthetic-cohort sensitivity, specificity, prevalence, Brier score, and ROC
AUC of a fixed risk score at a fixed threshold? The target is the finite
generated cohort's metric using all known synthetic outcomes. In MCAR and MAR,
the IPW estimator uses the fully observed covariate that drives verification.
In MNAR, verification additionally depends on the outcome, which is omitted
from the propensity features; this deliberate misspecification is a negative
identification control, not a method expected to recover the target.

## Data-generating design

- Three independent conditions: MCAR, MAR, and MNAR.
- Replicates: 100 per condition; cohort size: 2,500 per replicate.
- Base seed: `20261021`; condition offsets: MCAR `0`, MAR `100000`, MNAR
  `200000`; replicate `r` uses `base + condition_offset + r`.
- One covariate `X ~ Normal(0, 1)`; outcomes are drawn as
  `Y ~ Bernoulli(logistic(-1 + 1.2 X))`. The fixed score is
  `logistic(-1 + 1.2 X)`, and the fixed classification cutoff is `0.5`.
- MCAR verification probability is `0.60`.
- MAR verification probability is `logistic(-0.5 + X)`.
- MNAR verification probability is `logistic(-0.5 + X + 1.0 * (2Y - 1))`.
- All probabilities use the logistic function; use NumPy's `default_rng(seed)`.
  Generate `X`, then `Y`, then the Bernoulli verification indicator in that
  order. Verification features are the one-column matrix containing `X`.
- All labels are available to the simulator and full-cohort reference metric.
  Estimators receive only verified labels; unverified labels are replaced by
  `NaN` before the estimator call.

## Estimators and analysis

- Compare `evaluate_complete_case` and `evaluate_ipw_verification` with the
  fixed score, observed labels, verification indicator, verification feature,
  and cutoff above. Do not change the estimator implementation or inputs after
  outcomes are observed under this registration.
- For each replicate and metric, retain the full-cohort reference, both
  estimates, and estimate-minus-reference error. Do not drop undefined values;
  count and report them. The runner aborts if an IPW result is marked undefined
  for any registered replicate.
- For every condition and estimator, report mean estimate, mean error, error
  standard deviation, and 2.5th/97.5th error percentiles for each metric.
  Also report verification counts and the IPW maximum inverse weight and
  effective sample size per replicate.
- Report all replicate rows in JSON and generate the Markdown report only from
  that JSON. No pooled result may hide a failed condition.
- No hypothesis-test p-values or post-hoc pass/fail thresholds are used. The
  estimand comparison is descriptive method-validation evidence conditional
  on this simple synthetic design.

## Integrity and reproducibility

- The runner must refuse a dirty Git tree and existing result/access/report
  artifacts. Record the source commit, runner hash, Python and library versions,
  environment lock hash, seeds, conditions, and completion status in an
  immutable experiment-local `ACCESS_LOG.json`.
- The runner must write `results.json` and generated `REPORT.md` once. If a run
  fails after generation starts, preserve failure metadata and do not rerun
  these seeds; a corrected protocol requires a new experiment ID and new
  seeds.
- Add tests for the seed formula, condition probabilities, full-vs-masked
  labels, report parity, and refusal to overwrite existing outputs. Unit tests
  must not execute the registered 300 cohort replications.

## Limits

These experiments only show estimator behavior under the specified
one-covariate synthetic mechanisms. Correctness under MCAR/MAR does not prove
conditional exchangeability, positivity, correct propensity specification, or
transport to a partner cohort. Failure under MNAR confirms that the current
observed-data IPW path does not identify the target when outcome-dependent
verification is unmodeled. Any use of these estimators for patient or partner
data requires a separate preregistration, data approval, missingness
assumptions, validation design, and uncertainty analysis.
