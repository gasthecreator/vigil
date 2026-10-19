# EXP-K1-004 conclusion

## Decision

**K1 remains research-only and is not supported for product marker forecasting or recurrence-risk prediction.** The registered product-world estimand was future measured CA 15-3, not recurrence. On that marker-forecast estimand, K1 lost to both preregistered marker-only baselines in every generator/seed pair and its 90% predictive intervals substantially under-covered. No product-facing K1 score should be enabled.

The study also does not establish a generally calibrated four-parameter posterior. Recovery was evaluated under a synthetic model; the local Fisher analysis marks CA 15-3 clearance non-identifiable at the registered reference point, several route/setting SBC results are poor, and NUTS had nonzero divergences. Exact metrics and diagnostics remain in `results.json`.

## Training and provenance

Both estimators selected registered training seed 41002 using independent validation NLL. The amortized estimator selected epoch 12 with validation NLL 0.843916; the NPE estimator selected epoch 27 with validation NLL 6.725775. A failed pre-study smoke attempt exposed a Git status parsing defect; no evaluation cohort was accessed in that attempt. After correcting the parser and amending the preregistration to 1.10, both estimators were retrained. The repeated training histories and weight tensors matched the earlier deterministic run; artifact metadata changed with the protocol version. The successful smoke check passed before final evaluation.

The completed run used source commit `bbc1eded06ee9445e8a49c2a0e30324d46b45f42`, protocol 1.10, and the registered seeds. `ACCESS_LOG.json` marks completion and records one G3 access; its result SHA-256 matches `results.json`. The machine-readable outputs include all own-world, marker-transfer, low-data, bootstrap, SBC, identifiability, NUTS and particle-filter diagnostics.

## Own-world findings

Doubling-time RMSE averaged across the three registered seeds was 24.39 days (amortized), 24.38 (NPE), 23.80 (particle filter), and 21.76 on the 30-patient-per-seed NUTS subset for the correctly specified irregular-visit setting. Under sparse visits and missing analytes, it was 31.43, 30.43, 28.85, and 28.68 days respectively. Under misspecified noise and visit process, it was 29.69, 29.40, 29.40, and 26.10 days. These are synthetic parameter-recovery results, not clinical estimates.

The computed local Fisher spectrum identified one weak direction, CA 15-3 clearance. NUTS produced finite R-hat/ESS diagnostics but also 10 divergences in the irregular-visit subset, 54 in the sparse/missingness subset, and 34 in the misspecified subset. Neural and particle SBC results varied by parameter and setting; the complete KS p-values and interval coverage are reported without converting them into an unregistered pass threshold.

## Product-world marker transfer

These are equal-weight means of the three seed-level patient estimates; patient-bootstrap intervals remain reported separately in `results.json`.

| Generator | K1 MAE | Carry-forward MAE | Linear-trend MAE | K1 90% interval coverage |
|---|---:|---:|---:|---:|
| G1 smooth kinetics | 1644.37 | 87.27 | 128.59 | 0.293 |
| G2 shedding bursts | 1089.83 | 34.91 | 55.50 | 0.272 |
| G3 heavy-tailed noise | 912.31 | 37.39 | 28.76 | 0.349 |

K1 lost in all nine generator/seed comparisons. The low-data subgroup (at most six measured pre-landmark visits) had nearly the same performance because most eligible patients met that visit-count condition. This is a decisive negative result for transfer of the declared K1 marker model to the current simulator. It does not justify changing the fixed transfer data or tuning K1 against them.

## Contract and repository gates

The one-time acceptance result is recorded in `ACCEPTANCE.md`: 14 passed, 1 expected xfail, and 2 failed. The two failures concern the small-sample 39/40 coverage boundary and the training negative-control semantics; neither was tuned or worked around. The K1-WORLD recurrence gate xfailed under the registered stub. See `docs/proposals/PROP-K1-ACCEPTANCE-BOUNDARIES.md`.

The full repository suite completed with 877 passed, 18 skipped and 2 failed. The failures are the already documented legacy censor-aware AUC floors in `test_k3_joint_model_distinct_from_single_threshold` and `test_gbm_reaches_at_least_single_threshold_auc`; their assertions remain unchanged. Repository lint, evidence, excerpt, hazard, claims, i18n, docs, lockfile and status checks passed. The docs build passed with existing navigation/link warnings. The branch is not merge-ready while these gates remain red.
