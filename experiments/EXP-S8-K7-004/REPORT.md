# EXP-S8-K7-004: Patient-Grouped Cross-Fitted Causal Estimator

**Evidence class:** synthetic only; this is not clinical validation or a treatment recommendation.

- Run timestamp: `2026-10-20T23:56:49.582219+00:00`
- Implementation commit: `95f87e6`
- Cohort size per condition and seed: 5000
- Cohort seeds: 620261141–620261160 (20 per condition)
- Bootstrap: 1000 patient resamples per cohort-condition
- Treatment is delayed only when radiotherapy starts more than 56 days after surgery.
- The primary estimate is cross-fitted AIPW for the finite-cohort marginal RR.

## Condition summaries

| Condition | Estimable | Mean truth RR | Mean AIPW RR | Mean absolute error | 95% interval coverage |
|---|---:|---:|---:|---:|---:|
| Measured confounding | 20/20 | 1.1436687457008414 | 1.1479382319247005 | 0.004269486223859031 | 19/20 |
| Unmeasured U | 20/20 | 1.1251097247958617 | 1.3007615983057892 | 0.1756518735099275 | 5/20 |

## Registered hypotheses

- H1 measured-confounding recovery: **MET**. Registered criteria require at least 18 of 20 cohort intervals to cover their finite-cohort truth and absolute across-seed mean point-estimate error at most 0.02.
- H2 weighted balance: 20/20 measured-confounding replicates have maximum weighted SMD < 0.10; descriptive only.
- H3 unmeasured confounding: mean AIPW bias under hidden U is 0.1756518735099275; E-values are descriptive sensitivity summaries and do not detect U.

The E-value quantifies a sensitivity association strength for a defined risk ratio; it does not detect whether U exists. Undefined estimates and intervals remain null with explicit reasons in `results.json`.

## Provenance

- Registration SHA-256: `e45086f28a4207eedfe27327e6dadec7df71f841f088834b685994b61fc39caf`
- Implementation SHA-256: `d2100862d4745ddd6dfae6ed577e827722c2ff0c14662df7f024d448e5eb62cb`
- Runner SHA-256: `3053d560c3a17a69d0138e63daaa652a5c753717258d9d4931a18366318ee41b`
- Full per-seed results, denominators, source hashes, and run completion manifest are committed beside this report.
