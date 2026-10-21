# EXP-CORE-ML-003: Censor-aware, independently calibrated synthetic core-model tuning

## Status and timing

This pre-registration and the runner/shared implementation are committed before this study's test cohort is accessed or any results are emitted. EXP-CORE-ML-001 was aborted and EXP-CORE-ML-002 was withdrawn for an access-log SHA mismatch. Neither study seed set is reused here.

## Question and estimand

Can validation-only tuning improve fixed-horizon recurrence prediction for the B3 regularized logistic horizon baseline, B4 XGBoost horizon baseline, or fast landmark logistic research baseline relative to the rule and prevalence baselines on independent draws from one declared synthetic stress profile? The estimand is performance on synthetic landmark rows with censoring weights and equal total fit weight per determinable patient. Competing events before the horizon are known non-recurrence; early loss/admin censoring is unknown.

## Data and split

- Generator: G1 smooth kinetics; `synthetic_population_v1.json` (`balanced_synthetic_v1`). This is a neutral synthetic stress profile, not a Nigerian population estimate or a clinical calibration.
- Four independently generated cohorts, each with 1,000 synthetic patients and 730 days of follow-up: train seed 43001, calibration seed 43002, validation seed 43003, test seed 43004. Cohort patient IDs are namespaced and verified disjoint.
- Fixed horizon: 365 days. Target is observed clinical recurrence in this simulator; it does not estimate latent biological recurrence under partial verification.
- Fit IPCW is estimated within each split using its own follow-up and event arrays. Fit weights are normalized to equal total weight for each determinable patient while preserving relative within-patient IPCW weights.

## Candidates and frozen search

- B3 regularized logistic horizon classifier: `C ∈ {0.05, 0.5, 5.0}`, L2 penalty, `lbfgs`, `max_iter=2000`.
- B4 XGBoost horizon classifier: `max_depth ∈ {2, 3}`, `n_estimators ∈ {50, 150}`, `learning_rate ∈ {0.03, 0.05}`, `n_jobs=1`, binary logistic objective, fixed model seed.
- Fast landmark logistic research baseline (legacy class name `FastLandmarkJointModel`): `C ∈ {0.1, 1.0, 10.0}`. This is neither Bayesian nor the joint model specified in ML_PROGRAM §3.3; report the exact implementation name.
- Context comparators: empirical training prevalence, the fixed single-threshold rule, and the velocity rule.
- B1's cutoff is read from `ANALYTE_REGISTRY["ca_15_3"].plausibility.reference_high`. B2 retains the legacy comparator settings: 0.08 CA 15-3 slope units/day and a 2.0 multiplier on CEA slope before comparison. These are explicit, unvalidated research assumptions, not clinically supported cutoffs; B2 is not tuned or interpreted as clinical guidance.
- Select one configuration per learned family by minimum validation IPCW Brier score. Ties within 1e-12 resolve lexicographically by the exact parameter ID. No test data influences selection.

## Calibration and evaluation

- Fit one weighted logistic (Platt) calibration model per non-prevalence model on the independent calibration cohort, using only determinable rows and patient-equalized IPCW weights. Use scikit-learn logistic regression with L2 penalty, `C=1.0`, `max_iter=2000`, and random state 43002. The prevalence comparator remains the training prevalence estimate.
- Evaluate calibrated predictions once on the fresh test cohort. Primary descriptive metric: IPCW Brier score. Secondary: IPCW time-dependent AUC and IPCW calibration error.
- Report every candidate's validation score, selected parameters, all three test metrics, and paired test differences against the calibrated B1 rule with patient-cluster percentile 95% bootstrap intervals (500 replicates; seed 43005). Undefined metrics or fewer than 400 valid bootstrap replicates abort the result; they are not replaced by defaults.
- No clinical threshold, utility, deployment, or clinical performance claim is made. No multiplicity-adjusted confirmatory claim is made; this is exploratory synthetic tuning.

## Integrity checks and stop rules

Before fitting: run latent-column, outcome-derived-feature, unobserved-value, and patient-grouped shuffled-label canaries on the exact training data. Run the shuffled-label canary for B0, B1, B2, B3, B4, and the fast landmark logistic research baseline. Seeds: B0=43006, B1=43007, B2=43008, B3=43009, B4=43010, fast landmark=43011. Every shuffled-label AUC must be at most 0.60. Verify disjoint IDs, binary-or-missing labels, finite nonnegative weights, zero weight for early-censored labels, and both classes in every fit. Abort on failure. Keep all candidates and all scores. Do not revise the grid, seeds, horizon, or metric after results are accessed. Any later protocol change requires a new experiment ID and new seeds.

## Limits

One synthetic G1 configuration cannot establish transport to G2/G3, another site or lab, or real clinical data. The simulator's verification process and other mechanisms remain assumptions. Results are not clinical evidence and cannot identify a deployable or clinically optimal model. Prior exposed or invalid result artifacts are not used for selection.
