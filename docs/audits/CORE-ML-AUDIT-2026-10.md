# Core ML and Engine Audit — 2026-10

## Scope and method

This audit follows `AGENTS.md`, the complete `docs/MASTER_PLAN.md`, `docs/ML_PROGRAM.md`, `docs/PROGRESS.md`, `docs/EVIDENCE.md`, and the phase prompts in `docs/prompts/` (P0/P1 through P16, including P3A, P3A2, P3A3 and P3B). It traces requirements to source, generated results and reports. It does not tune a model or reuse any prior evaluation cohort.

The audit scope is the product engine: simulator exports and labels, landmark features, K1/K3 inference, baselines, benchmark design, and the model/experiment record. Synthetic evidence remains synthetic. This is a code and artifact audit; it does not validate clinical utility.

## Executive finding

**The recorded ML performance and K1 validation claims are not reliable enough to guide model selection.** The central issues are not insufficient model complexity. The current benchmark can mislabel censored follow-up, the K1 experiment inputs are boolean measurement masks rather than biomarker values, the K1 risk calculation is not a recurrence-horizon probability, and the K1 card reports results and capabilities that conflict with source and committed JSON. K3 is also not the Bayesian joint longitudinal-survival model its name and phase reports claim. Fixing these defects comes before architecture search or hyperparameter optimization.

No clinical model should be selected, promoted, or described as validated using the affected results. Project maturity remains L0 as recorded in the ledger.

## Confirmed findings

### Critical: horizon labels treat incomplete follow-up as a negative

`WindowedFeatureExtractor.transform_cohort` sets `y=0` whenever no recurrence is observed within the requested horizon. For non-event patients it separately computes follow-up/censoring time, but does not mark the binary label as unknown when that time is shorter than `horizon_days`. Thus a patient observed for less than 365 days can enter the 365-day classifier target as a non-event. The returned time/event arrays do not undo this when `y` is passed to ordinary classifiers, calibration curves or Brier calculations.

**Evidence:** `packages/vigil-ml/vigil_ml/features.py`, `transform_cohort`, label construction. `scripts/run_benchmarks.py::run_study_s1` fits B3/B4 from `y_train_full`; it also calculates calibration from `y_test`.

**Consequence:** estimates can be biased and model ranking can change. Correct survival estimators may account for censoring, but binary classifier training and ordinary calibration do not automatically do so. The current S1 results need to be treated as invalid until the target construction and evaluation population are repaired and the study is rerun under a new preregistration.

### Critical: all three K1 “optimization” studies consume the measurement mask

`CohortDataset.to_observations_dataframe` writes `observed_ca_15_3` as a boolean measured/not-measured flag; the numeric lab value is `ca_15_3`, and unmeasured numeric values are NaN. Each `experiments/EXP-K1-00{1,2,3}/run.py` filters with `dropna(subset=["observed_ca_15_3"])` and passes that boolean column as the numeric CA153 series. Because the mask itself is non-null for measured and unmeasured rows, the filter does not perform the claimed missing-value selection.

The interventions do not implement their preregistered model changes either: EXP-K1-001 clips posterior doubling-time samples after inference; EXP-K1-002 scales risk after inference by an interval factor; EXP-K1-003 applies a fixed `500` burden-score transform. None changes the registered prior, observation likelihood, or inference procedure as described. The use of `true_recurrence_event` also differs from the clinical observed-event label described in the broader evaluation program.

**Committed outputs:** all three JSON files record N=249 and 87 events, but source construction uses the mask as marker values. Their AUC deltas have CIs including zero and `hypothesis_confirmed: false`. The experiment reports and K1 card say otherwise in places. These runs cannot count as the three serious attempts required by §13 and must not support a model-elimination decision.

**Evidence:** `packages/vigil-sim/vigil_sim/generators.py::CohortDataset.to_observations_dataframe`; each `experiments/EXP-K1-001/run.py`, `...002/run.py`, `...003/run.py`; corresponding `results.json` and `REPORT.md`.

### Critical: K1 risk is not the advertised recurrence probability

