# Partner evaluation report: SYNTHETIC DRY RUN - NOT A RESULT

> Written by `scripts/run_partner_evaluation.py`; do not edit by hand. Status: **COMPLETED**.

**SYNTHETIC. The data are invented. This run rehearses the code path; it is not a result and says nothing about performance on real patients.**

Parameters: PROPOSED values of PREREGISTRATION.md (not ratified); PR-04 supplied on the command line. Bootstrap: 2000 resamples over patients, seed 20261018. Partition key identifier: `SYNTHETIC-DRYRUN-KEY`.

## Data quality (PREREGISTRATION section 5.6)

| table | rows in | clean | rejected | flagged |
|---|---:|---:|---:|---:|
| patients | 600 | 600 | 0 | 0 |
| baseline_profile | 600 | 600 | 0 | 0 |
| lab_observations | 18885 | 18885 | 0 | 0 |
| clinical_outcomes | 600 | 600 | 0 | 0 |

Rejection rate 0.000 against stop rate 0.1. Rejections by code: none. Complete-case patients: 600.

## Cohort

- cohort complete case: 600
- patients with a landmark: 600
- patients excluded fewer than two post index draws or terminal event before second draw: 0
- landmarks: 5635
- development patients: 307
- test patients: 293
- development events at first landmark: 35
- test events at first landmark: 36

## Development split

- comparator chosen (out-of-fold IPCW AUC): **B1_SINGLE_THRESHOLD** from B1_SINGLE_THRESHOLD 0.527, B2_VELOCITY_RULE 0.510, B3_REGULARIZED_LOGISTIC_HORIZON 0.444
- recalibration on out-of-fold predictions: intercept -1.653, slope 0.167
- operating threshold 0.143 (development alert rate 4.882 per 100 patient-months)
- candidate = GradientBoostingBaseline (B4) fitted from scratch on the development split; see ANALYSIS-SPEC.md section 3

## Confirmatory hypotheses (Holm-Bonferroni across three)

met only if the 95% CI criterion holds AND the Holm-adjusted one-sided bootstrap p-value is below 0.05. Test patients: 293.

| id | estimate | 95% CI | criterion | CI criterion | p (one-sided) | p Holm | met |
|---|---:|---|---|---|---:|---:|---|
| C1 | -1.063 | [-3.779, 1.362] | CI within [0.8, 1.2] | no | 0.924 | 1.000 | **no** |
| C2 | -0.030 | [-0.135, 0.072] | lower CI bound > 0.0 | no | 0.730 | 1.000 | **no** |
| C3 | 5.273 | [4.413, 6.169] | upper CI bound <= 5.0 | no | 0.726 | 1.000 | **no** |

A criterion not met is reported as not met. C3 measures workload only; meeting it says nothing about whether alerts are correct.

## Secondary and descriptive analyses (no pass/fail claim)

### calibration before recalibration

```json
{
  "ece": 0.08859496498658179,
  "mean_predicted": 0.13134629170176154,
  "observed_ipcw": 0.1233694612555097,
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
      "patients": 120,
      "events": 14,
      "result": "insufficient data"
    },
    "age50-64": {
      "patients": 85,
      "events": 8,
      "result": "insufficient data"
    },
    "age>=65": {
      "patients": 88,
      "events": 14,
      "result": "insufficient data"
    },
    "stage I-II": {
      "patients": 184,
      "events": 27,
      "ipcw_auc": 0.5136902162047615,
      "ci95": [
        0.38879949638357725,
        0.6416426866464875
      ]
    },
    "stage III": {
      "patients": 109,
      "events": 9,
      "result": "insufficient data"
    },
    "subtype HER2+": {
      "patients": 154,
      "events": 21,
      "ipcw_auc": 0.4107182403390819,
      "ci95": [
        0.2788560797043847,
        0.5495518945473856
      ]
    },
    "subtype HR+": {
      "patients": 86,
      "events": 9,
      "result": "insufficient data"
    },
    "subtype TNBC": {
      "patients": 53,
      "events": 6,
      "result": "insufficient data"
    }
  },
  "worst_group": [
    "subtype HER2+",
    0.4107182403390819
  ],
  "facility": "single-site extraction: not applicable"
}
```

### lead time

```json
{
  "conditional_lead_time_days": "435.0 \u00b1 334.4",
  "conditional_median_days": 280.0,
  "unconditional_mean_days": 159.0,
  "recurrence_detection_rate": 0.3656,
  "overdetection_rate": 0.7622,
  "alert_burden_per_100_pt_years": 23.51,
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
    "sensitivity": 0.05555555555555555,
    "specificity": 0.9354838709677419
  },
  "ipw": {
    "sensitivity": 0.048498709244888194,
    "specificity": 0.9409076188889142,
    "minimum_verified_propensity": 0.2798735284892447,
    "maximum_inverse_weight": 3.5730424574199384,
    "effective_sample_size": 125.68011069569663
  },
  "sensitivity_analysis": [
    {
      "assumed_unverified_event_rate": 0.0,
      "sensitivity": 0.05555555555555555,
      "specificity": 0.933852140077821
    },
    {
      "assumed_unverified_event_rate": 0.05,
      "sensitivity": 0.057692307692307696,
      "specificity": 0.9338826366559486
    },
    {
      "assumed_unverified_event_rate": 0.1,
      "sensitivity": 0.05916030534351145,
      "specificity": 0.9339152119700748
    },
    {
      "assumed_unverified_event_rate": 0.2,
      "sensitivity": 0.06104651162790698,
      "specificity": 0.9339875111507582
    }
  ],
  "note": "the propensity model is fitted on development patients only and applied to test patients; verified-outcome metrics still require conditional exchangeability and positivity. The complete-case estimate is descriptive, and the assumed-rate sensitivity analysis is not an estimate"
}
```

## What this report does not claim

No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.
