# EXP-CORE-ML-009: Verification-bias estimator validation

Synthetic method-validation results only; no clinical or real-cohort claim.

Source commit: `f2a1cf859009cd66b59386e19fca441826f627fc`
Cohort design: 100 replicates × 2500 per condition.

Mean estimate-minus-full-cohort error (with replicate SD), by verification mechanism:

| Mechanism | Estimator | Metric | Mean error | Replicate SD | 95% error percentiles |
|---|---|---|---:|---:|---:|
| MCAR | complete_case | empirical_sensitivity | -0.000076 | 0.013219 | [-0.023034, 0.026463] |
| MCAR | complete_case | empirical_specificity | -0.001249 | 0.005323 | [-0.010602, 0.008192] |
| MCAR | complete_case | apparent_prevalence | 0.000459 | 0.008661 | [-0.013852, 0.017506] |
| MCAR | complete_case | brier_score | 0.000382 | 0.003097 | [-0.004639, 0.005921] |
| MCAR | complete_case | roc_auc | -0.000621 | 0.007931 | [-0.014060, 0.016121] |
| MCAR | ipw | empirical_sensitivity | -0.000790 | 0.012901 | [-0.023845, 0.021544] |
| MCAR | ipw | empirical_specificity | -0.000867 | 0.004958 | [-0.010847, 0.008453] |
| MCAR | ipw | apparent_prevalence | -0.000023 | 0.007578 | [-0.013497, 0.014439] |
| MCAR | ipw | brier_score | 0.000258 | 0.002881 | [-0.004646, 0.005423] |
| MCAR | ipw | roc_auc | -0.000558 | 0.007919 | [-0.014006, 0.015863] |
| MAR | complete_case | empirical_sensitivity | 0.143898 | 0.016767 | [0.108766, 0.173352] |
| MAR | complete_case | empirical_specificity | -0.103676 | 0.013290 | [-0.129800, -0.081323] |
| MAR | complete_case | apparent_prevalence | 0.105468 | 0.011327 | [0.085126, 0.127945] |
| MAR | complete_case | brier_score | 0.024613 | 0.005092 | [0.015282, 0.035388] |
| MAR | complete_case | roc_auc | -0.016483 | 0.013788 | [-0.048036, 0.003869] |
| MAR | ipw | empirical_sensitivity | 0.002687 | 0.017865 | [-0.038721, 0.034739] |
| MAR | ipw | empirical_specificity | -0.000560 | 0.005167 | [-0.010581, 0.010018] |
| MAR | ipw | apparent_prevalence | -0.000158 | 0.011123 | [-0.022197, 0.021485] |
| MAR | ipw | brier_score | -0.000878 | 0.007344 | [-0.014300, 0.015650] |
| MAR | ipw | roc_auc | 0.003366 | 0.018048 | [-0.033196, 0.036466] |
| MNAR | complete_case | empirical_sensitivity | 0.079955 | 0.009600 | [0.062521, 0.099380] |
| MNAR | complete_case | empirical_specificity | -0.154215 | 0.020638 | [-0.190557, -0.112888] |
| MNAR | complete_case | apparent_prevalence | 0.343816 | 0.013263 | [0.315963, 0.371965] |
| MNAR | complete_case | brier_score | 0.081647 | 0.005210 | [0.071828, 0.091016] |
| MNAR | complete_case | roc_auc | -0.100030 | 0.014197 | [-0.124622, -0.075948] |
| MNAR | ipw | empirical_sensitivity | -0.127120 | 0.010038 | [-0.143489, -0.107197] |
| MNAR | ipw | empirical_specificity | 0.006050 | 0.009705 | [-0.012368, 0.021971] |
| MNAR | ipw | apparent_prevalence | 0.227947 | 0.027097 | [0.163846, 0.268775] |
| MNAR | ipw | brier_score | 0.102755 | 0.017121 | [0.066615, 0.132931] |
| MNAR | ipw | roc_auc | -0.070612 | 0.028223 | [-0.115412, -0.012541] |

All replicate records, full-cohort references, estimates, weights, and diagnostics are in `results.json`.
MCAR/MAR estimates are conditional on the registered one-covariate logistic design. MNAR intentionally omits the outcome from the propensity model; its bias is an identification-boundary result.
