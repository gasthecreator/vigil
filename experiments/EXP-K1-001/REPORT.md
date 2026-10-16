# EXP-K1-001 Report: Informative Prior Shrinkage

- **Baseline ROC-AUC:** 0.4747
- **Intervention ROC-AUC:** 0.5000
- **Delta ROC-AUC:** +0.0253 [95% CI: -0.0529, +0.0998]
- **Baseline Brier Score:** 0.6506
- **Intervention Brier Score:** 0.6506
- **Delta Brier Score:** +0.0000 [95% CI: +0.0000, +0.0000]
- **Hypothesis Verdict:** REFUTED (CI includes zero)

### Findings
Shrinking prior doubling time bounds produced a delta AUC of +0.0253 with 95% bootstrap confidence interval [-0.0529, +0.0998]. Because the confidence interval encompasses zero, the effect is statistically indistinguishable from noise (RR14), and fails to reach the pre-registered threshold of >=0.02.
