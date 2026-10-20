# Core ML and Engine Audit — 2026-10

## Scope and method

This audit follows `AGENTS.md`, the complete `docs/MASTER_PLAN.md`, `docs/ML_PROGRAM.md`, `docs/PROGRESS.md`, `docs/EVIDENCE.md`, and the phase prompts in `docs/prompts/` (P0/P1 through P16, including P3A, P3A2, P3A3 and P3B). It traces requirements to source, generated results and reports. It does not tune a model or reuse any prior evaluation cohort.

The audit scope is the product engine: simulator exports and labels, landmark features, K1/K3 inference, baselines, benchmark design, and the model/experiment record. Synthetic evidence remains synthetic. This is a code and artifact audit; it does not validate clinical utility.

> **Source-state note (2026-10-19):** The first findings below were confirmed against repository states before Q-7 repairs. Resolved source defects are labeled as historical; their old outputs remain stale or retracted. Current source status is maintained in [`CORE-ML-ENTRYPOINT-CROSSWALK-2026-10.md`](CORE-ML-ENTRYPOINT-CROSSWALK-2026-10.md) and [`CORE-ML-PROMPT-TRACE-2026-10.md`](CORE-ML-PROMPT-TRACE-2026-10.md).

## Executive finding

**The recorded ML performance and K1 validation claims are not reliable enough to guide model selection.** Historical benchmark outputs used an invalid censored-label contract and K1 experiments used boolean measurement masks rather than biomarker values. Q-7 corrected the label/export paths, but these source changes make prior comparisons stale and require a fresh registered evaluation. K1 recurrence-risk output now fails closed because its event definition does not match the product estimand. K3 is not the Bayesian joint longitudinal-survival model its name and earlier reports claim. No model-selection or clinical-performance claim follows from these source repairs.

No clinical model should be selected, promoted, or described as validated using the affected results. Project maturity remains L0 as recorded in the ledger.

## Confirmed findings

### Historical critical finding (Q-7 source fix): horizon labels treated incomplete follow-up as a negative

`WindowedFeatureExtractor.transform_cohort` sets `y=0` whenever no recurrence is observed within the requested horizon. For non-event patients it separately computes follow-up/censoring time, but does not mark the binary label as unknown when that time is shorter than `horizon_days`. Thus a patient observed for less than 365 days can enter the 365-day classifier target as a non-event. The returned time/event arrays do not undo this when `y` is passed to ordinary classifiers, calibration curves or Brier calculations.

**Historical evidence:** the pre-Q-7 `packages/vigil-ml/vigil_ml/features.py::transform_cohort` and old S1 runner. **Current disposition:** Q-7 marks early-censored labels unknown, requires explicit observed outcome metadata, preserves zero follow-up, validates event/day boundaries, and adds regression cases in `packages/vigil-ml/tests/test_features.py`. Historical S1 and prior EXP-CORE-ML results remain stale; corrected labels and features require a new preregistered evaluation.

**Consequence:** estimates can be biased and model ranking can change. Correct survival estimators may account for censoring, but binary classifier training and ordinary calibration do not automatically do so. The current S1 results need to be treated as invalid until the target construction and evaluation population are repaired and the study is rerun under a new preregistration.

### Critical: all three K1 “optimization” studies consume the measurement mask

`CohortDataset.to_observations_dataframe` writes `observed_ca_15_3` as a boolean measured/not-measured flag; the numeric lab value is `ca_15_3`, and unmeasured numeric values are NaN. Each `experiments/EXP-K1-00{1,2,3}/run.py` filters with `dropna(subset=["observed_ca_15_3"])` and passes that boolean column as the numeric CA153 series. Because the mask itself is non-null for measured and unmeasured rows, the filter does not perform the claimed missing-value selection.

