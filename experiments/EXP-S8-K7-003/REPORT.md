# EXP-S8-K7-003: Cross-Fitted Causal Estimator Recovery

**Evidence class:** synthetic only; this is not clinical validation or a treatment recommendation.

- Run timestamp: `2026-10-20T20:41:37.622912+00:00`
- Implementation commit: `c5a6ded08be00a3dbdc75c6d80bf83aa4e9563e0`
- Cohort size per condition and seed: 5000
- Cohort seeds: 620261121–620261140 (20 per condition)
- Bootstrap: 1000 patient resamples per cohort-condition
- Treatment is delayed only when radiotherapy starts more than 56 days after surgery.
- The primary estimate is cross-fitted AIPW for the finite-cohort marginal RR.

## Condition summaries

| Condition | Estimable | Mean truth RR | Mean AIPW RR | Mean absolute error | 95% interval coverage |
|---|---:|---:|---:|---:|---:|
| Measured confounding | 20/20 | 1.1436639861425295 | 1.1474709474659457 | 0.0038069613234161803 | 20/20 |
| Unmeasured U | 20/20 | 1.1252167752952595 | 1.302817310650893 | 0.17760053535563336 | 6/20 |

## Registered hypotheses

- H1 measured-confounding recovery: **MET**. Registered criteria require at least 18 of 20 cohort intervals to cover their finite-cohort truth and absolute across-seed mean point-estimate error at most 0.02.
- H2 weighted balance: 20/20 measured-confounding replicates have maximum weighted SMD < 0.10; descriptive only.
- H3 unmeasured confounding: mean AIPW bias under hidden U is 0.17760053535563336; E-values are descriptive sensitivity summaries and do not detect U.

The E-value quantifies a sensitivity association strength for a defined risk ratio; it does not detect whether U exists. Undefined estimates and intervals remain null with explicit reasons in `results.json`.

## Provenance

- Registration SHA-256: `c38c1023e3f1731d523f0ede732c7a8295ece847fd6d4303c56f731048134fc5`
- Implementation SHA-256: `071a8e50c036adf42f35bb41ab264469ba72af34b440dd439eba23eaff0a4625`
- Runner SHA-256: `66f63423d31541e9799103aa7c20490cc18eb84e82f6468edfef5ad0c48371b3`
- Full per-seed results, denominators, source hashes, and run completion manifest are committed beside this report.
