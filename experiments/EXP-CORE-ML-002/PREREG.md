# EXP-CORE-ML-002: Censor-aware, independently calibrated synthetic core-model tuning

## Status and timing

This pre-registration is committed before this study's runner, results, or model-selection output. EXP-CORE-ML-001 was aborted after its test cohort was accessed but before metrics were emitted; none of its seeds are reused here.

## Question and estimand

Can validation-only tuning improve fixed-horizon recurrence prediction for B3, B4, or the fast landmark K3 approximation relative to the rule and prevalence baselines on independent draws from one declared synthetic stress profile? The estimand is performance on synthetic landmark rows with censoring weights and equal total fit weight per determinable patient. Competing events before the horizon are known non-recurrence; early loss/admin censoring is unknown.

## Data and split

- Generator: G1 smooth kinetics; `synthetic_population_v1.json` (`balanced_synthetic_v1`). This is a neutral synthetic stress profile, not a Nigerian population estimate or a clinical calibration.
- Four independently generated cohorts, each with 1,000 synthetic patients and 730 days of follow-up: train seed 42001, calibration seed 42002, validation seed 42003, test seed 42004. Cohort patient IDs are namespaced and verified disjoint.
- Fixed horizon: 365 days. Target is observed clinical recurrence in this simulator; it does not estimate latent biological recurrence under partial verification.
- Fit IPCW is estimated within each split using its own follow-up and event arrays. Fit weights are normalized to equal total weight for each determinable patient while preserving relative within-patient IPCW weights.

## Candidates and frozen search

- B3 regularized logistic hazard: `C ∈ {0.05, 0.5, 5.0}`.
- B4 XGBoost: `max_depth ∈ {2, 3}`, `n_estimators ∈ {50, 150}`, implementation-default learning rate, fixed model seed.
- K3 fast landmark approximation: `C ∈ {0.1, 1.0, 10.0}`. This is not the Bayesian joint model specified in ML_PROGRAM §3.3; report the exact implementation name.
- Context comparators: empirical training prevalence, the fixed single-threshold rule, and the velocity rule.
- Select one configuration per learned family by minimum validation IPCW Brier score. Ties within 1e-12 resolve lexicographically by the exact parameter ID. No test data influences selection.

## Calibration and evaluation

- Fit one weighted logistic (Platt) calibration model per non-prevalence model on the independent calibration cohort, using only determinable rows and patient-equalized IPCW weights. Use scikit-learn logistic regression with L2 penalty, `C=1.0`, `max_iter=2000`, and random state 42002. The prevalence comparator remains the training prevalence estimate.
- Evaluate calibrated predictions once on the fresh test cohort. Primary descriptive metric: IPCW Brier score. Secondary: IPCW time-dependent AUC and IPCW calibration error.
- Report every candidate's validation score, selected parameters, all three test metrics, and paired test differences against the calibrated B1 rule with patient-cluster percentile 95% bootstrap intervals (500 replicates; seed 42005). Undefined metrics or fewer than 400 valid bootstrap replicates abort the result; they are not replaced by defaults.
- No clinical threshold, utility, deployment, or clinical performance claim is made. No multiplicity-adjusted confirmatory claim is made; this is exploratory synthetic tuning.

## Integrity checks and stop rules

Before fitting: run latent-column, outcome-derived-feature, unobserved-value, and patient-grouped shuffled-label canaries on the exact training data; shuffled-label AUC must be at most 0.60 for B3 and B4. Verify disjoint IDs, binary-or-missing labels, finite nonnegative weights, zero weight for early-censored labels, and both classes in every fit. Use canary seeds 42006 and 42007. Abort on failure. Keep all candidates and all scores. Do not revise the grid, seeds, horizon, or metric after results are accessed. Any later protocol change requires a new experiment ID and new seeds.

## Limits

One synthetic G1 configuration cannot establish transport to G2/G3, another site or lab, or real clinical data. The simulator's verification process and other mechanisms remain assumptions. Results are not clinical evidence and cannot identify a deployable or clinically optimal model. Prior exposed or invalid result artifacts are not used for selection.
