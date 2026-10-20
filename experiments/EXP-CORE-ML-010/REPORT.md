# EXP-CORE-ML-010: Development-fit verification propensity validation

Synthetic method-validation only; no clinical or partner-data inference.
Source commit: `a6e00fa873bba13171c4d6f7dffea4a68b58c197`

| Condition | Estimator | Metric | Mean error | Error SD | 95% error percentiles |
|---|---|---|---:|---:|---:|
| MCAR | complete_case | empirical_sensitivity | -0.000488 | 0.013105 | [-0.029973, 0.023538] |
| MCAR | complete_case | empirical_specificity | 0.000303 | 0.005894 | [-0.011451, 0.010812] |
| MCAR | complete_case | apparent_prevalence | 0.000642 | 0.008133 | [-0.014133, 0.015767] |
| MCAR | complete_case | brier_score | -0.000046 | 0.003459 | [-0.005513, 0.006734] |
| MCAR | complete_case | roc_auc | 0.000605 | 0.007635 | [-0.014089, 0.015145] |
| MCAR | development_fit_ipw | empirical_sensitivity | -0.000172 | 0.014427 | [-0.032181, 0.023054] |
| MCAR | development_fit_ipw | empirical_specificity | 0.000214 | 0.006826 | [-0.012953, 0.013736] |
| MCAR | development_fit_ipw | apparent_prevalence | 0.000651 | 0.008588 | [-0.014131, 0.015934] |
| MCAR | development_fit_ipw | brier_score | -0.000082 | 0.003598 | [-0.005571, 0.006822] |
| MCAR | development_fit_ipw | roc_auc | 0.000702 | 0.007650 | [-0.014000, 0.015439] |
| MAR | complete_case | empirical_sensitivity | 0.121178 | 0.014107 | [0.096607, 0.147431] |
| MAR | complete_case | empirical_specificity | -0.087130 | 0.009904 | [-0.105833, -0.067273] |
| MAR | complete_case | apparent_prevalence | 0.091501 | 0.010744 | [0.071485, 0.108321] |
| MAR | complete_case | brier_score | 0.023892 | 0.004301 | [0.015383, 0.032612] |
| MAR | complete_case | roc_auc | -0.018640 | 0.011592 | [-0.041750, 0.004176] |
| MAR | development_fit_ipw | empirical_sensitivity | 0.001350 | 0.016691 | [-0.026099, 0.035293] |
| MAR | development_fit_ipw | empirical_specificity | -0.000467 | 0.006870 | [-0.013403, 0.012625] |
| MAR | development_fit_ipw | apparent_prevalence | -0.000157 | 0.013635 | [-0.030018, 0.020667] |
| MAR | development_fit_ipw | brier_score | -0.000183 | 0.007251 | [-0.014664, 0.013983] |
| MAR | development_fit_ipw | roc_auc | 0.000704 | 0.015862 | [-0.032433, 0.028040] |
| MNAR | complete_case | empirical_sensitivity | 0.063055 | 0.009455 | [0.044952, 0.082380] |
| MNAR | complete_case | empirical_specificity | -0.139458 | 0.017230 | [-0.174639, -0.106467] |
| MNAR | complete_case | apparent_prevalence | 0.292495 | 0.011071 | [0.268774, 0.312612] |
| MNAR | complete_case | brier_score | 0.077626 | 0.004999 | [0.069180, 0.086809] |
| MNAR | complete_case | roc_auc | -0.095394 | 0.014556 | [-0.117931, -0.069076] |
| MNAR | development_fit_ipw | empirical_sensitivity | -0.120832 | 0.016343 | [-0.151005, -0.090545] |
| MNAR | development_fit_ipw | empirical_specificity | 0.000429 | 0.011835 | [-0.018106, 0.023589] |
| MNAR | development_fit_ipw | apparent_prevalence | 0.186622 | 0.022223 | [0.143074, 0.226829] |
| MNAR | development_fit_ipw | brier_score | 0.087689 | 0.013950 | [0.061893, 0.114189] |
| MNAR | development_fit_ipw | roc_auc | -0.073216 | 0.026468 | [-0.132137, -0.024452] |

All replicate-level truth, estimates, errors and diagnostics are preserved in `results.json`. MCAR/MAR are the specified synthetic identification designs; MNAR is a negative control. Results do not validate exchangeability, positivity or mechanism stability in real cohorts.
