# EXP-CORE-ML-008 — cross-generator core baseline evaluation

> Synthetic research evaluation only; not clinical validation, a deployment recommendation, or a population estimate.

Profile: `balanced_synthetic_v1`. Horizon: 365 days. Five independent cohorts per test generator, with 1000 patients each.

## Validation-selected configurations

| Model | Configuration | Pooled validation IPCW Brier |
|---|---|---:|
| B3_regularized_logistic_horizon | C=0.05 | 0.107542 |
| B4_xgboost_horizon | depth=3,estimators=150,learning_rate=0.05 | 0.096893 |

## Test results: G1

| Model | IPCW AUC | IPCW Brier | IPCW ECE | IPCW average precision |
|---|---:|---:|---:|---:|
| B0_prevalence | 0.5000 [0.5000, 0.5000] | 0.1243 [0.1196, 0.1292] | 0.0481 [0.0401, 0.0557] | 0.1422 [0.1346, 0.1501] |
| B1_single_threshold | 0.5643 [0.5548, 0.5750] | 0.1167 [0.1124, 0.1213] | 0.0638 [0.0563, 0.0710] | 0.2434 [0.2292, 0.2580] |
| B2_velocity | 0.5251 [0.5158, 0.5347] | 0.1222 [0.1177, 0.1269] | 0.0549 [0.0483, 0.0622] | 0.1773 [0.1671, 0.1887] |
| B3_regularized_logistic_horizon | 0.7727 [0.7595, 0.7859] | 0.0983 [0.0944, 0.1025] | 0.0551 [0.0493, 0.0623] | 0.5067 [0.4851, 0.5291] |
| B4_xgboost_horizon | 0.8003 [0.7881, 0.8120] | 0.0897 [0.0857, 0.0940] | 0.0526 [0.0478, 0.0595] | 0.5735 [0.5523, 0.5941] |

### Paired learned-model differences versus B0/B1/B2

| Model | Comparator | Metric | Difference [95% patient-cluster CI] | Valid resamples |
|---|---|---|---:|---:|
| B3_regularized_logistic_horizon | B0_prevalence | auc | 0.2727 [0.2595, 0.2859] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | brier | -0.0259 [-0.0287, -0.0233] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | ipcw_ece | 0.0071 [0.0036, 0.0124] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | average_precision | 0.3645 [0.3449, 0.3858] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | auc | 0.2084 [0.1925, 0.2240] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | brier | -0.0184 [-0.0210, -0.0160] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | ipcw_ece | -0.0086 [-0.0120, -0.0036] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | average_precision | 0.2633 [0.2444, 0.2831] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | auc | 0.2476 [0.2321, 0.2633] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | brier | -0.0239 [-0.0264, -0.0215] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | ipcw_ece | 0.0002 [-0.0041, 0.0045] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | average_precision | 0.3293 [0.3114, 0.3499] | 1000 |
| B4_xgboost_horizon | B0_prevalence | auc | 0.3003 [0.2881, 0.3120] | 1000 |
| B4_xgboost_horizon | B0_prevalence | brier | -0.0346 [-0.0374, -0.0318] | 1000 |
| B4_xgboost_horizon | B0_prevalence | ipcw_ece | 0.0045 [0.0014, 0.0107] | 1000 |
| B4_xgboost_horizon | B0_prevalence | average_precision | 0.4313 [0.4127, 0.4505] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | auc | 0.2360 [0.2205, 0.2509] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | brier | -0.0270 [-0.0297, -0.0246] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | ipcw_ece | -0.0112 [-0.0141, -0.0051] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | average_precision | 0.3301 [0.3113, 0.3480] | 1000 |
| B4_xgboost_horizon | B2_velocity | auc | 0.2752 [0.2600, 0.2901] | 1000 |
| B4_xgboost_horizon | B2_velocity | brier | -0.0325 [-0.0354, -0.0299] | 1000 |
| B4_xgboost_horizon | B2_velocity | ipcw_ece | -0.0023 [-0.0062, 0.0027] | 1000 |
| B4_xgboost_horizon | B2_velocity | average_precision | 0.3962 [0.3775, 0.4154] | 1000 |

## Test results: G2

