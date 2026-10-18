# Pre-registration of clinical validation (T-R retrospective and T-Q silent mode)

**Status: DRAFT, NOT FROZEN.** This document is committed before any real-data evaluation exists. It becomes binding only when `docs/clinical/PREREG-FREEZE.json` records its SHA-256 and carries a named ratification for every row of section 7 (the Status column of this file keeps reading PROPOSED; ratification lives in the freeze record so that this text is never edited after the freeze). `scripts/check_prereg_freeze.py` enforces that; the partner evaluation entry point (`scripts/run_partner_evaluation.py`, Tier 1) refuses to read real data while the check fails. Ratification of the numbers in section 7 is a **clinical and owner decision that the executor cannot make**: the values below are proposals with their rationale.

Governing text: `docs/MASTER_PLAN.md` section 18.3 and `docs/ML_PROGRAM.md` sections 4 and 5. Study protocol: `docs/clinical/PARTNERSHIP/STUDY-PROTOCOL.md`. Everything here is a plan; no real-data result exists, and the only performance numbers in this repository are **synthetic** (`reports/ml/`).

## 1. Scope and what is not claimed
- Tiers (MASTER_PLAN section 7): **T-R** retrospective de-identified partner cohort; **T-Q** prospective silent mode (alerts never shown to clinicians). T-L (live pilot) is governed by `docs/clinical/PILOT/` and is not a validation tier.
- Each reported number carries its tier label. Synthetic, T-P (public registries), T-R and T-Q numbers are never pooled in one headline figure.
- Not claimed by any outcome of this study: clinical benefit, survival benefit of earlier detection (unproven, E1 in `docs/EVIDENCE.md`), diagnostic use, regulatory clearance. Lead time is reported only as "earlier than the best rule-based comparator, relative to a fixed definition of clinical recurrence".

## 2. Population, index date and outcome (fixed before data are seen)
- **Population:** adults with breast cancer who completed primary treatment and have at least two surveillance laboratory draws after the index date. Exclusions are applied by the loader's rejection report, never by hand.
- **Index date:** date of completion of primary treatment (surgery, or last chemotherapy or radiotherapy session, whichever is later). Features may use only information dated on or before the prediction time.
- **Outcome:** imaging-confirmed distant recurrence or clinical restaging for distant recurrence, whichever is earlier, with the event date being the date of the confirming test. The horizon is 365 days. Competing event: death without recurrence (cumulative-incidence handling, `ML_PROGRAM` 4.3).
- **Verification:** confirmatory imaging is selective in this setting. The partner's trigger for imaging is documented before analysis (`docs/clinical/PARTNERSHIP/DATA-DICTIONARY.md`) and used as a design feature.

## 3. Data partition (fixed before data are seen)
- Patient-level partition by a keyed hash of the pseudonymous patient id (the key itself is held by the data steward and never committed; the freeze file records only a key identifier): 50 % development, 50 % **frozen test**. No visit-level splitting.
- Development split: model recalibration (`ML_PROGRAM` section 5, level 3: recalibrate, never retrain from scratch without an ADR), selection of the operating point, selection of the comparator among the rule and regularised-hazard baselines.
- Frozen test split: opened **once** per pre-registered analysis, with an entry in an append-only access log (`reports/ml/frozen_test_access_log.jsonl` format). A second opening is a protocol deviation and is reported as such.

## 4. Confirmatory hypotheses (family F, Holm-Bonferroni across the three)
| ID | Hypothesis | Estimand and test | Pass criterion (parameters in section 7) |
|---|---|---|---|
| C1 | Calibration is acceptable at the 365-day horizon after recalibration on the development split | Calibration slope (logistic recalibration of the predicted risk) with 95 % patient-level bootstrap CI | CI lies within [PR-01, PR-02] |
| C2 | Discrimination exceeds the pre-selected comparator | IPCW time-dependent AUC at 365 days, difference vs the comparator chosen on the development split, paired bootstrap over **patients** | Lower CI bound of the difference is above PR-03 |
| C3 | Alert burden at the pre-selected operating point is within budget | Alerts per 100 patient-months on the frozen test split, patient-level bootstrap CI | Upper CI bound is at most PR-04 |

Bootstrap: 2000 resamples, patients as the resampling unit, RNG seed fixed in the freeze file; effect sizes are reported with intervals, not only p-values. A criterion not met is reported as not met; no analysis is added or replaced after the test split is opened.

