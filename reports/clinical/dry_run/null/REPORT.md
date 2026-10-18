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
- patients excluded fewer than two post index draws or recurred first: 0
- landmarks: 5635
- development patients: 307
- test patients: 293
- development events at first landmark: 35
- test events at first landmark: 36

## Development split

- comparator chosen (out-of-fold IPCW AUC): **B1_SINGLE_THRESHOLD** from B1_SINGLE_THRESHOLD 0.543, B2_VELOCITY_RULE 0.503, B3_REGULARIZED_COX_HAZARD 0.458
- recalibration on out-of-fold predictions: intercept -1.250, slope 0.374
- operating threshold 0.182 (development alert rate 4.882 per 100 patient-months)
- candidate = GradientBoostingBaseline (B4) fitted from scratch on the development split; see ANALYSIS-SPEC.md section 3

## Confirmatory hypotheses (Holm-Bonferroni across three)

met only if the 95% CI criterion holds AND the Holm-adjusted one-sided bootstrap p-value is below 0.05. Test patients: 293.

| id | estimate | 95% CI | criterion | CI criterion | p (one-sided) | p Holm | met |
|---|---:|---|---|---|---:|---:|---|
| C1 | -0.762 | [-2.239, 0.579] | CI within [0.8, 1.2] | no | 0.989 | 1.000 | **no** |
| C2 | -0.046 | [-0.207, 0.112] | lower CI bound > 0.0 | no | 0.710 | 1.000 | **no** |
| C3 | 5.118 | [4.306, 5.928] | upper CI bound <= 5.0 | no | 0.594 | 1.000 | **no** |

A criterion not met is reported as not met. C3 measures workload only; meeting it says nothing about whether alerts are correct.

## Secondary and descriptive analyses (no pass/fail claim)

### calibration before recalibration

```json
{
  "ece": 0.09311833083629609,
  "mean_predicted": 0.14306637995523594,
  "observed_ipcw": 0.1233694612555097,
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
    0.11451460732879767,
    0.03921394845628333,
    -0.009539040851614004,
    -0.0029789731004601153,
    0.0,
    0.0,
    0.0,
    0.0
  ],
  "net_benefit_all": [
    0.11451460732879767,
    0.04714071875598881,
    -0.0313300455817533,
    -0.12388530608267982,
    -0.23469089964012718,
    -0.36973521678826615,
    -0.5379483135868248,
    -0.7532610774889804
  ]
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
      "ipcw_auc": 0.49610832994629195,
      "ci95": [
        0.3607135996596697,
        0.6315442319960717
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
      "ipcw_auc": 0.3821165942264598,
      "ci95": [
        0.23672090171394167,
        0.5379278221532162
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
    0.3821165942264598
  ],
  "facility": "single-site extraction: not applicable"
}
```

### lead time

```json
{
  "conditional_lead_time_days": "428.3 \u00b1 277.6",
  "conditional_median_days": 358.0,
  "unconditional_mean_days": 147.4,
  "recurrence_detection_rate": 0.3441,
  "overdetection_rate": 0.7557,
  "alert_burden_per_100_pt_years": 21.53,
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
    "sensitivity": 0.08333333333333333,
    "specificity": 0.956989247311828
  },
  "ipw": {
    "sensitivity": 0.08513766215559572,
    "specificity": 0.9573454869000981
  },
  "sensitivity_analysis": [
    {
      "assumed_unverified_event_rate": 0.0,
      "sensitivity": 0.08333333333333333,
      "specificity": 0.9571984435797666
    },
    {
      "assumed_unverified_event_rate": 0.05,
      "sensitivity": 0.0757918552036199,
      "specificity": 0.9571945337620579
    },
    {
      "assumed_unverified_event_rate": 0.1,
      "sensitivity": 0.07061068702290076,
      "specificity": 0.9571903574397339
    },
    {
      "assumed_unverified_event_rate": 0.2,
      "sensitivity": 0.06395348837209301,
      "specificity": 0.9571810883140054
    }
  ],
  "note": "complete-case estimates are biased by selective verification; the sensitivity analysis varies an assumed event rate among unverified patients and is not an estimate"
}
```

## What this report does not claim

No clinical benefit, no survival benefit of earlier detection, no diagnostic use, no regulatory status. Single-site retrospective data cannot establish any of these.
