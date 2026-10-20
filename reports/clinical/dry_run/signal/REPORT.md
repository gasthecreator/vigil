# Partner evaluation report: SYNTHETIC DRY RUN - NOT A RESULT

> Written by `scripts/run_partner_evaluation.py`; do not edit by hand. Status: **COMPLETED**.

**SYNTHETIC. The data are invented. This run rehearses the code path; it is not a result and says nothing about performance on real patients.**

Parameters: PROPOSED values of PREREGISTRATION.md (not ratified); PR-04 supplied on the command line. Bootstrap: 2000 resamples over patients, seed 20261018. Partition key identifier: `SYNTHETIC-DRYRUN-KEY`.

## Data quality (PREREGISTRATION section 5.6)

| table | rows in | clean | rejected | flagged |
|---|---:|---:|---:|---:|
| patients | 600 | 600 | 0 | 0 |
| baseline_profile | 600 | 600 | 0 | 0 |
| lab_observations | 18645 | 18645 | 0 | 0 |
| clinical_outcomes | 600 | 600 | 0 | 0 |

Rejection rate 0.000 against stop rate 0.1. Rejections by code: none. Complete-case patients: 600.

## Cohort

- cohort complete case: 600
- patients with a landmark: 600
- patients excluded fewer than two post index draws or terminal event before second draw: 0
- landmarks: 5574
- development patients: 307
- test patients: 293
- development events at first landmark: 39
- test events at first landmark: 28

## Development split

- comparator chosen (out-of-fold IPCW AUC): **B3_REGULARIZED_LOGISTIC_HORIZON** from B1_SINGLE_THRESHOLD 0.599, B2_VELOCITY_RULE 0.572, B3_REGULARIZED_LOGISTIC_HORIZON 0.635
- recalibration on out-of-fold predictions: intercept -0.767, slope 0.526
- operating threshold 0.165 (development alert rate 4.880 per 100 patient-months)
- candidate = GradientBoostingBaseline (B4) fitted from scratch on the development split; see ANALYSIS-SPEC.md section 3

## Confirmatory hypotheses (Holm-Bonferroni across three)

met only if the 95% CI criterion holds AND the Holm-adjusted one-sided bootstrap p-value is below 0.05. Test patients: 293.

| id | estimate | 95% CI | criterion | CI criterion | p (one-sided) | p Holm | met |
|---|---:|---|---|---|---:|---:|---|
| C1 | 1.313 | [0.802, 1.936] | CI within [0.8, 1.2] | no | 0.688 | 1.000 | **no** |
| C2 | -0.037 | [-0.159, 0.079] | lower CI bound > 0.0 | no | 0.750 | 1.000 | **no** |
| C3 | 4.455 | [3.651, 5.332] | upper CI bound <= 5.0 | no | 0.101 | 0.301 | **no** |

A criterion not met is reported as not met. C3 measures workload only; meeting it says nothing about whether alerts are correct.

## Secondary and descriptive analyses (no pass/fail claim)

### calibration before recalibration

```json
{
  "ece": 0.03927118513738498,
  "mean_predicted": 0.106497362645587,
  "observed_ipcw": 0.09734945648924323,
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
      "patients": 105,
      "events": 6,
      "result": "insufficient data"
    },
    "age50-64": {
      "patients": 91,
      "events": 14,
      "result": "insufficient data"
    },
    "age>=65": {
      "patients": 97,
      "events": 8,
      "result": "insufficient data"
    },
    "stage I-II": {
      "patients": 170,
      "events": 17,
      "result": "insufficient data"
    },
    "stage III": {
      "patients": 123,
      "events": 11,
      "result": "insufficient data"
    },
    "subtype HER2+": {
      "patients": 137,
      "events": 8,
      "result": "insufficient data"
    },
    "subtype HR+": {
      "patients": 98,
      "events": 9,
      "result": "insufficient data"
    },
    "subtype TNBC": {
      "patients": 58,
      "events": 11,
      "result": "insufficient data"
    }
  },
  "worst_group": null,
  "facility": "single-site extraction: not applicable"
}
```

### lead time

```json
{
  "conditional_lead_time_days": "258.1 \u00b1 197.4",
  "conditional_median_days": 194.0,
  "unconditional_mean_days": 188.6,
  "recurrence_detection_rate": 0.7308,
  "overdetection_rate": 0.544,
  "alert_burden_per_100_pt_years": 20.68,
  "caveat": "relative to the confirming test date; length bias and overdetection apply (ML_PROGRAM 4.5); no survival benefit is implied"
}
```

### m10 aggregate

```json
{
  "patients_with_dismissed_prior_signal": 6,
  "small_cell_threshold": 5
}
```

### verification bias

```json
{
  "complete_case": {
    "sensitivity": 0.32142857142857145,
    "specificity": 0.9550561797752809
  },
  "ipw": {
    "sensitivity": 0.2599566409137687,
    "specificity": 0.9618753517448542,
    "minimum_verified_propensity": 0.2112012174721741,
    "maximum_inverse_weight": 4.7348211907526085,
    "effective_sample_size": 109.7869338609718
  },
  "sensitivity_analysis": [
    {
      "assumed_unverified_event_rate": 0.0,
      "sensitivity": 0.32142857142857145,
      "specificity": 0.9169811320754717
    },
    {
      "assumed_unverified_event_rate": 0.05,
      "sensitivity": 0.2690217391304348,
      "specificity": 0.9176424668227947
    },
    {
      "assumed_unverified_event_rate": 0.1,
      "sensitivity": 0.23684210526315794,
      "specificity": 0.9183508488278093
    },
    {
      "assumed_unverified_event_rate": 0.2,
      "sensitivity": 0.19936708860759492,
      "specificity": 0.9199303742384682
    }
  ],
  "note": "the propensity model is fitted on development patients only and applied to test patients; verified-outcome metrics still require conditional exchangeability and positivity. The complete-case estimate is descriptive, and the assumed-rate sensitivity analysis is not an estimate"
}
```

## What this report does not claim

No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.