`vigil_ml.k1.risk_from_posterior` derives an exponential burden from doubling time and onset, then applies a logistic transform around `detection_threshold` (default `1.0`). It does not use recurrence event likelihood, a competing-risk process, or a horizon-specific event-time distribution. `HybridKineticModelK1.fit` selects this threshold with Youden's J on the same supplied labels and biomarker values; this is outcome-supervised threshold fitting, not posterior calibration. The `return_ci` result bootstraps only 10 subsets of 50 posterior draws and returns the 5th/95th percentile of those Monte Carlo means; these are neither patient-level uncertainty intervals nor a well-estimated posterior credible interval.

The source therefore contradicts the model card's stated risk formula, “zero label head” implication that risk is exclusively mechanistic, calibration claim, and claimed credible intervals. This route is research code and must not be called a recurrence probability until its event model and uncertainty semantics are implemented and independently tested.

**Evidence:** `packages/vigil-ml/vigil_ml/k1.py::risk_from_posterior`, `HybridKineticModelK1.fit`, `predict_risk`; `docs/models/MODEL-CARD-K1.md` §§3–4.

### Critical: two incompatible K1 classes are publicly exposed

`vigil_ml.__init__` exports `HybridKineticModelK1` from `vigil_ml.kinetic_k1`, while the current route and S1 script import the distinct class from `vigil_ml.k1`. The exported legacy implementation contains a direct supervised risk head and fixed blend/threshold formulas (see `packages/vigil-ml/vigil_ml/kinetic_k1.py` and `VERDICT-P3A.md`). This violates the P3A3 requirement to remove the direct label head and leaves the invalid implementation reachable through the package's normal public API.

**Consequence:** code using the documented package-level import can run a different model than the benchmark and current K1 contract. Package identity, model registry and served inference path must be made unambiguous before promotion.

### Critical: K1 route and training claims exceed implementation

The current K1 amortized route interpolates irregular observations onto the fixed `SCHEDULE` with endpoint extrapolation (`np.interp`), despite P3A3 requiring direct irregular schedule handling. `train_amortized` trains on the private four-parameter toy simulator and returns an in-memory model, but `_get_or_load_amortized_model` loads committed weights; the reproducible artifact lineage and training configuration must be verified end to end before calling the deployed weights reproducible. The route's posterior spread is built from residual SD constants/calibration JSON, not a learned posterior distribution. NPE retrains at import/use from a fixed toy simulator and fixed training settings. The particle filter is not an unscented Kalman filter despite the `ukf` route name. These distinctions matter; the acceptance tests establish behavior only for their specified toy world and sampled checks, not the broad scientific claims in the card.

**Evidence:** `packages/vigil-ml/vigil_ml/k1.py` (`SCHEDULE`, `_route_amortized`, `train_amortized`, `CALIBRATED_RESIDUAL_SD`, `_get_or_load_npe_posterior`, `_route_ukf`); `docs/prompts/PROMPT-P3A3.md`; `docs/ml/K1-CONTRACT.md`.

### Critical: K3 is not a Bayesian joint longitudinal-survival model

`BayesianJointModelK3.fit` uses landmark rows as observations, fits a Gaussian marker trend, then samples only trend coefficients and a hand-written scalar association likelihood. It has no patient-specific random effects in the likelihood, uses the binary horizon label as event indicator in the benchmark call, and does not use a valid time-to-event likelihood with censoring. The survival expression omits a fitted baseline hazard process and does not integrate the longitudinal trajectory over time. The “R-hat” is a basic variance ratio with no modern split-chain corrections; the “ESS” uses a clipped lag-1 approximation from only the first chain. `FastLandmarkJointModel` is also a separate approximation and should not inherit the Bayesian claim.

**Evidence:** `packages/vigil-ml/vigil_ml/joint_model.py::BayesianJointModelK3.fit`, `_sample_chain`, `_compute_convergence_diagnostics`; `scripts/run_benchmarks.py::run_study_s1`; `docs/prompts/PROMPT-P2.md` and `PROMPT-P3A.md`.

### High: the “5% alert rate” is estimated on the test predictions

S1 computes `alert_thresh = percentile(preds, 95)` from the same test predictions whose lead time it reports. This is a test-set retrospective alert burden, not an operating threshold selected on a calibration/development set and evaluated on untouched patients. It can be reported as a descriptive within-cohort quantile only, and the label must say so. The PREREG and headline framing currently imply a fixed deployable alert rate.

