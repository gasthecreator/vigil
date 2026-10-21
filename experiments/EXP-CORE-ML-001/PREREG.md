# EXP-CORE-ML-001: Censor-aware synthetic model tuning

## Status and timing

Pre-registration only. This file is committed before `run.py`, `results.json`, or any model-selection result is created. The study is synthetic research software evaluation; it cannot establish clinical performance.

## Question and estimand

Can validation-only tuning improve fixed-horizon recurrence discrimination and prediction error for B3, B4, or the fast landmark K3 approximation, relative to their untuned defaults, on independent draws from one declared simulator stress profile? The estimand is performance on synthetic landmark rows, with inverse-probability-of-censoring weighting and equal total contribution per patient during fitting. Competing events before the horizon are known non-recurrence outcomes; early loss/admin censoring is unknown.

## Data and split

- Generator: G1 smooth kinetics, with `synthetic_population_v1.json` (`balanced_synthetic_v1`). The file labels all input distributions as stress-test assumptions, not Nigerian estimates or clinical calibration.
- Training, validation, and test are separate independently generated cohorts with seeds 41001, 41002, and 41003 respectively; each contains 1,000 synthetic patients and 730 days of follow-up.
- No patient contributes to more than one cohort. `WindowedFeatureExtractor` creates landmark rows; all fitting weights are computed only from the corresponding cohort's follow-up and event arrays. The test cohort is accessed once after choices are frozen.
- Horizon: 365 days. The event is *observed clinical recurrence* as represented in the simulator; this does not estimate biological recurrence under partial verification.

## Candidates and fixed search space

- B3 regularized logistic hazard: `C ∈ {0.05, 0.5, 5.0}`.
- B4 XGBoost: `max_depth ∈ {2, 3}`, `n_estimators ∈ {50, 150}`, with the implementation default learning rate and fixed seed.
- K3 fast landmark approximation: `C ∈ {0.1, 1.0, 10.0}`. It is not the Bayesian joint model specified in ML_PROGRAM §3.3 and will be reported by its exact implementation name.
- Comparators: empirical prevalence, the fixed CA 15-3 rule, and the velocity rule. They are context baselines, not tuned models.

## Selection, metrics, and uncertainty

- Select one configuration per learned family by lowest validation IPCW Brier score at 365 days. Ties within 1e-12 choose the first configuration in the ordered grid above. No test metric may influence configuration, feature, model, or threshold selection.
- Report on test: IPCW time-dependent AUC, IPCW Brier score, IPCW calibration error, determinable patient and landmark counts, and patient-cluster bootstrap 95% percentile intervals (500 replicates; seed 41004). Report each model and paired differences against B1.
- Discrimination and prediction error are descriptive synthetic outcomes. There is no clinical threshold, net-benefit claim, deployment claim, or claim that the best model is clinically optimal.
- No multiplicity-adjusted confirmatory claim is made; the validation grid is an exploratory hyperparameter selection procedure. All candidates and selected parameters are published.

## Data-quality and validity checks

Before fit: assert no latent/outcome-derived columns in model features; run unobserved-value and shuffled-label canaries on the training matrix; verify patient IDs are disjoint across cohorts; verify all y values are binary or missing; verify weights are finite/non-negative, censored labels have zero weight, and every fit has both classes. Abort on any failure or degenerate IPCW metric; do not substitute a default score.

## Stopping and deviations

Abort rather than modify the grid after inspecting validation or test results. If a family cannot fit, report it as failed with the actual error and do not select a replacement. If metrics are undefined due to no weighted cases or controls, report them as undefined and do not change the cohort seeds or horizon. Any code/config/metric change after results exist requires a new experiment ID and a new pre-registration.

## Scope limits

This single G1 study does not establish transport across G2/G3, sites, laboratories, or real cohorts. It does not correct partial verification bias. It is not a substitute for the registered S1/S3/S9 studies or for Phase 9 validation. Prior exposed seeds and prior invalid result files are not used for tuning.
