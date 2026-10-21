# EXP-K1-004 Report — canonical inference and marker transfer

> All results are synthetic. K1 recurrence-risk use is disabled; marker forecasting is not recurrence prediction.

Protocol: 1.10  
Evaluation source commit: `bbc1eded06ee9445e8a49c2a0e30324d46b45f42`  
Training source commit: `bbc1eded06ee9445e8a49c2a0e30324d46b45f42`  

## Own-world parameter inference

Per-setting/seed parameter bias, RMSE, coverage and predictive checks are recorded in `results.json`. NUTS is limited to the preregistered common 30-patient subset per setting/seed and reports chain diagnostics. The immutable acceptance-suite result is a separate gate and is not used for tuning.

## Product-simulator marker forecasting

Forecasts use measured CA 15-3 values only. The measurement flag selects rows; it is never passed as a value. No recurrence labels or latent outcome fields are read by the forecasting evaluation. G1/G2/G3 results are reported separately by seed, for all eligible patients and for the at-most-6-pre-landmark-visit subgroup, with patient-cluster bootstrap intervals.

| Stratum | Generator | Seed | Eligible patients | K1 MAE | Carry-forward MAE | Linear-trend MAE | K1 90% interval coverage |
|---|---|---:|---:|---:|---:|---:|---:|
| all_eligible | g1_smooth_kinetics | 44001 | 733 | 1795.0537 | 93.1365 | 138.0379 | 0.3092 |
| low_data_6_or_fewer_pre_landmark_visits | g1_smooth_kinetics | 44001 | 733 | 1795.0537 | 93.1365 | 138.0379 | 0.3092 |
| all_eligible | g1_smooth_kinetics | 44002 | 740 | 1592.0065 | 83.7748 | 129.7462 | 0.2887 |
| low_data_6_or_fewer_pre_landmark_visits | g1_smooth_kinetics | 44002 | 739 | 1594.1586 | 83.8618 | 129.8958 | 0.2878 |
| all_eligible | g1_smooth_kinetics | 44003 | 747 | 1546.0528 | 84.8900 | 117.9944 | 0.2809 |
| low_data_6_or_fewer_pre_landmark_visits | g1_smooth_kinetics | 44003 | 747 | 1546.0528 | 84.8900 | 117.9944 | 0.2809 |
| all_eligible | g2_shedding_bursts | 44001 | 899 | 1134.2731 | 35.1488 | 54.9829 | 0.2633 |
| low_data_6_or_fewer_pre_landmark_visits | g2_shedding_bursts | 44001 | 897 | 1136.4135 | 35.0975 | 54.9766 | 0.2633 |
| all_eligible | g2_shedding_bursts | 44002 | 910 | 1190.9534 | 33.8365 | 56.4483 | 0.2744 |
| low_data_6_or_fewer_pre_landmark_visits | g2_shedding_bursts | 44002 | 910 | 1190.9534 | 33.8365 | 56.4483 | 0.2744 |
| all_eligible | g2_shedding_bursts | 44003 | 911 | 944.2495 | 35.7581 | 55.0633 | 0.2791 |
| low_data_6_or_fewer_pre_landmark_visits | g2_shedding_bursts | 44003 | 911 | 944.2495 | 35.7581 | 55.0633 | 0.2791 |
| all_eligible | g3_heavy_tailed_noise | 45001 | 916 | 828.5091 | 36.4699 | 28.3713 | 0.3360 |
| low_data_6_or_fewer_pre_landmark_visits | g3_heavy_tailed_noise | 45001 | 915 | 829.2810 | 36.5092 | 28.4017 | 0.3364 |
| all_eligible | g3_heavy_tailed_noise | 45002 | 895 | 1061.9616 | 39.9186 | 30.4909 | 0.3645 |
| low_data_6_or_fewer_pre_landmark_visits | g3_heavy_tailed_noise | 45002 | 895 | 1061.9616 | 39.9186 | 30.4909 | 0.3645 |
| all_eligible | g3_heavy_tailed_noise | 45003 | 890 | 846.4525 | 35.7810 | 27.4174 | 0.3458 |
| low_data_6_or_fewer_pre_landmark_visits | g3_heavy_tailed_noise | 45003 | 885 | 850.3818 | 35.9678 | 27.5540 | 0.3469 |

## Limits and decision

Own-world recovery establishes behavior only under the declared synthetic likelihood. Product-world CA 15-3 forecasts test transfer of that measurement model and do not validate recurrence prediction. The simulator does not expose K1's four latent parameters, and its recurrence process is separate. K1 remains research-only; see `PROP-K1-EVENT-SEMANTICS.md` and the model card.

## Recorded outcome

The completed run's interpretation and research-only decision are in [`CONCLUSION.md`](CONCLUSION.md). The immutable K1 acceptance result was 14 passed, 1 xfailed, and 2 failed; see [`ACCEPTANCE.md`](ACCEPTANCE.md). No acceptance outcome was used for tuning.
