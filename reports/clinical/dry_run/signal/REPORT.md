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
- patients excluded fewer than two post index draws or recurred first: 0
- landmarks: 5574
- development patients: 307
- test patients: 293
- development events at first landmark: 39
- test events at first landmark: 28

## Development split

- comparator chosen (out-of-fold IPCW AUC): **B2_VELOCITY_RULE** from B1_SINGLE_THRESHOLD 0.582, B2_VELOCITY_RULE 0.637, B3_REGULARIZED_COX_HAZARD 0.625
- recalibration on out-of-fold predictions: intercept -0.893, slope 0.497
- operating threshold 0.165 (development alert rate 4.880 per 100 patient-months)
- candidate = GradientBoostingBaseline (B4) fitted from scratch on the development split; see ANALYSIS-SPEC.md section 3

## Confirmatory hypotheses (Holm-Bonferroni across three)

met only if the 95% CI criterion holds AND the Holm-adjusted one-sided bootstrap p-value is below 0.05. Test patients: 293.

| id | estimate | 95% CI | criterion | CI criterion | p (one-sided) | p Holm | met |
|---|---:|---|---|---|---:|---:|---|
| C1 | 1.130 | [0.713, 1.590] | CI within [0.8, 1.2] | no | 0.391 | 0.781 | **no** |
| C2 | -0.057 | [-0.191, 0.064] | lower CI bound > 0.0 | no | 0.814 | 0.814 | **no** |
| C3 | 4.506 | [3.699, 5.358] | upper CI bound <= 5.0 | no | 0.132 | 0.396 | **no** |

A criterion not met is reported as not met. C3 measures workload only; meeting it says nothing about whether alerts are correct.

## Secondary and descriptive analyses (no pass/fail claim)

### calibration before recalibration

```json
{
  "ece": 0.04591479576446793,
  "mean_predicted": 0.11427875015058993,
  "observed_ipcw": 0.09734945648924323,
  "note": "ECE is unweighted and on determinable outcomes only; the IPCW means are the calibration-in-the-large inputs"
}
```

### decision curve

```json
{
  "thresholds": [
    0.01,
    0.08,
    0.15000000000000002,
    0.22,
    0.29000000000000004,
    0.36000000000000004,
    0.43,
    0.5
  ],
  "net_benefit_model": [
    0.08823177423155883,
    0.025106480201931194,
    0.01408343382443029,
    0.01673627339191395,
    0.014995490802004133,
    0.01226722396476724,
    0.017732879113164998,
    0.020489749158691138
  ],
  "net_benefit_all": [
    0.08823177423155883,
    0.01885810487961223,
    -0.06194181589500794,
    -0.15724428655225217,
    -0.2713387936771221,
    -0.41039147423555744,
    -0.5835974447557133,
    -0.8053010870215133
  ]
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
  "conditional_lead_time_days": "266.4 \u00b1 229.3",
  "conditional_median_days": 194.0,
  "unconditional_mean_days": 194.6,
  "recurrence_detection_rate": 0.7308,
  "overdetection_rate": 0.525,
  "alert_burden_per_100_pt_years": 19.85,
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
    "specificity": 0.9438202247191011
  },
  "ipw": {
    "sensitivity": 0.28953889150736306,
    "specificity": 0.9428302767008229
  },
  "sensitivity_analysis": [
    {
      "assumed_unverified_event_rate": 0.0,
      "sensitivity": 0.32142857142857145,
      "specificity": 0.939622641509434
    },
    {
      "assumed_unverified_event_rate": 0.05,
      "sensitivity": 0.2595108695652174,
      "specificity": 0.939695550351288
    },
    {
      "assumed_unverified_event_rate": 0.1,
      "sensitivity": 0.22149122807017543,
      "specificity": 0.9397736459175424
    },
    {
      "assumed_unverified_event_rate": 0.2,
      "sensitivity": 0.1772151898734177,
      "specificity": 0.9399477806788511
    }
  ],
  "note": "complete-case estimates are biased by selective verification; the sensitivity analysis varies an assumed event rate among unverified patients and is not an estimate"
}
```

## What this report does not claim

No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.