**Evidence:** `scripts/run_benchmarks.py::run_study_s1`, lead-time block.

### High: S1's nominal held-out test is not an independent generator test

The train and test cohorts are distinct cohorts from the same G1 generator instance and seed stream. This avoids within-patient overlap, but does not test generator/site shift. The benchmark headline is therefore limited to one synthetic world. The full prompt calls for cross-generator robustness and S9; those results must be separately checked and cannot be inferred from S1.

### High: fixed values are not all defects, but many are unsupported assumptions

The core contains many meaningful fixed values: K1 prior bounds, baseline `18.0`, noise `1.5`, seven-point visit schedule, calibration residual widths and prior blending; K3 prior centers/variances, alpha range, hazard constants, chain counts; and S1 threshold `0.15`, bootstrap count `100`, seed `42`, 365-day horizon. Some may be preregistered synthetic-world settings; others are defaults or convenience fallbacks. The defect is that model cards and code do not consistently identify their source, units, calibration split, intended range, or sensitivity. In particular, the K1 constants cannot be described as physiological or calibrated merely because they are named that way. E9 and the Evidence register do not establish the full K1 model's assumptions.

### High: baseline feature handling silently substitutes values

`WindowedFeatureExtractor` uses hard-coded defaults for missing demographics, marks missing labs with a zero value plus an indicator, and drops some stage/subtype categories into all-zero indicators. B3/B4 then `fillna(0.0)`; B1/B2 replace missing required columns with zeros. These choices can encode missingness or unknown categories as real values and need explicit training-only preprocessing, schema validation and missingness tests. The current transforms are not a robust production feature contract.

### High: features and labels are built on every visit, with dependence and leakage risks

The extractor emits one row per eligible visit, while standard baselines treat rows as independent examples. The patient-cluster bootstrap addresses uncertainty in some metrics, but does not correct row-weighted training, repeated-patient calibration, or validation splits that are not grouped. Future history is correctly filtered inside `extract_features_at_visit`, but label construction and censoring remain as above. Any new development/validation/test split must happen by patient before landmarks are materialized or must group all rows by patient.

### Medium: metric and report generation are not fully aligned with the plan

S1 uses 100 bootstrap replications, while the plan calls for larger repeated patient-level uncertainty analysis; calibration uses ordinary binary labels, and one decision-curve threshold is hard-coded. Report narrative contains typed “CONFIRMED” hypotheses (visible in `render_s1_markdown`) rather than deriving verdicts from registered criteria and result artifacts. `run_benchmarks.py` also runs S3/S9 alongside S1, so the entrypoint, preregistration, and outputs need an explicit reproducibility map and per-study isolation.

## Corrections applied to the record

1. The three EXP-K1 runs are retracted as invalid evidence; their historical JSON is preserved. Do not edit those JSONs or rerun those seeds as a repair.
2. K1 is research-only as previously decided, but the claim that its routes and recurrence-risk inference are scientifically validated is withdrawn. Acceptance-suite passes do not establish clinical risk validity.
3. S1 benchmark performance claims are provisional/retracted pending correction of censored binary targets, operating-point selection and generated-report logic. Do not use the recorded K1/K3/B4 ranking to justify deployment or further tuning.
4. No model is “optimized” by this audit. Model optimization must follow corrected data/label semantics, a development/calibration/test split by patient, frozen evaluation seeds and a new preregistration. Existing reported cohorts are not tuning data.

### Additional package-B finding (Q-7, identified 2026-10-19)


The existing synthetic profile also sampled analyzer offsets/scales independently per patient, despite identifying them as facility effects; imaging exports lacked a result and the verification mechanism had deterministic threshold sensitivity and perfect specificity. Added `synthetic_population_k3_v2.json` as a separately versioned study profile: seeded analyte shifts are shared per facility; treatment exposure and imaging result (positive, negative or unobserved) are exported; imaging sensitivity/specificity, visibility, routine propensity, symptom/marker propensity, and assay-missingness assumptions are explicit config. A positive imaging result updates the synthetic confirmed-diagnosis endpoint only when recurrence is visible under the configured burden threshold; positive screening findings below visibility do not become confirmed diagnoses. Historical profiles keep their former generator semantics. Tests verify same-facility effect identity, observed/unobserved result semantics, both imaging result classes, propensity bounds, missingness assumptions, seeded deterministic generation, recurrence-config validation, and separation of positive screening from confirmed diagnosis. Across the simulator, feature-contract, evaluation-canary and metric tests: 51 passed; Ruff and `git diff --check` passed. A test review caught and fixed an unreachable recurrence-config validator caused by helper placement before these results were recorded. EXP-CORE-ML-005 preregisters a synthetic observation-process audit; no cohort from its design has been generated yet.