The interventions do not implement their preregistered model changes either: EXP-K1-001 clips posterior doubling-time samples after inference; EXP-K1-002 scales risk after inference by an interval factor; EXP-K1-003 applies a fixed `500` burden-score transform. None changes the registered prior, observation likelihood, or inference procedure as described. The use of `true_recurrence_event` also differs from the clinical observed-event label described in the broader evaluation program.

**Committed outputs:** all three JSON files record N=249 and 87 events, but source construction uses the mask as marker values. Their AUC deltas have CIs including zero and `hypothesis_confirmed: false`. The experiment reports and K1 card say otherwise in places. These runs cannot count as the three serious attempts required by §13 and must not support a model-elimination decision.

**Evidence:** `packages/vigil-sim/vigil_sim/generators.py::CohortDataset.to_observations_dataframe`; each `experiments/EXP-K1-001/run.py`, `...002/run.py`, `...003/run.py`; corresponding `results.json` and `REPORT.md`.

### Historical critical finding (risk route now fails closed): K1 did not estimate the advertised recurrence probability

`vigil_ml.k1.risk_from_posterior` derives an exponential burden from doubling time and onset, then applies a logistic transform around `detection_threshold` (default `1.0`). It does not use recurrence event likelihood, a competing-risk process, or a horizon-specific event-time distribution. `HybridKineticModelK1.fit` selects this threshold with Youden's J on the same supplied labels and biomarker values; this is outcome-supervised threshold fitting, not posterior calibration. The `return_ci` result bootstraps only 10 subsets of 50 posterior draws and returns the 5th/95th percentile of those Monte Carlo means; these are neither patient-level uncertainty intervals nor a well-estimated posterior credible interval.

That earlier source contradicted the card's risk formula and credible-interval claims. The current `HybridKineticModelK1.predict_risk` raises; `risk_from_posterior` is explicitly a synthetic one-doubling event, not clinical recurrence. This closes the unsafe output path, not the event-model work. K1 remains research-only and does not provide a recurrence probability.

**Evidence:** `packages/vigil-ml/vigil_ml/k1.py::risk_from_posterior`, `HybridKineticModelK1.fit`, `predict_risk`; `docs/models/MODEL-CARD-K1.md` §§3–4.

### Historical critical finding (public K1 identity consolidated)

The earlier package API exposed a legacy implementation distinct from `vigil_ml.k1`, including a direct supervised risk head. Current `vigil_ml.__init__` imports `HybridKineticModelK1` from `vigil_ml.k1`, and `vigil_ml.kinetic_k1` is now a deprecated import shim re-exporting that same class. The duplicate implementation is no longer exposed. The compatibility module remains intentionally importable, so its deprecation and identity need to remain tested; recurrence risk remains disabled.

**Current disposition:** package identity is consolidated in source; this does not close K1 scientific validity, route fidelity, or artifact lineage.

### Critical: K1 route and training claims exceed implementation

Current K1 uses four explicit routes, but `ukf` is only a compatibility key for a sequential particle filter, not an unscented Kalman filter. The amortized and NPE routes bin observations against a fixed configured reference schedule; they do not use the former irregular-grid endpoint interpolation asserted in the historical version of this audit. Their training routines generate a private one-marker synthetic simulator, not the product `vigil-sim`; deployed inference loads safetensors artifacts, while training returns in-memory models and a separate script writes artifacts. Reproducible artifact lineage and exact training config still require end-to-end verification. Posterior spread comes from learned conditional outputs, but no calibration/coverage evidence supports patient-level credible-interval claims. The four parameters remain synthetic research assumptions, and the fixed schedule/binning makes visit timing and out-of-range behavior a route-parity concern. Acceptance tests establish only their specified toy-world behavior, not the broader scientific claims in the card.

**Evidence:** `packages/vigil-ml/vigil_ml/k1.py` (`SCHEDULE`, `_summarize_observations`, `train_amortized`, `train_npe`, `_route_ukf`, route registry and `predict_risk`); `kinetic_k1.py` compatibility shim; `docs/prompts/PROMPT-P3A3.md`; `docs/ml/K1-CONTRACT.md`.

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


