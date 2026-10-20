# Analysis specification for the partner evaluation (operational definitions)

> **Status: DRAFT, NOT FROZEN.** This file states what `scripts/partner_analysis.py` and `scripts/run_partner_evaluation.py` do, so that the pre-registration (`PREREGISTRATION.md`) can be read together with the code that implements it. It is frozen with the pre-registration (the freeze record carries its SHA-256). Every sentence below describes the code; where the code and this text disagree, that is a defect to be reported, not resolved silently. Clinical and statistical review is pending (`docs/HANDOVER.md`).

## 1. Unit of analysis, index date and landmarks
- Population: the complete-case patients of the ingestion report (patient, baseline and outcome rows all accepted).
- Index date: `patients.index_day` (completion of primary treatment). Laboratory draws before it are discarded before any feature is built.
- Landmarks: every surveillance draw day from the **second** post-index draw day onward (so `history_length >= 2`, PREREG section 2). A patient with fewer than two post-index draws, or with a recurrence on or before the second draw, has no landmark and is counted as excluded.
- Landmarks at or after a recurrence, and at or after the last follow-up, are not created.
- First landmark: the earliest landmark of each patient. C1 and C2 use only first landmarks, so each patient contributes once; C3 uses all landmarks.

## 2. Outcome, time and censoring
- Event: `recurrence_confirmed` with `recurrence_day <= days_to_last_followup`.
- Time at a landmark `t`: `min(recurrence_day, days_to_last_followup) - t` (at least one day). Patients without an event are censored at the last follow-up.
- Death from another cause (`vital_status = DEAD_OTHER`) is treated as **censoring** (a cause-specific analysis). `PREREGISTRATION.md` section 2 asks for cumulative-incidence handling of this competing event; that is **not implemented**, and estimates that depend on the unobserved subsequent course (calibration, AUC) can be biased when death is common. This is an open deviation for the clinical statistician to rule on at ratification.
- The horizon outcome at a landmark is "event within 365 days". IPCW weights are those of `vigil_eval.metrics.compute_ipcw_weights` at 365 days.
- The feature extractor (`WindowedFeatureExtractor`) censors at the last laboratory day; the pipeline discards its time and event columns and recomputes them from the partner's follow-up as above.

## 3. Candidate, comparators and what "recalibrate" means here
- **Candidate:** `GradientBoostingBaseline` (B4) fitted **from scratch** on the development split (determinable landmarks only: event within 365 days, or followed beyond 365 days). `PREREGISTRATION.md` section 3 says "recalibrate, never retrain from scratch without an ADR". There is no clinically trained Vigil model to recalibrate: the model of `vigil_ml.runtime` is an untrained latency surrogate (`SurrogateInferenceNet`), and every performance number in this repository is synthetic. Fitting on the partner's development split is therefore the only available candidate; it is recorded as a deviation to be accepted or rejected at ratification, and is the subject of ADR-0021.
- **Comparator** (chosen on the development split among rule and hazard baselines): B1 single threshold (`SingleThresholdBaseline`), B2 velocity rule (`VelocityBaseline`), B3 regularised hazard (`RegularizedCoxHazardBaseline`). The one with the highest development IPCW AUC at first landmarks is chosen; B3's development AUC is out-of-fold.
- **Cross-fitting:** the development split is divided into five folds by patient (`GroupKFold`). Comparator selection, recalibration and the operating threshold use the out-of-fold predictions, so none of them is tuned on predictions the model made for its own training rows. The final candidate and B3 are then refitted on the whole development split.
- **Recalibration:** an IPCW-weighted logistic regression of the horizon outcome on `logit(p)` (unpenalised) fitted on the out-of-fold candidate predictions at first landmarks; `p_cal = sigmoid(a + b * logit(p))`.
- Model inputs are the extractor's features except `patient_id` and `eval_day`.

## 4. Operating point and alert burden
- An **alert** is counted at every landmark whose `p_cal` is at or above the threshold. Counting only the onset of an episode would let "alert always on" cost one alert per patient; it is not used.
- Months at risk per patient: from the first landmark to `min(recurrence_day, days_to_last_followup)`, in months of 30.4375 days. The rate is `100 * alerts / months at risk` over the patients concerned.
- The threshold is the smallest value on a 201-point quantile grid of the development `p_cal` whose development alert rate does not exceed PR-04.

## 5. Confirmatory tests (frozen test split, opened once)
- C1: IPCW-weighted calibration slope of `p_cal` at first landmarks. C2: IPCW time-dependent AUC of `p_cal` minus that of the comparator, paired. C3: alert rate at the development threshold.
- 95 % intervals are the 2.5th and 97.5th percentiles of 2000 patient-level bootstrap resamples with the frozen seed.
- One-sided bootstrap p-values: C1 `max(P(slope < PR-01), P(slope > PR-02))`; C2 `P(difference <= PR-03)`; C3 `P(rate > PR-04)`; each is floored at `1/(resamples + 1)`. Holm-Bonferroni is applied across the three at 0.05.
- **A hypothesis is reported as met only if the 95 % CI criterion of the pre-registration holds and the Holm-adjusted p-value is below 0.05.** C3 measures workload, not correctness.
- The test split is opened through `FrozenTestAccessLogger`; a second opening of the same dataset is refused unless `--acknowledge-deviation` is given, and is then reported as a protocol deviation.
- A step that cannot be done honestly (too few development events, a cross-fitting fold with one class, fewer than 20 test patients) ends the run with status `NOT RUN` and the reason, never with a number.

## 6. Secondary and descriptive analyses
Reported without a pass/fail claim: calibration before recalibration (ECE on determinable outcomes, IPCW calibration-in-the-large inputs); IPCW decision curve only at the explicitly ratified PR-10 threshold grid from the freeze record (never the evaluator's compatibility default); subgroups by age band (<50, 50-64, 65 and over), stage group and receptor subtype with IPCW AUC and bootstrap CI (500 resamples), "insufficient data" below PR-05 events and small counts shown as `<PR-06`; lead time and over-detection from `vigil_eval.lead_time` (relative to the confirming test; length bias and over-detection apply); the M10 count of dismissed prior signals with small-cell suppression; verification bias.
- **Verification bias** is run only when `restaging_imaging_done` is complete and binary in both development and test patients. Fit the logistic propensity model on the first landmark of development patients only; use age, current CA 15-3, and history length, with covariate medians fitted on development and a missingness indicator for each imputed field. Apply that transform/model to test patients and pass the resulting probabilities to `vigil_eval.verification_bias`; never fit the propensity on test verification status. If the development mask is incomplete/one-class, an input field is entirely missing in development, or test support is invalid, report "not run" with the reason. On determinable test rows, report complete-case and development-fit IPW at the development operating threshold, plus the sensitivity analysis over assumed event rates among unverified patients (0, 5, 10, 20 %). The sensitivity analysis varies an assumption; it is not an estimate. IPW population interpretation still requires conditional exchangeability, positivity, and a sufficiently specified/stable verification model; this implementation does not establish those assumptions.
- Not produced: facility subgroups (single-site extraction), cumulative-incidence estimates for the competing event (section 2).

## 7. What a synthetic dry run does and does not show
`scripts/run_partner_dry_run.py` runs this code on invented cohorts (`reports/clinical/dry_run/`). A cohort with a planted signal shows that the pipeline can find a signal that exists; a cohort without one shows that it does not invent one (candidate AUC near 0.5, C1 and C2 not met). Neither shows performance on real patients. Real-data runs are blocked by `scripts/check_prereg_freeze.py` until the pre-registration and this file are frozen.
