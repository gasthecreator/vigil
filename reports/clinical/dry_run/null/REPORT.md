# Partner evaluation report: SYNTHETIC DRY RUN - NOT A RESULT

> Written by `scripts/run_partner_evaluation.py`; do not edit by hand. Status: **COMPLETED**.

**SYNTHETIC. The data are invented. This run rehearses the code path; it is not a result and says nothing about performance on real patients.**

Parameters: PROPOSED values of PREREGISTRATION.md (not ratified); PR-04 supplied on the command line. Bootstrap: 2000 resamples over patients, seed 20261018. Partition key identifier: `SYNTHETIC-DRYRUN-KEY`.

## Data quality (PREREGISTRATION section 5.6)

| table | rows in | clean | rejected | flagged |
|---|---:|---:|---:|---:|
| patients | 600 | 600 | 0 | 0 |
| baseline_profile | 600 | 600 | 0 | 0 |
| lab_observations | 18390 | 18390 | 0 | 0 |
| clinical_outcomes | 600 | 600 | 0 | 0 |

Rejection rate 0.000 against stop rate 0.1. Rejections by code: none. Complete-case patients: 600.

## Cohort

- cohort complete case: 600
- patients with a landmark: 600
- patients excluded fewer than two post index draws or terminal event before second draw: 0
- landmarks: 5530
- development patients: 307
- test patients: 293
- development events at first landmark: 43
- test events at first landmark: 42

## Development split

- comparator chosen (out-of-fold IPCW AUC): **B2_VELOCITY_RULE** from B1_SINGLE_THRESHOLD 0.505, B2_VELOCITY_RULE 0.514, B3_REGULARIZED_LOGISTIC_HORIZON 0.492
- recalibration on out-of-fold predictions: intercept -1.345, slope 0.230
- operating threshold 0.174 (development alert rate 4.887 per 100 patient-months)
- candidate = GradientBoostingBaseline (B4) fitted from scratch on the development split; see ANALYSIS-SPEC.md section 3

## Confirmatory hypotheses (Holm-Bonferroni across three)

met only if the 95% CI criterion holds AND the Holm-adjusted one-sided bootstrap p-value is below 0.05. Test patients: 293.

| id | estimate | 95% CI | criterion | CI criterion | p (one-sided) | p Holm | met |
|---|---:|---|---|---|---:|---:|---|
| C1 | -1.734 | [-3.808, 0.210] | CI within [0.8, 1.2] | no | 0.995 | 1.000 | **no** |
| C2 | -0.033 | [-0.156, 0.085] | lower CI bound > 0.0 | no | 0.695 | 1.000 | **no** |
| C3 | 3.921 | [2.990, 4.968] | upper CI bound <= 5.0 | yes | 0.021 | 0.061 | **no** |

A criterion not met is reported as not met. C3 measures workload only; meeting it says nothing about whether alerts are correct.

## Secondary and descriptive analyses (no pass/fail claim)

### calibration before recalibration

```json
{
  "ece": 0.0904955008679142,
  "mean_predicted": 0.12748014295918675,
  "observed_ipcw": 0.14458276239637544,
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
      "patients": 118,
      "events": 14,
      "result": "insufficient data"
    },
    "age50-64": {
      "patients": 82,
      "events": 10,
      "result": "insufficient data"
    },
    "age>=65": {
      "patients": 93,
      "events": 18,
      "result": "insufficient data"
    },
    "stage I-II": {
      "patients": 177,
      "events": 20,
      "ipcw_auc": 0.4831167338272715,
      "ci95": [
        0.3537924852092443,
        0.6110552295788424
      ]
    },
    "stage III": {
      "patients": 116,
      "events": 22,
      "ipcw_auc": 0.3796807383141365,
      "ci95": [
        0.2517618552377042,
        0.5127291629686477
      ]
    },
    "subtype HER2+": {
      "patients": 144,
      "events": 24,
      "ipcw_auc": 0.4018722752701146,
      "ci95": [
        0.2779191985895781,
        0.5307617125964708
      ]
    },
    "subtype HR+": {
      "patients": 103,
      "events": 11,
      "result": "insufficient data"
    },
    "subtype TNBC": {
      "patients": 46,
      "events": 7,
      "result": "insufficient data"
    }
  },
  "worst_group": [
    "stage III",
    0.3796807383141365
  ],
  "facility": "single-site extraction: not applicable"
}
```

### lead time

```json
{
  "not_computed": "No censoring- and competing-risk-aware lead-time/over-detection estimand is registered for partner follow-up."
}
```

### m10 aggregate

```json
{
  "patients_with_dismissed_prior_signal": 11,
  "small_cell_threshold": 5
}
```

### verification bias

```json
{
  "complete_case": {
    "sensitivity": 0.047619047619047616,
    "specificity": 0.9512195121951219
  },
  "ipw": {
    "sensitivity": 0.051816719243133025,
    "specificity": 0.9511466972458436,
    "minimum_verified_propensity": 0.32943742232684536,
    "maximum_inverse_weight": 3.0354778547528465,
    "effective_sample_size": 122.719508749161
  },
  "sensitivity_analysis": [
    {
      "assumed_unverified_event_rate": 0.0,
      "sensitivity": 0.047619047619047616,
      "specificity": 0.9601593625498008
    },
    {
      "assumed_unverified_event_rate": 0.05,
      "sensitivity": 0.04558969276511397,
      "specificity": 0.9600082457225315
    },
    {
      "assumed_unverified_event_rate": 0.1,
      "sensitivity": 0.044142614601018676,
      "specificity": 0.9598462195642887
    },
    {
      "assumed_unverified_event_rate": 0.2,
      "sensitivity": 0.04221635883905014,
      "specificity": 0.9594843462246777
    }
  ],
  "note": "the propensity model is fitted on development patients only and applied to test patients; verified-outcome metrics still require conditional exchangeability and positivity. The complete-case estimate is descriptive, and the assumed-rate sensitivity analysis is not an estimate"
}
```

## What this report does not claim

No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.