| Model | IPCW AUC | IPCW Brier | IPCW ECE | IPCW average precision |
|---|---:|---:|---:|---:|
| B0_prevalence | 0.5000 [0.5000, 0.5000] | 0.1319 [0.1274, 0.1371] | 0.0357 [0.0273, 0.0430] | 0.1545 [0.1472, 0.1629] |
| B1_single_threshold | 0.5134 [0.5085, 0.5188] | 0.1295 [0.1247, 0.1348] | 0.0294 [0.0212, 0.0366] | 0.1773 [0.1689, 0.1869] |
| B2_velocity | 0.4874 [0.4772, 0.4965] | 0.1330 [0.1283, 0.1384] | 0.0463 [0.0417, 0.0526] | 0.1517 [0.1451, 0.1598] |
| B3_regularized_logistic_horizon | 0.7358 [0.7210, 0.7508] | 0.1134 [0.1090, 0.1180] | 0.0340 [0.0329, 0.0439] | 0.4186 [0.3958, 0.4456] |
| B4_xgboost_horizon | 0.7701 [0.7551, 0.7840] | 0.1035 [0.0990, 0.1083] | 0.0388 [0.0364, 0.0474] | 0.5131 [0.4914, 0.5356] |

### Paired learned-model differences versus B0/B1/B2

| Model | Comparator | Metric | Difference [95% patient-cluster CI] | Valid resamples |
|---|---|---|---:|---:|
| B3_regularized_logistic_horizon | B0_prevalence | auc | 0.2358 [0.2210, 0.2508] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | brier | -0.0185 [-0.0212, -0.0160] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | ipcw_ece | -0.0017 [-0.0028, 0.0085] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | average_precision | 0.2641 [0.2435, 0.2872] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | auc | 0.2224 [0.2078, 0.2375] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | brier | -0.0161 [-0.0188, -0.0136] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | ipcw_ece | 0.0046 [0.0038, 0.0150] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | average_precision | 0.2413 [0.2214, 0.2651] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | auc | 0.2483 [0.2318, 0.2661] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | brier | -0.0196 [-0.0224, -0.0171] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | ipcw_ece | -0.0123 [-0.0142, -0.0030] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | average_precision | 0.2669 [0.2458, 0.2907] | 1000 |
| B4_xgboost_horizon | B0_prevalence | auc | 0.2701 [0.2551, 0.2840] | 1000 |
| B4_xgboost_horizon | B0_prevalence | brier | -0.0284 [-0.0314, -0.0256] | 1000 |
| B4_xgboost_horizon | B0_prevalence | ipcw_ece | 0.0031 [-0.0004, 0.0139] | 1000 |
| B4_xgboost_horizon | B0_prevalence | average_precision | 0.3585 [0.3384, 0.3807] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | auc | 0.2567 [0.2421, 0.2704] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | brier | -0.0260 [-0.0289, -0.0232] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | ipcw_ece | 0.0095 [0.0059, 0.0203] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | average_precision | 0.3358 [0.3151, 0.3580] | 1000 |
| B4_xgboost_horizon | B2_velocity | auc | 0.2827 [0.2657, 0.3007] | 1000 |
| B4_xgboost_horizon | B2_velocity | brier | -0.0296 [-0.0325, -0.0267] | 1000 |
| B4_xgboost_horizon | B2_velocity | ipcw_ece | -0.0075 [-0.0114, 0.0009] | 1000 |
| B4_xgboost_horizon | B2_velocity | average_precision | 0.3613 [0.3411, 0.3832] | 1000 |

## Test results: G3

