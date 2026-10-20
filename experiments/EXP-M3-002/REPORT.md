# EXP-M3-002: M3 synthetic-assumption sensitivity audit

> Synthetic robustness only. This study does not select parameters, validate clinical performance, or establish a patient-level probability.

Protocol: `1.0`  
Source commit: `f2006aa2c702b5ecdc2ebc5da1f61a35ec7ded59`  
Input strata: 9  
Configurations: 23

M3 scores are conditional on synthetic assumptions. Descriptive AUROCs compare those scores with simulator labels whose semantics do not equal M3's components; they are not performance evidence.

## Input eligibility and exclusions

| Generator | Seed | Eligible evaluations | Unobserved | Missing values | Nonfinite values | Nonpositive values | Nonfinite days |
|---|---:|---:|---:|---:|---:|---:|---:|
| G1 | 20261024 | 704 | 502 | 0 | 0 | 0 | 0 |
| G1 | 20261025 | 706 | 549 | 0 | 0 | 0 | 0 |
| G1 | 20261026 | 798 | 446 | 0 | 0 | 0 | 0 |
| G2 | 20261024 | 694 | 67 | 0 | 0 | 0 | 0 |
| G2 | 20261025 | 658 | 106 | 0 | 0 | 0 | 0 |
| G2 | 20261026 | 739 | 101 | 0 | 0 | 0 | 0 |
| G3 | 20261024 | 965 | 171 | 0 | 0 | 0 | 0 |
| G3 | 20261025 | 975 | 175 | 0 | 0 | 0 | 0 |
| G3 | 20261026 | 926 | 162 | 0 | 0 | 0 | 0 |

## Paired sensitivity by stratum