### Additional package-B finding: oracle labels ignored loss to follow-up (2026-10-19)

`CohortDataset.get_survival_training_examples(use_observed_labels=False)` could label a latent recurrence after loss to follow-up as observed, because it selected the latent event day without comparing it with the censoring time. This contaminated the documented oracle-only path and could make simulator checks overstate what is learnable. The event selection now accepts recurrence only when it occurs on or before the observation end; a regression test sets loss at day 10 and latent recurrence at day 100 and asserts censored/unknown at a 180-day horizon. The focused simulator and feature-contract suite passed (15 tests); Ruff and `git diff --check` passed. This does not complete package B: every historical study and production/serving path still needs its source-contract classification and affected outputs need reconciliation.

## Work order to maximize valid model output

1. Correct the target contract: define event, competing event, censoring, horizon, landmark eligibility, and label observability. Make invalid binary labels impossible to pass silently to classifier fitting and calibration.
2. Build a single patient-grouped study harness with distinct train, development/calibration and frozen test patients; report cross-generator and cross-site stress results separately. Select thresholds and calibration only on development/calibration data.
3. Fix cohort-to-feature schema: observed numeric values only, no latent columns or boolean masks as measurements; train-only imputation/scaling/encoding; enforce feature whitelist and leakage canaries on the exact model input.
4. Retire or rename the legacy K1 public export. Keep exactly one canonical API and make all model IDs resolve to the implementation actually benchmarked.
5. Either rebuild K1 as a properly specified event-time posterior model on the simulator's actual data-generating process, or restrict it to parameter recovery research and remove all recurrence-risk claims. Do not attempt another score transform.
6. Reimplement K3 with a valid censored time-to-event likelihood and patient-level longitudinal structure using a maintained Bayesian sampler, or rename and describe the current model as a synthetic heuristic. Derive diagnostics from the chosen sampler.
7. After the data and evaluation contract is fixed, optimize the strongest honest baseline (likely B4 or a simple survival model) on development data with nested/grouped selection. Freeze the model before untouched evaluation, then compare calibration, utility, lead time at calibrated alert burden, subgroup behavior and cross-generator robustness.
8. Add a reproducibility command that regenerates every model result and report from committed preregistrations, records code/config/data hashes and fails on prose/result mismatches.

## Prompt/plan trace summary

The original P0/P1 and P3 prompts explicitly required removal of circular labels, clean observation exports, censored event horizons, patient splits, leakage canaries, independent generators, calibrated thresholds, and experiment provenance. P3A2/A3 introduced independent behavioral tests after earlier hand-built posteriors, test-seed tuning, fake observations and unreproducible weights were found. P3B and P15 repeated the rules against test-seed tuning, stand-ins and silent post-preregistration changes. Later P5–P14 prompts document recurring incidents: hard-coded or typed results, invalid/stale studies, test-only backdoors, invented data, and self-grading. The present findings show those rules were recorded but not consistently enforced across the full engine. P16's current scope is platform/product gap work; it does not close these underlying scientific issues.

## Verification limits

This audit did not rerun model studies or acceptance tests. Re-running affected seeds would not repair invalid study design and risks treating seen evaluation outcomes as tuning feedback. The numerical outputs cited above are read from committed source and JSON files; no new performance estimates were generated. The audit does not establish clinical validity or real-world transportability.

The repository's `python3 scripts/reality_audit.py --require-stub-registry` currently reports “no hard-coded results, no-op fits, toy validations or phantom classes found,” despite the concrete examples documented above. Treat that pass as evidence that the static audit has a coverage gap, not as evidence that these issues are absent. The checker needs seeded failure cases for these patterns before it can serve as a gate for scientific validity.