The existing synthetic profile also sampled analyzer offsets/scales independently per patient, despite identifying them as facility effects; imaging exports lacked a result and the verification mechanism had deterministic threshold sensitivity and perfect specificity. Added `synthetic_population_k3_v2.json` as a separately versioned study profile: seeded analyte shifts are shared per facility; treatment exposure and imaging result (positive, negative or unobserved) are exported; imaging sensitivity/specificity, visibility, routine propensity, symptom/marker propensity, and assay-missingness assumptions are explicit config. A positive imaging result updates the synthetic confirmed-diagnosis endpoint only when recurrence is visible under the configured burden threshold; positive screening findings below visibility do not become confirmed diagnoses. Historical profiles keep their former generator semantics. Tests verify same-facility effect identity, observed/unobserved result semantics, both imaging result classes, propensity bounds, missingness assumptions, seeded deterministic generation, recurrence-config validation, and separation of positive screening from confirmed diagnosis. Across the simulator, feature-contract, evaluation-canary and metric tests: 51 passed; Ruff and `git diff --check` passed. A test review caught and fixed an unreachable recurrence-config validator caused by helper placement before these results were recorded. EXP-CORE-ML-005 completed once for the exact source SHA `ce897a1`; its synthetic propensities and test results were mostly near configured values, while 4 of 30 decile point estimates were just outside unadjusted Wilson intervals. Those intervals are descriptive, not a multiple-comparison or patient-cluster analysis. Its result is preserved as a source-specific audit.

### Additional package-B finding: oracle labels ignored loss to follow-up (2026-10-19)


EXP-CORE-ML-005 ran once from `ce897a1` after preregistration. Across three generators and five seeds, configured per-visit imaging propensity, result sensitivity/specificity, assay missingness, and shared facility effects were checked; per-facility effects had zero within-facility inconsistencies. Four of 30 propensity decile point estimates fell just outside their unadjusted Wilson intervals; no pass/fail threshold was registered, and no formal correction for repeated cells or patient clustering was used. These are implementation checks only. A further source audit found generated visits continued after a diagnosis first occurred during the longitudinal loop: the schedule was filtered before confirmation, not as confirmation happened. The source is now fixed to stop after the configured 90-day transition window. EXP-CORE-ML-005 remains immutable evidence for `ce897a1`, not this corrected source. EXP-CORE-ML-006 was preregistered independently and completed on the corrected source; it recorded zero post-diagnosis-window and post-competing-event observations across 30,000 synthetic patients, with zero facility-effect inconsistencies. These results do not validate clinical follow-up patterns or test characteristics. A regression test also forces a confirmed diagnosis and checks no later observation exceeds the 90-day transition window.

This does not complete package B: every historical study and production/serving path still needs its source-contract classification and affected outputs need reconciliation.

### Package-G correction: legacy S3 and aggregate benchmark are retracted

The S3 source review confirmed the legacy findings listed in `reports/ml/S3_VERIFICATION_BIAS/RETRACTION.md`. Its generated report claimed IPW as the default evaluation harness despite using lifetime recurrence, setting all unverified patients negative, reducing verification to ever-imaged, and reporting a hand-set sigmoid score. The one executed cohort did not match the registered ten-replication design. The historical preregistration, result JSON and report are preserved unchanged; a sidecar and the aggregate report's leading retraction notice make the status visible. The legacy aggregate script now stops before frozen-data access or output writes, and a regression test asserts historical files remain byte-identical on attempted execution. The K3 model card is marked retracted at its front door. This closes only the specific S3/aggregate rerun hazard; full S1/S9/card/result reconciliation remains open.

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