## 5. Secondary and descriptive analyses (no pass/fail claim; all reported)
1. **Verification-bias analysis (mandatory).** Sensitivity and specificity are reported only together with an inverse-probability-of-verification-weighted estimate and a Begg-Greenes-type sensitivity analysis; complete-case estimates are labelled as biased upward (as in the synthetic study S3, a simulation result, not a real-data one).
2. **Subgroups** (age band, receptor subtype, stage at diagnosis, facility): metrics with intervals, worst-group value, and a statement of power; a subgroup with fewer than PR-05 events is reported as "insufficient data", not estimated.
3. **Lead time:** distribution (median and interquartile range) between first alert and confirming test, relative to the best comparator, with its definition; length-bias and overdetection caveats stated (`ML_PROGRAM` 4.5).
4. **Calibration before recalibration**, calibration-in-the-large, reliability plot data, decision-curve data with IPCW net benefit.
5. **Missed-Signal Audit (M10), aggregate only:** counts of dismissed significant serial elevations; any cell with fewer than PR-06 patients is suppressed.
6. **Data quality:** the loader's per-row rejection report (counts by reason) is part of the report; a rejection rate above PR-07 stops the analysis for review.

## 6. Silent mode (T-Q) monitoring plan
Silent mode writes alerts to a shadow store that no clinician-facing route can read (`apps/api/vigil_api/silent_mode.py`, Tier 1). The monitoring report is produced on a schedule from the shadow store only, and tests:
- **Alarm-rate audit:** realised alerts per 100 patient-months against the budget of C3, with an exact Poisson interval; breach if the lower bound exceeds PR-04.
- **Calibration drift:** rolling calibration slope and observed/expected ratio over windows of at least PR-08 events; breach if the slope interval excludes [PR-01, PR-02].
- **Conformal coverage tracking:** realised coverage of the conformal sets against the nominal level; breach if below nominal by more than PR-09 over a window of at least PR-08 predictions.
- **Data-shift indicators:** per-analyte missingness and unit-conversion rejection rates; breach if a rate more than doubles against the first window.
A breach pauses further evaluation and triggers the review in `docs/clinical/PILOT/STOP-RULES.md`; it is never "fixed" by editing the budget.

## 7. Decision parameters (each needs a named ratifier before freeze)
| ID | Parameter | Proposed value | Rationale | Status |
|---|---|---|---|---|
| PR-01 | Lower bound of acceptable calibration slope | 0.80 | Conventional reading that a slope well below 1 signals overfitting; to be confirmed by the clinical lead | PROPOSED |
| PR-02 | Upper bound of acceptable calibration slope | 1.20 | Symmetric counterpart | PROPOSED |
| PR-03 | Minimum AUC improvement over the comparator (lower CI bound) | 0.00 | A non-inferiority-style bar is the least that can honestly be claimed; a clinically meaningful margin must be set by clinicians | PROPOSED |
| PR-04 | Alert budget (alerts per 100 patient-months) | **no default** | Depends on clinic workload and test cost; the clinical lead sets it. The operating point is chosen on the development split to meet it | PROPOSED (value required) |
| PR-05 | Minimum events for a subgroup estimate | 20 | Below this an interval is uninformative; to be checked against `docs/clinical/SAMPLE-SIZE.md` | PROPOSED |
| PR-06 | Small-cell suppression threshold (patients) | 5 | Common disclosure-control convention; the data steward may require more | PROPOSED |
| PR-07 | Loader rejection rate that stops the analysis | 0.10 | A tenth of rows failing validation suggests a mapping error, not noise | PROPOSED |
| PR-08 | Minimum window size for silent-mode drift monitoring (events or predictions) | 30 | Smaller windows give intervals too wide to act on | PROPOSED |
| PR-09 | Tolerated shortfall of conformal coverage | 0.05 | Absolute shortfall against the nominal level before a breach | PROPOSED |

## 8. Multiplicity, missing data, deviations
- Holm-Bonferroni across C1 to C3; secondary analyses are descriptive and not corrected.
- Missing analytes: no imputation across patients; missingness is modelled (K1/K3 handle it) and reported by pattern; a sensitivity analysis under MAR/MNAR stress is part of the report.
- Any deviation (loader change, split reopened, parameter changed) is listed in the report with its reason and a `git diff`. Amendments are appended below the freeze line; they never edit the frozen text.

## 9. Reporting
TRIPOD+AI checklist and PROBAST+AI self-appraisal accompany the report. Results are written only by scripts to `reports/clinical/` with the SHA-256 of this file and of the freeze record embedded.

## 10. Freeze procedure (owner and clinical lead)
1. The clinical lead and owner review section 7 and record a named ratification per row (value may differ from the proposal; the ratified value is the one used) in `docs/clinical/PREREG-FREEZE.json` (`ratifications`: id, value, ratifier, date).
2. The data steward records the partition key identifier and the bootstrap seed (the key itself is not committed).
3. Run `python scripts/check_prereg_freeze.py`; it fails on any unratified row, any placeholder, or a SHA-256 mismatch.
4. Commit the freeze record alone. Nothing in this document is edited afterwards.
