# EXP-K1-002 Report: Interval-Adaptive Noise Scaling

- **Baseline ROC-AUC:** 0.4747
- **Intervention ROC-AUC:** 0.5090
- **Delta ROC-AUC:** +0.0343 [95% CI: -0.0508, +0.1176]
- **Baseline Brier Score:** 0.6506
- **Intervention Brier Score:** 0.4354
- **Delta Brier Score:** -0.2152 [95% CI: -0.2489, -0.1858]
- **Hypothesis Verdict:** REFUTED (CI includes zero)

### Findings
Interval-adaptive noise scaling adjusted for clustered sampling intervals, producing a delta AUC of +0.0343 with 95% bootstrap confidence interval [-0.0508, +0.1176]. Per RR14, because this interval encompasses zero, the effect is statistically indistinguishable from zero and the pre-registered hypothesis is refuted.
