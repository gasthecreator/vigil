# EXP-CORE-ML-011: simulator mechanism validation

> Synthetic mechanism checks only; these results do not establish clinical calibration or biological realism.

Study source commit: `7bb5533a29df6af8a73d69690065da02d547d992`. Profile: `balanced_synthetic_core_v4`.

## G1 first-order secretion and clearance

Independent RK4 cases: 1000; maximum absolute error: 2.4879227567e-09; passed: True; recurrence-free signal violations: 0.

## G2 Poisson shot noise

Patients: 5000; observed recurrence-linked events: 21229; expected events from eligible person-time: 21503.569430.
Exact Poisson p-value: 0.061216933; conditional event-time uniform KS statistic: 0.0079750199; p-value: 0.1336078.
No-recurrence event-count violations: 0; event-count reconstruction mismatches: 0.

## Replicates

| generator | replicate | patients | recurrence-linked events | eligible person-days |
|---|---:|---:|---:|---:|
| G1 | 0 | 1000 | 0 | 0.000 |
| G1 | 1 | 1000 | 0 | 0.000 |
| G1 | 2 | 1000 | 0 | 0.000 |
| G1 | 3 | 1000 | 0 | 0.000 |
| G1 | 4 | 1000 | 0 | 0.000 |
| G2 | 0 | 1000 | 3999 | 207152.475 |
| G2 | 1 | 1000 | 4438 | 223324.359 |
| G2 | 2 | 1000 | 4153 | 205861.527 |
| G2 | 3 | 1000 | 4459 | 227049.965 |
| G2 | 4 | 1000 | 4180 | 211790.146 |

## Limits

Synthetic mechanism fidelity only; no human parameter calibration, clinical validity, or real-cohort performance is established.