| Model | IPCW AUC | IPCW Brier | IPCW ECE | IPCW average precision |
|---|---:|---:|---:|---:|
| B0_prevalence | 0.5000 [0.5000, 0.5000] | 0.1327 [0.1279, 0.1373] | 0.0345 [0.0271, 0.0422] | 0.1558 [0.1480, 0.1632] |
| B1_single_threshold | 0.5238 [0.5175, 0.5295] | 0.1291 [0.1242, 0.1339] | 0.0308 [0.0236, 0.0386] | 0.1904 [0.1797, 0.2006] |
| B2_velocity | 0.4952 [0.4854, 0.5051] | 0.1327 [0.1279, 0.1374] | 0.0480 [0.0431, 0.0546] | 0.1636 [0.1548, 0.1732] |
| B3_regularized_logistic_horizon | 0.7557 [0.7420, 0.7689] | 0.1110 [0.1068, 0.1150] | 0.0482 [0.0432, 0.0557] | 0.4695 [0.4468, 0.4923] |
| B4_xgboost_horizon | 0.7907 [0.7782, 0.8036] | 0.1008 [0.0966, 0.1049] | 0.0478 [0.0440, 0.0556] | 0.5508 [0.5293, 0.5708] |

### Paired learned-model differences versus B0/B1/B2

| Model | Comparator | Metric | Difference [95% patient-cluster CI] | Valid resamples |
|---|---|---|---:|---:|
| B3_regularized_logistic_horizon | B0_prevalence | auc | 0.2557 [0.2420, 0.2689] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | brier | -0.0216 [-0.0245, -0.0187] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | ipcw_ece | 0.0137 [0.0108, 0.0207] | 1000 |
| B3_regularized_logistic_horizon | B0_prevalence | average_precision | 0.3138 [0.2944, 0.3348] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | auc | 0.2319 [0.2184, 0.2454] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | brier | -0.0181 [-0.0208, -0.0152] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | ipcw_ece | 0.0174 [0.0145, 0.0244] | 1000 |
| B3_regularized_logistic_horizon | B1_single_threshold | average_precision | 0.2791 [0.2595, 0.2970] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | auc | 0.2605 [0.2445, 0.2754] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | brier | -0.0217 [-0.0244, -0.0189] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | ipcw_ece | 0.0002 [-0.0051, 0.0073] | 1000 |
| B3_regularized_logistic_horizon | B2_velocity | average_precision | 0.3059 [0.2870, 0.3249] | 1000 |
| B4_xgboost_horizon | B0_prevalence | auc | 0.2907 [0.2782, 0.3036] | 1000 |
| B4_xgboost_horizon | B0_prevalence | brier | -0.0319 [-0.0347, -0.0288] | 1000 |
| B4_xgboost_horizon | B0_prevalence | ipcw_ece | 0.0132 [0.0092, 0.0219] | 1000 |
| B4_xgboost_horizon | B0_prevalence | average_precision | 0.3950 [0.3757, 0.4134] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | auc | 0.2669 [0.2534, 0.2798] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | brier | -0.0283 [-0.0312, -0.0254] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | ipcw_ece | 0.0170 [0.0131, 0.0254] | 1000 |
| B4_xgboost_horizon | B1_single_threshold | average_precision | 0.3603 [0.3410, 0.3781] | 1000 |
| B4_xgboost_horizon | B2_velocity | auc | 0.2955 [0.2800, 0.3113] | 1000 |
| B4_xgboost_horizon | B2_velocity | brier | -0.0319 [-0.0347, -0.0289] | 1000 |
| B4_xgboost_horizon | B2_velocity | ipcw_ece | -0.0002 [-0.0052, 0.0073] | 1000 |
| B4_xgboost_horizon | B2_velocity | average_precision | 0.3871 [0.3678, 0.4045] | 1000 |

## Integrity checks and scope

- Shuffled-label AUC canaries: B0_prevalence=0.5000; B1_single_threshold=0.5016; B2_velocity=0.5038; B3_regularized_logistic_horizon=0.4893; B4_xgboost_horizon=0.5036.
- The unobserved CA 15-3 canary found 6241 masked values in training observations.
- Test patients are namespaced by split, generator, and replicate. Test metrics are generated by `run.py` and retain each test replicate in `results.json`.
- Evaluation is for the simulator's observed recurrence outcome. Partial verification, new real sites/laboratories, clinical benefit, and real cohort calibration remain unvalidated.
- A synthetic G3 result is a stress test of these simulator assumptions, not evidence of transport to a clinical population.

Reproduce with `make reproduce-ml-core-complete-rerun`. Machine-readable results: [`results.json`](results.json). Frozen test access: [`data/audit/frozen_test_access.jsonl`](../../data/audit/frozen_test_access.jsonl).