| Configuration | Generator | Seed | Evaluations | Invalid | Abstentions | Median absolute score delta | P95 absolute score delta | Action switch rate | AUROC vs recurrence label* | AUROC vs injected-error label* | Action counts |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `m3_synthetic_contract_v1` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6128 | 0.9434 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `m3_synthetic_contract_v1` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6105 | 0.9292 | abstain=0, escalate=46, explained=612, needs_repeat=48 |
| `m3_synthetic_contract_v1` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6479 | 0.9760 | abstain=0, escalate=44, explained=681, needs_repeat=73 |
| `m3_synthetic_contract_v1` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `m3_synthetic_contract_v1` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `m3_synthetic_contract_v1` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `m3_synthetic_contract_v1` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8735 | 0.9375 | abstain=0, escalate=95, explained=780, needs_repeat=90 |
| `m3_synthetic_contract_v1` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8319 | 0.9478 | abstain=0, escalate=82, explained=800, needs_repeat=93 |
| `m3_synthetic_contract_v1` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8575 | 0.9405 | abstain=0, escalate=86, explained=764, needs_repeat=76 |
| `error_prior_0_01` | G1 | 20261024 | 704 | 0 | 0 | 0.001556 | 0.009177 | 0.0000 | 0.6248 | 0.9434 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `error_prior_0_01` | G1 | 20261025 | 706 | 0 | 0 | 0.001625 | 0.008074 | 0.0057 | 0.6203 | 0.9291 | abstain=0, escalate=50, explained=612, needs_repeat=44 |
| `error_prior_0_01` | G1 | 20261026 | 798 | 0 | 0 | 0.001580 | 0.009547 | 0.0063 | 0.6623 | 0.9759 | abstain=0, escalate=47, explained=683, needs_repeat=68 |
| `error_prior_0_01` | G2 | 20261024 | 694 | 0 | 0 | 0.001600 | 0.003100 | 0.0029 | 0.2663 | 0.9405 | abstain=0, escalate=18, explained=651, needs_repeat=25 |
| `error_prior_0_01` | G2 | 20261025 | 658 | 0 | 0 | 0.001551 | 0.003160 | 0.0076 | 0.3415 | 0.9589 | abstain=0, escalate=21, explained=608, needs_repeat=29 |
| `error_prior_0_01` | G2 | 20261026 | 739 | 0 | 0 | 0.001629 | 0.003536 | 0.0054 | 0.1555 | 0.9848 | abstain=0, escalate=23, explained=690, needs_repeat=26 |
| `error_prior_0_01` | G3 | 20261024 | 965 | 0 | 0 | 0.001620 | 0.017273 | 0.0124 | 0.8917 | 0.9374 | abstain=0, escalate=104, explained=783, needs_repeat=78 |
| `error_prior_0_01` | G3 | 20261025 | 975 | 0 | 0 | 0.001665 | 0.014994 | 0.0113 | 0.8506 | 0.9477 | abstain=0, escalate=86, explained=807, needs_repeat=82 |
| `error_prior_0_01` | G3 | 20261026 | 926 | 0 | 0 | 0.001692 | 0.016839 | 0.0119 | 0.8714 | 0.9405 | abstain=0, escalate=94, explained=767, needs_repeat=65 |
| `error_prior_0_10` | G1 | 20261024 | 704 | 0 | 0 | 0.006003 | 0.030481 | 0.0071 | 0.5957 | 0.9437 | abstain=0, escalate=49, explained=583, needs_repeat=72 |
| `error_prior_0_10` | G1 | 20261025 | 706 | 0 | 0 | 0.006341 | 0.024591 | 0.0028 | 0.5942 | 0.9293 | abstain=0, escalate=44, explained=612, needs_repeat=50 |
| `error_prior_0_10` | G1 | 20261026 | 798 | 0 | 0 | 0.006150 | 0.028509 | 0.0075 | 0.6290 | 0.9762 | abstain=0, escalate=44, explained=675, needs_repeat=79 |
| `error_prior_0_10` | G2 | 20261024 | 694 | 0 | 0 | 0.006262 | 0.012060 | 0.0029 | 0.2665 | 0.9402 | abstain=0, escalate=18, explained=647, needs_repeat=29 |
| `error_prior_0_10` | G2 | 20261025 | 658 | 0 | 0 | 0.006041 | 0.011699 | 0.0015 | 0.3419 | 0.9561 | abstain=0, escalate=21, explained=602, needs_repeat=35 |
| `error_prior_0_10` | G2 | 20261026 | 739 | 0 | 0 | 0.006378 | 0.013570 | 0.0027 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=686, needs_repeat=32 |
| `error_prior_0_10` | G3 | 20261024 | 965 | 0 | 0 | 0.006256 | 0.051709 | 0.0145 | 0.8470 | 0.9377 | abstain=0, escalate=87, explained=774, needs_repeat=104 |
| `error_prior_0_10` | G3 | 20261025 | 975 | 0 | 0 | 0.006460 | 0.046762 | 0.0123 | 0.7933 | 0.9480 | abstain=0, escalate=75, explained=795, needs_repeat=105 |
| `error_prior_0_10` | G3 | 20261026 | 926 | 0 | 0 | 0.006570 | 0.051158 | 0.0205 | 0.8395 | 0.9406 | abstain=0, escalate=78, explained=753, needs_repeat=95 |
| `real_prior_0_10` | G1 | 20261024 | 704 | 0 | 0 | 0.000361 | 0.017110 | 0.0071 | 0.6140 | 0.9425 | abstain=0, escalate=48, explained=590, needs_repeat=66 |
| `real_prior_0_10` | G1 | 20261025 | 706 | 0 | 0 | 0.000352 | 0.014444 | 0.0014 | 0.6111 | 0.9288 | abstain=0, escalate=45, explained=612, needs_repeat=49 |
| `real_prior_0_10` | G1 | 20261026 | 798 | 0 | 0 | 0.000362 | 0.016342 | 0.0125 | 0.6495 | 0.9745 | abstain=0, escalate=38, explained=685, needs_repeat=75 |
| `real_prior_0_10` | G2 | 20261024 | 694 | 0 | 0 | 0.000351 | 0.003622 | 0.0043 | 0.2664 | 0.9414 | abstain=0, escalate=17, explained=651, needs_repeat=26 |
| `real_prior_0_10` | G2 | 20261025 | 658 | 0 | 0 | 0.000341 | 0.003392 | 0.0061 | 0.3416 | 0.9626 | abstain=0, escalate=19, explained=605, needs_repeat=34 |
| `real_prior_0_10` | G2 | 20261026 | 739 | 0 | 0 | 0.000355 | 0.004631 | 0.0014 | 0.1555 | 0.9842 | abstain=0, escalate=21, explained=689, needs_repeat=29 |
| `real_prior_0_10` | G3 | 20261024 | 965 | 0 | 0 | 0.000361 | 0.028907 | 0.0114 | 0.8758 | 0.9359 | abstain=0, escalate=89, explained=785, needs_repeat=91 |
| `real_prior_0_10` | G3 | 20261025 | 975 | 0 | 0 | 0.000371 | 0.024843 | 0.0113 | 0.8343 | 0.9458 | abstain=0, escalate=76, explained=805, needs_repeat=94 |
| `real_prior_0_10` | G3 | 20261026 | 926 | 0 | 0 | 0.000388 | 0.027947 | 0.0076 | 0.8592 | 0.9388 | abstain=0, escalate=83, explained=768, needs_repeat=75 |
| `real_prior_0_35` | G1 | 20261024 | 704 | 0 | 0 | 0.000752 | 0.011800 | 0.0128 | 0.6106 | 0.9441 | abstain=0, escalate=51, explained=579, needs_repeat=74 |
| `real_prior_0_35` | G1 | 20261025 | 706 | 0 | 0 | 0.000735 | 0.011176 | 0.0042 | 0.6082 | 0.9293 | abstain=0, escalate=47, explained=610, needs_repeat=49 |
| `real_prior_0_35` | G1 | 20261026 | 798 | 0 | 0 | 0.000758 | 0.015328 | 0.0138 | 0.6453 | 0.9781 | abstain=0, escalate=48, explained=674, needs_repeat=76 |
| `real_prior_0_35` | G2 | 20261024 | 694 | 0 | 0 | 0.000733 | 0.007152 | 0.0029 | 0.2665 | 0.9274 | abstain=0, escalate=18, explained=647, needs_repeat=29 |
| `real_prior_0_35` | G2 | 20261025 | 658 | 0 | 0 | 0.000711 | 0.006554 | 0.0030 | 0.3416 | 0.9326 | abstain=0, escalate=21, explained=601, needs_repeat=36 |
| `real_prior_0_35` | G2 | 20261026 | 739 | 0 | 0 | 0.000741 | 0.008664 | 0.0014 | 0.1555 | 0.9854 | abstain=0, escalate=22, explained=688, needs_repeat=29 |
| `real_prior_0_35` | G3 | 20261024 | 965 | 0 | 0 | 0.000755 | 0.028139 | 0.0176 | 0.8696 | 0.9389 | abstain=0, escalate=103, explained=771, needs_repeat=91 |
| `real_prior_0_35` | G3 | 20261025 | 975 | 0 | 0 | 0.000777 | 0.025524 | 0.0103 | 0.8267 | 0.9502 | abstain=0, escalate=86, explained=794, needs_repeat=95 |
| `real_prior_0_35` | G3 | 20261026 | 926 | 0 | 0 | 0.000806 | 0.034683 | 0.0162 | 0.8547 | 0.9411 | abstain=0, escalate=91, explained=754, needs_repeat=81 |
| `real_ratio_1_2_2_0` | G1 | 20261024 | 704 | 0 | 0 | 0.005423 | 0.075157 | 0.0526 | 0.4176 | 0.9330 | abstain=0, escalate=38, explained=570, needs_repeat=96 |
| `real_ratio_1_2_2_0` | G1 | 20261025 | 706 | 0 | 0 | 0.005413 | 0.084292 | 0.0482 | 0.2598 | 0.9138 | abstain=0, escalate=29, explained=597, needs_repeat=80 |
| `real_ratio_1_2_2_0` | G1 | 20261026 | 798 | 0 | 0 | 0.005784 | 0.115586 | 0.0652 | 0.4045 | 0.9657 | abstain=0, escalate=32, explained=651, needs_repeat=115 |
| `real_ratio_1_2_2_0` | G2 | 20261024 | 694 | 0 | 0 | 0.004777 | 0.054833 | 0.0317 | 0.2237 | 0.9412 | abstain=0, escalate=11, explained=634, needs_repeat=49 |
| `real_ratio_1_2_2_0` | G2 | 20261025 | 658 | 0 | 0 | 0.004921 | 0.047244 | 0.0228 | 0.3434 | 0.9614 | abstain=0, escalate=16, explained=593, needs_repeat=49 |
| `real_ratio_1_2_2_0` | G2 | 20261026 | 739 | 0 | 0 | 0.004648 | 0.063117 | 0.0392 | 0.1614 | 0.9837 | abstain=0, escalate=14, explained=668, needs_repeat=57 |
| `real_ratio_1_2_2_0` | G3 | 20261024 | 965 | 0 | 0 | 0.005952 | 0.295975 | 0.1016 | 0.3438 | 0.9268 | abstain=0, escalate=41, explained=746, needs_repeat=178 |
| `real_ratio_1_2_2_0` | G3 | 20261025 | 975 | 0 | 0 | 0.006586 | 0.273239 | 0.0964 | 0.3297 | 0.9371 | abstain=0, escalate=35, explained=761, needs_repeat=179 |
| `real_ratio_1_2_2_0` | G3 | 20261026 | 926 | 0 | 0 | 0.006375 | 0.280475 | 0.0994 | 0.3410 | 0.9277 | abstain=0, escalate=35, explained=731, needs_repeat=160 |
| `real_ratio_1_8_4_0` | G1 | 20261024 | 704 | 0 | 0 | 0.000172 | 0.049062 | 0.0384 | 0.7653 | 0.9512 | abstain=0, escalate=60, explained=594, needs_repeat=50 |
| `real_ratio_1_8_4_0` | G1 | 20261025 | 706 | 0 | 0 | 0.000146 | 0.020802 | 0.0382 | 0.8539 | 0.9358 | abstain=0, escalate=62, explained=617, needs_repeat=27 |
| `real_ratio_1_8_4_0` | G1 | 20261026 | 798 | 0 | 0 | 0.000178 | 0.042344 | 0.0439 | 0.8497 | 0.9781 | abstain=0, escalate=51, explained=691, needs_repeat=56 |
| `real_ratio_1_8_4_0` | G2 | 20261024 | 694 | 0 | 0 | 0.000106 | 0.005414 | 0.0101 | 0.2659 | 0.9258 | abstain=0, escalate=20, explained=652, needs_repeat=22 |
| `real_ratio_1_8_4_0` | G2 | 20261025 | 658 | 0 | 0 | 0.000115 | 0.005033 | 0.0106 | 0.3384 | 0.9615 | abstain=0, escalate=20, explained=605, needs_repeat=33 |
| `real_ratio_1_8_4_0` | G2 | 20261026 | 739 | 0 | 0 | 0.000099 | 0.007010 | 0.0081 | 0.1543 | 0.9840 | abstain=0, escalate=23, explained=690, needs_repeat=26 |
| `real_ratio_1_8_4_0` | G3 | 20261024 | 965 | 0 | 0 | 0.000177 | 0.086133 | 0.0528 | 0.9633 | 0.9481 | abstain=0, escalate=132, explained=788, needs_repeat=45 |
| `real_ratio_1_8_4_0` | G3 | 20261025 | 975 | 0 | 0 | 0.000186 | 0.069532 | 0.0492 | 0.9268 | 0.9580 | abstain=0, escalate=113, explained=813, needs_repeat=49 |
| `real_ratio_1_8_4_0` | G3 | 20261026 | 926 | 0 | 0 | 0.000179 | 0.084563 | 0.0486 | 0.9464 | 0.9502 | abstain=0, escalate=112, explained=773, needs_repeat=41 |
| `population_median_12` | G1 | 20261024 | 704 | 0 | 0 | 0.000251 | 0.006700 | 0.0000 | 0.6230 | 0.9379 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `population_median_12` | G1 | 20261025 | 706 | 0 | 0 | 0.000239 | 0.007310 | 0.0071 | 0.6193 | 0.9143 | abstain=0, escalate=51, explained=612, needs_repeat=43 |
| `population_median_12` | G1 | 20261026 | 798 | 0 | 0 | 0.000235 | 0.004618 | 0.0100 | 0.6652 | 0.9799 | abstain=0, escalate=51, explained=682, needs_repeat=65 |
| `population_median_12` | G2 | 20261024 | 694 | 0 | 0 | 0.000271 | 0.001364 | 0.0014 | 0.2666 | 0.9019 | abstain=0, escalate=19, explained=649, needs_repeat=26 |
| `population_median_12` | G2 | 20261025 | 658 | 0 | 0 | 0.000249 | 0.001563 | 0.0030 | 0.3409 | 0.8901 | abstain=0, escalate=21, explained=605, needs_repeat=32 |
| `population_median_12` | G2 | 20261026 | 739 | 0 | 0 | 0.000245 | 0.001670 | 0.0027 | 0.1555 | 0.9897 | abstain=0, escalate=23, explained=688, needs_repeat=28 |
| `population_median_12` | G3 | 20261024 | 965 | 0 | 0 | 0.000284 | 0.016080 | 0.0135 | 0.9013 | 0.9437 | abstain=0, escalate=107, explained=779, needs_repeat=79 |
| `population_median_12` | G3 | 20261025 | 975 | 0 | 0 | 0.000271 | 0.011212 | 0.0092 | 0.8589 | 0.9471 | abstain=0, escalate=91, explained=800, needs_repeat=84 |
| `population_median_12` | G3 | 20261026 | 926 | 0 | 0 | 0.000279 | 0.016868 | 0.0097 | 0.8808 | 0.9294 | abstain=0, escalate=95, explained=764, needs_repeat=67 |
| `population_median_24` | G1 | 20261024 | 704 | 0 | 0 | 0.000420 | 0.002467 | 0.0000 | 0.5986 | 0.9310 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `population_median_24` | G1 | 20261025 | 706 | 0 | 0 | 0.000467 | 0.004202 | 0.0014 | 0.5916 | 0.9264 | abstain=0, escalate=45, explained=612, needs_repeat=49 |
| `population_median_24` | G1 | 20261026 | 798 | 0 | 0 | 0.000477 | 0.003068 | 0.0000 | 0.6310 | 0.9700 | abstain=0, escalate=44, explained=681, needs_repeat=73 |
| `population_median_24` | G2 | 20261024 | 694 | 0 | 0 | 0.000447 | 0.001370 | 0.0000 | 0.2665 | 0.9426 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `population_median_24` | G2 | 20261025 | 658 | 0 | 0 | 0.000477 | 0.001412 | 0.0046 | 0.3418 | 0.9628 | abstain=0, escalate=21, explained=604, needs_repeat=33 |
| `population_median_24` | G2 | 20261026 | 739 | 0 | 0 | 0.000464 | 0.001449 | 0.0000 | 0.1555 | 0.9691 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `population_median_24` | G3 | 20261024 | 965 | 0 | 0 | 0.000522 | 0.016027 | 0.0093 | 0.8520 | 0.9312 | abstain=0, escalate=88, explained=782, needs_repeat=95 |
| `population_median_24` | G3 | 20261025 | 975 | 0 | 0 | 0.000476 | 0.008616 | 0.0092 | 0.8033 | 0.9330 | abstain=0, escalate=77, explained=804, needs_repeat=94 |
| `population_median_24` | G3 | 20261026 | 926 | 0 | 0 | 0.000500 | 0.018282 | 0.0022 | 0.8421 | 0.9451 | abstain=0, escalate=84, explained=764, needs_repeat=78 |
| `population_log_sd_0_3` | G1 | 20261024 | 704 | 0 | 0 | 0.000763 | 0.008870 | 0.0156 | 0.6262 | 0.9205 | abstain=0, escalate=58, explained=586, needs_repeat=60 |
| `population_log_sd_0_3` | G1 | 20261025 | 706 | 0 | 0 | 0.000749 | 0.006844 | 0.0184 | 0.6275 | 0.9345 | abstain=0, escalate=59, explained=612, needs_repeat=35 |
| `population_log_sd_0_3` | G1 | 20261026 | 798 | 0 | 0 | 0.000694 | 0.008729 | 0.0188 | 0.6845 | 0.9772 | abstain=0, escalate=59, explained=681, needs_repeat=58 |
| `population_log_sd_0_3` | G2 | 20261024 | 694 | 0 | 0 | 0.000742 | 0.003542 | 0.0043 | 0.2666 | 0.8909 | abstain=0, escalate=21, explained=649, needs_repeat=24 |
| `population_log_sd_0_3` | G2 | 20261025 | 658 | 0 | 0 | 0.000615 | 0.003469 | 0.0046 | 0.3415 | 0.9016 | abstain=0, escalate=22, explained=605, needs_repeat=31 |
| `population_log_sd_0_3` | G2 | 20261026 | 739 | 0 | 0 | 0.000785 | 0.003921 | 0.0041 | 0.1554 | 0.9651 | abstain=0, escalate=24, explained=688, needs_repeat=27 |
| `population_log_sd_0_3` | G3 | 20261024 | 965 | 0 | 0 | 0.000794 | 0.031888 | 0.0363 | 0.9261 | 0.9245 | abstain=0, escalate=125, explained=783, needs_repeat=57 |
| `population_log_sd_0_3` | G3 | 20261025 | 975 | 0 | 0 | 0.000948 | 0.021699 | 0.0267 | 0.8893 | 0.9454 | abstain=0, escalate=105, explained=803, needs_repeat=67 |
| `population_log_sd_0_3` | G3 | 20261026 | 926 | 0 | 0 | 0.000943 | 0.026651 | 0.0367 | 0.9265 | 0.9644 | abstain=0, escalate=112, explained=768, needs_repeat=46 |
| `population_log_sd_0_9` | G1 | 20261024 | 704 | 0 | 0 | 0.000525 | 0.003671 | 0.0000 | 0.5901 | 0.9453 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `population_log_sd_0_9` | G1 | 20261025 | 706 | 0 | 0 | 0.000594 | 0.003142 | 0.0014 | 0.5642 | 0.9387 | abstain=0, escalate=45, explained=612, needs_repeat=49 |
| `population_log_sd_0_9` | G1 | 20261026 | 798 | 0 | 0 | 0.000571 | 0.003267 | 0.0013 | 0.6207 | 0.9747 | abstain=0, escalate=44, explained=682, needs_repeat=72 |
| `population_log_sd_0_9` | G2 | 20261024 | 694 | 0 | 0 | 0.000607 | 0.001518 | 0.0014 | 0.2661 | 0.9376 | abstain=0, escalate=17, explained=649, needs_repeat=28 |
| `population_log_sd_0_9` | G2 | 20261025 | 658 | 0 | 0 | 0.000547 | 0.001409 | 0.0046 | 0.3418 | 0.9571 | abstain=0, escalate=20, explained=605, needs_repeat=33 |
| `population_log_sd_0_9` | G2 | 20261026 | 739 | 0 | 0 | 0.000618 | 0.001668 | 0.0000 | 0.1556 | 0.9850 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `population_log_sd_0_9` | G3 | 20261024 | 965 | 0 | 0 | 0.000603 | 0.009747 | 0.0083 | 0.8499 | 0.9478 | abstain=0, escalate=90, explained=779, needs_repeat=96 |
| `population_log_sd_0_9` | G3 | 20261025 | 975 | 0 | 0 | 0.000663 | 0.008066 | 0.0062 | 0.8015 | 0.9424 | abstain=0, escalate=77, explained=801, needs_repeat=97 |
| `population_log_sd_0_9` | G3 | 20261026 | 926 | 0 | 0 | 0.000692 | 0.008713 | 0.0011 | 0.8401 | 0.9312 | abstain=0, escalate=85, explained=764, needs_repeat=77 |
| `inter_lab_cv_0_00` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6128 | 0.9434 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `inter_lab_cv_0_00` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6105 | 0.9292 | abstain=0, escalate=46, explained=612, needs_repeat=48 |
| `inter_lab_cv_0_00` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6479 | 0.9760 | abstain=0, escalate=44, explained=681, needs_repeat=73 |
| `inter_lab_cv_0_00` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `inter_lab_cv_0_00` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `inter_lab_cv_0_00` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `inter_lab_cv_0_00` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8735 | 0.9375 | abstain=0, escalate=95, explained=780, needs_repeat=90 |
| `inter_lab_cv_0_00` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8319 | 0.9478 | abstain=0, escalate=82, explained=800, needs_repeat=93 |
| `inter_lab_cv_0_00` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8575 | 0.9405 | abstain=0, escalate=86, explained=764, needs_repeat=76 |
| `inter_lab_cv_0_20` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6128 | 0.9434 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `inter_lab_cv_0_20` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6105 | 0.9292 | abstain=0, escalate=46, explained=612, needs_repeat=48 |
| `inter_lab_cv_0_20` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6479 | 0.9760 | abstain=0, escalate=44, explained=681, needs_repeat=73 |
| `inter_lab_cv_0_20` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `inter_lab_cv_0_20` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `inter_lab_cv_0_20` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `inter_lab_cv_0_20` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8735 | 0.9375 | abstain=0, escalate=95, explained=780, needs_repeat=90 |
| `inter_lab_cv_0_20` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8319 | 0.9478 | abstain=0, escalate=82, explained=800, needs_repeat=93 |
| `inter_lab_cv_0_20` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8575 | 0.9405 | abstain=0, escalate=86, explained=764, needs_repeat=76 |
| `decimal_shift_5` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0028 | 0.5151 | 0.9418 | abstain=0, escalate=48, explained=587, needs_repeat=69 |
| `decimal_shift_5` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0042 | 0.4319 | 0.9282 | abstain=0, escalate=43, explained=612, needs_repeat=51 |
| `decimal_shift_5` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0038 | 0.5524 | 0.9756 | abstain=0, escalate=41, explained=681, needs_repeat=76 |
| `decimal_shift_5` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0029 | 0.2648 | 0.9400 | abstain=0, escalate=16, explained=649, needs_repeat=29 |
| `decimal_shift_5` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0015 | 0.3416 | 0.9583 | abstain=0, escalate=20, explained=603, needs_repeat=35 |
| `decimal_shift_5` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0054 | 0.1538 | 0.9847 | abstain=0, escalate=17, explained=688, needs_repeat=34 |
| `decimal_shift_5` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.001137 | 0.0114 | 0.7822 | 0.9367 | abstain=0, escalate=84, explained=780, needs_repeat=101 |
| `decimal_shift_5` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000105 | 0.0103 | 0.7103 | 0.9465 | abstain=0, escalate=72, explained=800, needs_repeat=103 |
| `decimal_shift_5` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000207 | 0.0119 | 0.7860 | 0.9390 | abstain=0, escalate=75, explained=764, needs_repeat=87 |
| `decimal_shift_20` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6167 | 0.9436 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `decimal_shift_20` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6142 | 0.9292 | abstain=0, escalate=46, explained=612, needs_repeat=48 |
| `decimal_shift_20` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6508 | 0.9762 | abstain=0, escalate=44, explained=681, needs_repeat=73 |
| `decimal_shift_20` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2646 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `decimal_shift_20` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3407 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `decimal_shift_20` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1534 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `decimal_shift_20` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8735 | 0.9375 | abstain=0, escalate=95, explained=780, needs_repeat=90 |
| `decimal_shift_20` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8322 | 0.9478 | abstain=0, escalate=82, explained=800, needs_repeat=93 |
| `decimal_shift_20` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8577 | 0.9405 | abstain=0, escalate=86, explained=764, needs_repeat=76 |
| `population_error_heavy` | G1 | 20261024 | 704 | 0 | 0 | 0.001807 | 0.010641 | 0.0028 | 0.6078 | 0.9436 | abstain=0, escalate=49, explained=586, needs_repeat=69 |
| `population_error_heavy` | G1 | 20261025 | 706 | 0 | 0 | 0.001908 | 0.008662 | 0.0014 | 0.6053 | 0.9292 | abstain=0, escalate=45, explained=612, needs_repeat=49 |
| `population_error_heavy` | G1 | 20261026 | 798 | 0 | 0 | 0.001856 | 0.008549 | 0.0000 | 0.6421 | 0.9760 | abstain=0, escalate=44, explained=681, needs_repeat=73 |
| `population_error_heavy` | G2 | 20261024 | 694 | 0 | 0 | 0.001877 | 0.003465 | 0.0000 | 0.2665 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `population_error_heavy` | G2 | 20261025 | 658 | 0 | 0 | 0.001813 | 0.003506 | 0.0015 | 0.3417 | 0.9584 | abstain=0, escalate=21, explained=602, needs_repeat=35 |
| `population_error_heavy` | G2 | 20261026 | 739 | 0 | 0 | 0.001916 | 0.004094 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `population_error_heavy` | G3 | 20261024 | 965 | 0 | 0 | 0.001894 | 0.018678 | 0.0062 | 0.8621 | 0.9375 | abstain=0, escalate=91, explained=778, needs_repeat=96 |
| `population_error_heavy` | G3 | 20261025 | 975 | 0 | 0 | 0.001951 | 0.015440 | 0.0051 | 0.8160 | 0.9478 | abstain=0, escalate=77, explained=800, needs_repeat=98 |
| `population_error_heavy` | G3 | 20261026 | 926 | 0 | 0 | 0.001981 | 0.018312 | 0.0065 | 0.8499 | 0.9405 | abstain=0, escalate=84, explained=760, needs_repeat=82 |
| `decimal_error_heavy` | G1 | 20261024 | 704 | 0 | 0 | 0.000917 | 0.005408 | 0.0000 | 0.6160 | 0.9434 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `decimal_error_heavy` | G1 | 20261025 | 706 | 0 | 0 | 0.000959 | 0.004832 | 0.0014 | 0.6124 | 0.9292 | abstain=0, escalate=47, explained=612, needs_repeat=47 |
| `decimal_error_heavy` | G1 | 20261026 | 798 | 0 | 0 | 0.000932 | 0.004563 | 0.0038 | 0.6526 | 0.9760 | abstain=0, escalate=46, explained=682, needs_repeat=70 |
| `decimal_error_heavy` | G2 | 20261024 | 694 | 0 | 0 | 0.000941 | 0.001741 | 0.0014 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=650, needs_repeat=26 |
| `decimal_error_heavy` | G2 | 20261025 | 658 | 0 | 0 | 0.000912 | 0.001776 | 0.0046 | 0.3415 | 0.9584 | abstain=0, escalate=21, explained=606, needs_repeat=31 |
| `decimal_error_heavy` | G2 | 20261026 | 739 | 0 | 0 | 0.000961 | 0.002074 | 0.0027 | 0.1555 | 0.9848 | abstain=0, escalate=22, explained=689, needs_repeat=28 |
| `decimal_error_heavy` | G3 | 20261024 | 965 | 0 | 0 | 0.000951 | 0.009976 | 0.0062 | 0.8827 | 0.9375 | abstain=0, escalate=98, explained=783, needs_repeat=84 |
| `decimal_error_heavy` | G3 | 20261025 | 975 | 0 | 0 | 0.000983 | 0.008462 | 0.0051 | 0.8416 | 0.9478 | abstain=0, escalate=84, explained=803, needs_repeat=88 |
| `decimal_error_heavy` | G3 | 20261026 | 926 | 0 | 0 | 0.000999 | 0.009879 | 0.0032 | 0.8638 | 0.9405 | abstain=0, escalate=89, explained=764, needs_repeat=73 |
| `error_action_threshold_0_20` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6128 | 0.9434 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `error_action_threshold_0_20` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0014 | 0.6105 | 0.9292 | abstain=0, escalate=45, explained=612, needs_repeat=49 |
| `error_action_threshold_0_20` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6479 | 0.9760 | abstain=0, escalate=44, explained=681, needs_repeat=73 |
| `error_action_threshold_0_20` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `error_action_threshold_0_20` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `error_action_threshold_0_20` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `error_action_threshold_0_20` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0031 | 0.8735 | 0.9375 | abstain=0, escalate=92, explained=780, needs_repeat=93 |
| `error_action_threshold_0_20` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0051 | 0.8319 | 0.9478 | abstain=0, escalate=77, explained=800, needs_repeat=98 |
| `error_action_threshold_0_20` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0022 | 0.8575 | 0.9405 | abstain=0, escalate=84, explained=764, needs_repeat=78 |
| `error_action_threshold_0_40` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6128 | 0.9434 | abstain=0, escalate=50, explained=587, needs_repeat=67 |
| `error_action_threshold_0_40` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0014 | 0.6105 | 0.9292 | abstain=0, escalate=47, explained=612, needs_repeat=47 |
| `error_action_threshold_0_40` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0025 | 0.6479 | 0.9760 | abstain=0, escalate=46, explained=681, needs_repeat=71 |
| `error_action_threshold_0_40` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `error_action_threshold_0_40` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `error_action_threshold_0_40` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0014 | 0.1555 | 0.9848 | abstain=0, escalate=22, explained=688, needs_repeat=29 |
| `error_action_threshold_0_40` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0010 | 0.8735 | 0.9375 | abstain=0, escalate=96, explained=780, needs_repeat=89 |
| `error_action_threshold_0_40` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0021 | 0.8319 | 0.9478 | abstain=0, escalate=84, explained=800, needs_repeat=91 |
| `error_action_threshold_0_40` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0022 | 0.8575 | 0.9405 | abstain=0, escalate=88, explained=764, needs_repeat=74 |
| `real_action_threshold_0_50` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0014 | 0.6128 | 0.9434 | abstain=0, escalate=51, explained=587, needs_repeat=66 |
| `real_action_threshold_0_50` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6105 | 0.9292 | abstain=0, escalate=46, explained=612, needs_repeat=48 |
| `real_action_threshold_0_50` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0013 | 0.6479 | 0.9760 | abstain=0, escalate=45, explained=681, needs_repeat=72 |
| `real_action_threshold_0_50` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `real_action_threshold_0_50` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `real_action_threshold_0_50` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `real_action_threshold_0_50` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0021 | 0.8735 | 0.9375 | abstain=0, escalate=97, explained=780, needs_repeat=88 |
| `real_action_threshold_0_50` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0021 | 0.8319 | 0.9478 | abstain=0, escalate=84, explained=800, needs_repeat=91 |
| `real_action_threshold_0_50` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0011 | 0.8575 | 0.9405 | abstain=0, escalate=87, explained=764, needs_repeat=75 |
| `real_action_threshold_0_70` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0028 | 0.6128 | 0.9434 | abstain=0, escalate=48, explained=587, needs_repeat=69 |
| `real_action_threshold_0_70` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6105 | 0.9292 | abstain=0, escalate=46, explained=612, needs_repeat=48 |
| `real_action_threshold_0_70` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0025 | 0.6479 | 0.9760 | abstain=0, escalate=42, explained=681, needs_repeat=75 |
| `real_action_threshold_0_70` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=649, needs_repeat=27 |
| `real_action_threshold_0_70` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=603, needs_repeat=34 |
| `real_action_threshold_0_70` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `real_action_threshold_0_70` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8735 | 0.9375 | abstain=0, escalate=95, explained=780, needs_repeat=90 |
| `real_action_threshold_0_70` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8319 | 0.9478 | abstain=0, escalate=82, explained=800, needs_repeat=93 |
| `real_action_threshold_0_70` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.8575 | 0.9405 | abstain=0, escalate=86, explained=764, needs_repeat=76 |
| `stable_action_threshold_0_85` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0028 | 0.6128 | 0.9434 | abstain=0, escalate=50, explained=589, needs_repeat=65 |
| `stable_action_threshold_0_85` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.6105 | 0.9292 | abstain=0, escalate=46, explained=612, needs_repeat=48 |
| `stable_action_threshold_0_85` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0025 | 0.6479 | 0.9760 | abstain=0, escalate=44, explained=683, needs_repeat=71 |
| `stable_action_threshold_0_85` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0029 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=651, needs_repeat=25 |
| `stable_action_threshold_0_85` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0046 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=606, needs_repeat=31 |
| `stable_action_threshold_0_85` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0014 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=689, needs_repeat=29 |
| `stable_action_threshold_0_85` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0062 | 0.8735 | 0.9375 | abstain=0, escalate=95, explained=786, needs_repeat=84 |
| `stable_action_threshold_0_85` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0062 | 0.8319 | 0.9478 | abstain=0, escalate=82, explained=806, needs_repeat=87 |
| `stable_action_threshold_0_85` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0022 | 0.8575 | 0.9405 | abstain=0, escalate=86, explained=766, needs_repeat=74 |
| `stable_action_threshold_0_95` | G1 | 20261024 | 704 | 0 | 0 | 0.000000 | 0.000000 | 0.0114 | 0.6128 | 0.9434 | abstain=0, escalate=50, explained=579, needs_repeat=75 |
| `stable_action_threshold_0_95` | G1 | 20261025 | 706 | 0 | 0 | 0.000000 | 0.000000 | 0.0028 | 0.6105 | 0.9292 | abstain=0, escalate=46, explained=610, needs_repeat=50 |
| `stable_action_threshold_0_95` | G1 | 20261026 | 798 | 0 | 0 | 0.000000 | 0.000000 | 0.0088 | 0.6479 | 0.9760 | abstain=0, escalate=44, explained=674, needs_repeat=80 |
| `stable_action_threshold_0_95` | G2 | 20261024 | 694 | 0 | 0 | 0.000000 | 0.000000 | 0.0043 | 0.2664 | 0.9404 | abstain=0, escalate=18, explained=646, needs_repeat=30 |
| `stable_action_threshold_0_95` | G2 | 20261025 | 658 | 0 | 0 | 0.000000 | 0.000000 | 0.0030 | 0.3416 | 0.9584 | abstain=0, escalate=21, explained=601, needs_repeat=36 |
| `stable_action_threshold_0_95` | G2 | 20261026 | 739 | 0 | 0 | 0.000000 | 0.000000 | 0.0000 | 0.1555 | 0.9848 | abstain=0, escalate=21, explained=688, needs_repeat=30 |
| `stable_action_threshold_0_95` | G3 | 20261024 | 965 | 0 | 0 | 0.000000 | 0.000000 | 0.0104 | 0.8735 | 0.9375 | abstain=0, escalate=95, explained=770, needs_repeat=100 |
| `stable_action_threshold_0_95` | G3 | 20261025 | 975 | 0 | 0 | 0.000000 | 0.000000 | 0.0072 | 0.8319 | 0.9478 | abstain=0, escalate=82, explained=793, needs_repeat=100 |
| `stable_action_threshold_0_95` | G3 | 20261026 | 926 | 0 | 0 | 0.000000 | 0.000000 | 0.0140 | 0.8575 | 0.9405 | abstain=0, escalate=86, explained=751, needs_repeat=89 |

\* Descriptive synthetic-label comparisons only; no patient-level confidence intervals or clinical interpretation are registered.

## Integrity

Each stratum records separate hashes for model inputs and analysis-only labels. Every configuration uses the same input hashes. Source, simulator, config, preregistration, runner, renderer, lockfile, and repository revision hashes are in `ACCESS_LOG.json`.

No configuration is ranked or selected. These results do not establish clinical plausibility for any assumption setting; M3 remains research-only.
