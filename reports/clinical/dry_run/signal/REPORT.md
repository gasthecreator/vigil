# Partner evaluation report: SYNTHETIC DRY RUN - NOT A RESULT

> Written by `scripts/run_partner_evaluation.py`; do not edit by hand. Status: **COMPLETED**.

**SYNTHETIC. The data are invented. This run rehearses the code path; it is not a result and says nothing about performance on real patients.**

Parameters: PROPOSED values of PREREGISTRATION.md (not ratified); PR-04 supplied on the command line. Bootstrap: 2000 resamples over patients, seed 20261018. Partition key identifier: `SYNTHETIC-DRYRUN-KEY`.

## Data quality (PREREGISTRATION section 5.6)

| table | rows in | clean | rejected | flagged |
|---|---:|---:|---:|---:|
| patients | 600 | 600 | 0 | 0 |
| baseline_profile | 600 | 600 | 0 | 0 |
| lab_observations | 18354 | 18354 | 0 | 0 |
| clinical_outcomes | 600 | 600 | 0 | 0 |

Rejection rate 0.000 against stop rate 0.1. Rejections by code: none. Complete-case patients: 600.

## Cohort

- cohort complete case: 600
- patients with a landmark: 600
- patients excluded fewer than two post index draws or terminal event before second draw: 0
- landmarks: 5518
- development patients: 307
- test patients: 293
- development events at first landmark: 45
- test events at first landmark: 36

## Development split

- comparator chosen (out-of-fold IPCW AUC): **B3_REGULARIZED_LOGISTIC_HORIZON** from B1_SINGLE_THRESHOLD 0.582, B2_VELOCITY_RULE 0.651, B3_REGULARIZED_LOGISTIC_HORIZON 0.685
- recalibration on out-of-fold predictions: intercept -0.739, slope 0.564
- operating threshold 0.200 (development alert rate 4.865 per 100 patient-months)
- candidate = GradientBoostingBaseline (B4) fitted from scratch on the development split; see ANALYSIS-SPEC.md section 3

## Confirmatory hypotheses (Holm-Bonferroni across three)

met only if the 95% CI criterion holds AND the Holm-adjusted one-sided bootstrap p-value is below 0.05. Test patients: 293.

| id | estimate | 95% CI | criterion | CI criterion | p (one-sided) | p Holm | met |
|---|---:|---|---|---|---:|---:|---|
| C1 | 0.943 | [0.586, 1.308] | CI within [0.8, 1.2] | no | 0.187 | 0.374 | **no** |
| C2 | 0.006 | [-0.082, 0.102] | lower CI bound > 0.0 | no | 0.436 | 0.436 | **no** |
| C3 | 3.516 | [2.814, 4.278] | upper CI bound <= 5.0 | yes | 0.000 | 0.001 | **YES** |

A criterion not met is reported as not met. C3 measures workload only; meeting it says nothing about whether alerts are correct.

## Secondary and descriptive analyses (no pass/fail claim)

### calibration before recalibration

```json
{
  "ece": 0.06112648365029434,
  "mean_predicted": 0.11897231086444977,
  "observed_ipcw": 0.1250139904656653,
  "note": "ECE and calibration-in-the-large means use IPCW weights on determinable outcomes"
}
```

### decision curve

```json
{
  "not_run": "no clinically ratified PR-10 threshold grid is present in the frozen protocol"
}
```

### subgroups

```json
{
  "groups": {
    "age<50": {
      "patients": 114,
      "events": 15,
      "result": "insufficient data"
    },
    "age50-64": {
      "patients": 79,
      "events": 9,
      "result": "insufficient data"
    },
    "age>=65": {
      "patients": 100,
      "events": 12,
      "result": "insufficient data"
    },
    "stage I-II": {
      "patients": 183,
      "events": 22,
      "ipcw_auc": 0.6179869978511685,
      "ci95": [
        0.48214858857021436,
        0.7450245133514669
      ]
    },
    "stage III": {
      "patients": 110,
      "events": 14,
      "result": "insufficient data"
    },
    "subtype HER2+": {
      "patients": 151,
      "events": 15,
      "result": "insufficient data"
    },
    "subtype HR+": {
      "patients": 96,
      "events": 14,
      "result": "insufficient data"
    },
    "subtype TNBC": {
      "patients": 46,
      "events": 7,
      "result": "insufficient data"
    }
  },
  "worst_group": [
    "stage I-II",
    0.6179869978511685
  ],
  "facility": "single-site extraction: not applicable"
}
```

### lead time

```json
{
  "conditional_lead_time_days": "199.9 \u00b1 97.2",
  "conditional_median_days": 196.0,
  "unconditional_mean_days": 141.0,
  "recurrence_detection_rate": 0.7051,
  "overdetection_rate": 0.4811,
  "alert_burden_per_100_pt_years": 17.66,
  "caveat": "relative to the confirming test date; length bias and overdetection apply (ML_PROGRAM 4.5); no survival benefit is implied"
}
```

### m10 aggregate

```json
{
  "patients_with_dismissed_prior_signal": 10,
  "small_cell_threshold": 5
}
```

### verification bias

```json
{
  "complete_case": {
    "sensitivity": 0.2777777777777778,
    "specificity": 0.9393939393939394
  },
  "ipw": {
    "sensitivity": 0.20877039335439626,
    "specificity": 0.950211151152116,
    "minimum_verified_propensity": 0.26830426937966756,
    "maximum_inverse_weight": 3.7271117687096385,
    "effective_sample_size": 96.50427096733927
  },
  "sensitivity_analysis": [
    {
      "assumed_unverified_event_rate": 0.0,
      "sensitivity": 0.2777777777777778,
      "specificity": 0.9610894941634242
    },
    {
      "assumed_unverified_event_rate": 0.05,
      "sensitivity": 0.22612513721185512,
      "specificity": 0.960800161648818
    },
    {
      "assumed_unverified_event_rate": 0.1,
      "sensitivity": 0.1923774954627949,
      "specificity": 0.960487599831862
    },
    {
      "assumed_unverified_event_rate": 0.2,
      "sensitivity": 0.1509433962264151,
      "specificity": 0.959780621572212
    }
  ],
  "note": "the propensity model is fitted on development patients only and applied to test patients; verified-outcome metrics still require conditional exchangeability and positivity. The complete-case estimate is descriptive, and the assumed-rate sensitivity analysis is not an estimate"
}
```

## What this report does not claim

No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.