Every prompt P0/P1 through P16 (including P3A, P3A2, P3A3 and P3B) has now been read and mapped in [`CORE-ML-PROMPT-TRACE-2026-10.md`](CORE-ML-PROMPT-TRACE-2026-10.md). That crosswalk distinguishes prompt assignments from current evidence and records the repeated failures: typed or hard-coded outputs, invalid target semantics, leakage, test contamination, proxy implementations, stale claims, and product routes that outlive quarantine. P16's engineering/product work does not close these scientific issues.

### Additional package-H finding: ONNX runtime invented a model and uncertainty

The runtime previously exported a fresh randomly initialized `SurrogateInferenceNet` to a shared `/tmp` path whenever no model path was supplied, then passed a literal epistemic SD of `0.04` to K8. The K8 controller happened to abstain because it had no calibration cohort, but the default still fabricated model weights and uncertainty inputs behind a production-sounding API. The runtime now requires an existing explicit artifact and explicit uncertainty, validates input shape/finiteness, rejects latency sample counts below 1,000, and leaves the default controller uncalibrated (abstention). Focused verification: `packages/vigil-ml/tests/test_phase3_models.py` — 11 passed; Ruff and `git diff --check` passed. The latency test measures only ONNX CPU execution on an explicitly exported untrained network; it excludes preprocessing, uncertainty, calibration, API overhead and model performance. ADR-0037 records the compatibility boundary. Artifact provenance, uncertainty validity, model calibration and a supported risk route remain open.

### Additional package-F finding: K8 card included unproduced metrics

`docs/models/MODEL-CARD-K8.md` presented exact FNR/FPR, OOD and ACI measurements and asserted the default ACI step size came from a regret-bound derivation. No committed result-producing artifact or derivation was found for those statements. The numerical table and unsupported derivation were removed. Input validation now rejects invalid alpha, malformed/non-finite calibration data, a no-positive CRC calibration cohort, and use before fitting; OOD and ACI inputs/parameters are checked as well. `packages/vigil-ml/tests/test_k8_input_contract.py` passed 7 tests, the unchanged K8 contract passed 4 tests, and Ruff passed after import cleanup. This does not add a patient-level or clinical guarantee; those remain open under S-007.

## Verification limits

Q-7 package B added two preregistered synthetic process audits (EXP-CORE-ML-005/006), not model-performance studies. The feature-contract regression set across features, evaluation metrics/leakage, and simulator generator/surveillance passes 57 tests; the partner-analysis suite passes 23 tests after the adapter was updated for the strict censor/event contract. The focused baseline gate command reports 28 passed and two unchanged fixed-AUC failures (`test_gbm_reaches_at_least_single_threshold_auc` and `test_k3_joint_model_distinct_from_single_threshold`); the shared proposal remains pending overseer review. The earlier K3 shuffled-outcome canary also remains unresolved under `PROP-K3-SHUFFLED-OUTCOME-CANARY.md`. EXP-CORE-ML-007 is exploratory because its registered paired contrast set was incomplete; EXP-CORE-ML-008 completed its registered synthetic paired comparison, but does not meet C decision-curve, alert-burden, subgroup or runtime evidence requirements. The latest full repository suite is 909 passed, 18 skipped, 3 failed, and 0 errors. The failures are the two fixed AUC gates and the K3 shuffled-outcome canary; do not claim the full core suite is green. The M12 audit additionally found its frozen output lacks a canonical access-log entry and predates corrected early-censor labels; fail-closed guards now reject unknown training/calibration labels and empty cohorts. EXP-CORE-ML-005/006 estimates are synthetic mechanism diagnostics only and do not establish clinical validity or real-world transportability. Frozen model acceptance results remain untouched.

The repository's `python3 scripts/reality_audit.py --require-stub-registry` currently reports “no hard-coded results, no-op fits, toy validations or phantom classes found,” despite the concrete examples documented above. Treat that pass as evidence that the static audit has a coverage gap, not as evidence that these issues are absent. The checker needs seeded failure cases for these patterns before it can serve as a gate for scientific validity.
