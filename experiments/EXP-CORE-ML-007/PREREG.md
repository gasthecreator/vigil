# EXP-CORE-ML-007: Corrected-feature cross-generator baseline re-evaluation

## Status

This is a new, independently seeded study. EXP-CORE-ML-003/004 outputs are preserved as historical results and are not reused, relabeled, or accessed by this run. The study runs after source commit `d7d4660` and the runner commit, with all model selection restricted to training, calibration, and validation cohorts. Its purpose is to measure the effect of the corrected shared feature/data contract on the registered synthetic baseline comparison; it does not establish clinical performance or an optimum for real patients.

This preregistration is committed before the runner is written against or reads any cohort from the frozen test seeds. EXP-CORE-ML-003 remains the separate single-G1 tuning study; its test data and results are not reused here.

## Question and estimand

Do B3 (regularized logistic horizon classifier) and B4 (XGBoost horizon classifier), trained on synthetic G1 and G2 data, retain discrimination and calibration on an independently generated G3 cohort with heavy-tailed noise and inter-laboratory shifts? G1 and G2 test cohorts are retained as in-generator comparators. The estimand is performance for observed simulator recurrence within 365 days among determinable landmark rows, with IPCW correction for early censoring and equal total fit weight per determinable patient. This does not estimate latent biological recurrence under partial verification.

## Data, cohorts, and splits

- Synthetic profile: `packages/vigil-sim/vigil_sim/config/synthetic_population_v1.json`, profile `balanced_synthetic_v1`. This profile is a stress-test assumption, not a population estimate. The current simulator implementation includes Q-7 corrections; the profile file itself is hash-checked by the runner.
- Generators: G1 smooth kinetics and G2 shedding bursts for training, calibration, and validation; G1, G2, and structurally distinct G3 heavy-tailed noise/inter-laboratory shifts for test.
- Each split/generator/replicate cohort has 1,000 patients and 730 days of follow-up. Use five independent replicates (`replicate ∈ {0,1,2,3,4}`). Patient identifiers include split, generator, and replicate namespaces; all splits must be disjoint.
- Deterministic seed formula: `54_000 + split_offset + generator_offset + replicate`, with split offsets train=100, calibration=200, validation=300, test=400; generator offsets G1=10, G2=20, G3=30. G3 is generated only for the test split. These non-overlapping offsets ensure every split/generator/replicate tuple has a unique seed.
- Prediction horizon: 365 days. Early censoring remains unknown; a competing event before the horizon is a known non-recurrence under the registered observed-event estimand.
- Training and validation use the pooled G1+G2 cohorts. Fit weights are estimated within their own split and normalize each determinable patient's total contribution equally. No patient, seed, or generated cohort is shared across splits.

## Candidate models and selection

- B3 uses the same implementation and candidate `C ∈ {0.05, 0.5, 5.0}` as EXP-CORE-ML-003.
- B4 uses the same implementation and grid as EXP-CORE-ML-003: `max_depth ∈ {2,3}`, `n_estimators ∈ {50,150}`, and `learning_rate ∈ {0.03,0.05}`; `n_jobs=1`, binary logistic objective, and fixed model seed 54001.
- Select one candidate per family by the lowest pooled, uncalibrated validation IPCW Brier score across the five G1 and five G2 validation cohorts. Scores within `1e-12` tie-break lexicographically by parameter ID. Do not use test metrics to change the grid, features, or configuration.
- After selection, fit one weighted Platt calibrator per model on the separate pooled G1+G2 calibration cohorts. Evaluate calibrated predictions once on each frozen G1/G2/G3 test cohort.
- Comparators: B0 prevalence, B1 registry-based CA 15-3 threshold, and B2 velocity rule, all fitted/initialized without test outcomes. They are comparators, not clinical guidance.

## Metrics and uncertainty

- Primary transport metric: calibrated IPCW Brier score on pooled G3 test patients.
- Secondary metrics on each test generator: IPCW time-dependent AUC, IPCW Brier score, IPCW calibration error, and IPCW-weighted average precision. Report all five replicate cohort results and pooled estimates; do not suppress a poor generator or undefined metric.
- Compare each learned model with B0, B1, and B2 using paired patient-cluster percentile bootstrap intervals (1,000 resamples, seed 54500), resampling patients within each replicate and keeping all their landmarks together. At least 400 valid replicates are required for every reported interval. A comparison with an undefined estimand is reported as undefined, never replaced by a numeric default.
- This is an exploratory robustness study. No model passes a clinical or deployment gate by winning on any synthetic generator. A result that degrades on G3 is a negative transport result.

## Integrity checks and frozen-test access

- Before fitting, verify label validity, zero fit weight for unknown outcomes, finite nonnegative weights, disjoint patient IDs, absence of outcome-derived columns, preservation of unobserved values as missing, and shuffled-label canaries for B0–B4 on the exact pooled training features. All canaries must meet the existing preregistered ≤0.60 AUC rule.
- Run a frozen-test clean-checkout SHA guard. Log one-time access for the G1, G2, and G3 test cohorts at the same committed code SHA. The script writes `results.json` and renders `REPORT.md` from that JSON; manual edits to results are prohibited.
- If a preregistered integrity check or metric-domain precondition fails, abort and record the failure without changing the protocol or accessing a replacement test cohort. Any corrected study uses a new experiment ID, preregistration commit, and seeds.

## Limits

All cohorts are synthetic and inherit the simulator's assumptions, including event ascertainment and population profiles. This experiment cannot establish clinical performance, site-level transport to real hospitals, usefulness of biomarkers in asymptomatic follow-up, or an optimal clinical model. It evaluates only the listed classical baselines and does not validate K1 or a Bayesian joint longitudinal-survival model.

## Changed feature contract under evaluation

The implementation SHA includes the ADR-0039 corrections: the 90-day slope window matches its name; acceleration is normalized for irregular visit spacing; zero-mean CV is unavailable; zero time from landmark to censoring is preserved; missing/contradictory outcomes, unknown patient references, duplicate days, invalid dates, and observation/follow-up boundary violations fail closed; configured competing events beyond administrative follow-up are censored. Predictive landmarks exclude observations at/after confirmed recurrence and terminal competing events. The simulator's bounded post-diagnosis transition visits are not treated as predictive observations.

The test cohorts are newly generated from the registered seeds and are read once only after the clean implementation commit is frozen. The runner must retain its access log at that commit and must refuse prior output/access artifacts. Do not compare winner status or performance against old outputs as if the feature/data sources were identical; report prior results only as historical context.
