# EXP-K4-001 report (study S4): deep irregular-time models, pre-training and scale

> **SYNTHETIC DATA ONLY.** Nothing here is evidence about real patients. Every number below was written by `experiments/EXP-K4-001/run.py` from `results.json`; the design is `PREREG.md` (with its amendments).

Replications: 10 (0 to 9); base seed 20261201; run time 1480 s on 8 workers (machine-dependent); code hash `8af5136e5e3339ea`.

## 1. Verdicts (pre-registered primary family, Bonferroni level 0.9833)

| Hypothesis | Quantity | Estimate | Interval | Rule | Verdict |
|---|---|---|---|---|---|
| H1 pre-training helps (N=100, medium, mean of 3 families) | AUC(PT-all) - AUC(scratch) | -0.0201 | [-0.0300, -0.0082] | lower > 0.01 | **NOT MET** |
| H2 `gru_ode_bayes` beats every classical baseline (N=1000) | weakest margin vs `B4_GradientBoosting` | -0.0064 | [-0.0181, 0.0062] | every lower bound > 0 | **NOT MET** |
| H3 scale helps (N=1000, large vs medium) | AUC(large) - AUC(medium) | -0.0041 | [-0.0108, 0.0024] | helps if lower > 0.005; does not help if upper < 0.005 | **SCALE DOES NOT HELP** |

Consequences by the pre-registered kill rules: **no pre-training is claimed or shipped; no pre-trained checkpoint is exported or registered**; **K4 is not claimed to beat classical models and stays outside every production ensemble**; **medium is the largest size anyone is told to use**.

### H2 detail (designated family chosen on development replications: `gru_ode_bayes`)

| Baseline | AUC difference (designated minus baseline) | Interval | Beats |
|---|---|---|---|
| `B1_SingleThreshold` | 0.1460 | [0.1287, 0.1607] | yes |
| `B2_Velocity` | 0.2361 | [0.2216, 0.2484] | yes |
| `B3_RegularizedHazard` | 0.0292 | [0.0171, 0.0399] | yes |
| `B4_GradientBoosting` | -0.0064 | [-0.0181, 0.0062] | no |
| `K3_JointModel` | 0.0014 | [-0.0111, 0.0139] | no |

## 2. Leakage canary

GRU-D, medium, N=1000, 20 label permutations per replication (all training rows, amendments A1 and A3), true test labels: mean G1 AUC **0.4479** over 200 fits (standard deviation of one fit 0.1105). Rule (amendment A3c): VOID only if the mean is above 0.55, because leakage can only raise the AUC -> **passes**. The mean is below 0.45: this is not a leakage signal and is reported as observed (see amendment A3c); a model fitted to permuted labels is not centred on 0.5.

## 3. Strongest classical baseline first (G1 test, IPCW AUC at 365 days, mean over replications)

| N | Strongest baseline | AUC | B1_SingleThreshold | B2_Velocity | B3_RegularizedHazard | B4_GradientBoosting | K3_JointModel |
|---|---|---|---|---|---|---|---|
| 50 | `K3_JointModel` | 0.7664 | 0.6405 | 0.5503 | 0.7144 | 0.7330 | 0.7664 |
| 100 | `K3_JointModel` | 0.7785 | 0.6405 | 0.5503 | 0.7340 | 0.7522 | 0.7785 |
| 200 | `K3_JointModel` | 0.7805 | 0.6405 | 0.5503 | 0.7400 | 0.7696 | 0.7805 |
| 500 | `K3_JointModel` | 0.7829 | 0.6405 | 0.5503 | 0.7497 | 0.7819 | 0.7829 |
| 1000 | `B4_GradientBoosting` | 0.7928 | 0.6405 | 0.5503 | 0.7572 | 0.7928 | 0.7850 |

## 4. Zoo: six families, medium, trained from scratch (G1 AUC mean [95% interval over replications])

| Family | N=50 | N=100 | N=200 | N=500 | N=1000 |
|---|---|---|---|---|---|
| `grud` | 0.727 [0.707, 0.749] | 0.739 [0.720, 0.758] | 0.754 [0.740, 0.767] | 0.767 [0.759, 0.776] | 0.782 [0.771, 0.792] |
| `gru_ode_bayes` | 0.735 [0.716, 0.753] | 0.739 [0.726, 0.752] | 0.745 [0.728, 0.760] | 0.768 [0.754, 0.782] | 0.786 [0.775, 0.798] |
| `neural_cde` | 0.649 [0.625, 0.675] | 0.655 [0.634, 0.679] | 0.698 [0.675, 0.721] | 0.740 [0.727, 0.751] | 0.761 [0.745, 0.780] |
| `ct_transformer` | 0.734 [0.721, 0.749] | 0.736 [0.708, 0.761] | 0.743 [0.733, 0.752] | 0.754 [0.746, 0.762] | 0.772 [0.762, 0.781] |
| `gruwe` | 0.676 [0.610, 0.724] | 0.742 [0.727, 0.757] | 0.750 [0.732, 0.765] | 0.767 [0.759, 0.774] | 0.776 [0.768, 0.784] |
| `ssm` | 0.743 [0.728, 0.762] | 0.751 [0.737, 0.764] | 0.750 [0.741, 0.761] | 0.760 [0.752, 0.767] | 0.771 [0.760, 0.784] |

Ranking at N=1000: `gru_ode_bayes` 0.786, `grud` 0.782, `gruwe` 0.776, `ct_transformer` 0.772, `ssm` 0.771, `neural_cde` 0.761.

Smallest N at which a family (scratch, medium) reaches the strongest baseline's mean AUC at that N: `grud`: never, `gru_ode_bayes`: never, `neural_cde`: never, `ct_transformer`: never, `gruwe`: never, `ssm`: never.

## 5. Pre-training (descriptive except H1): mean over the F3 families of AUC(arm) - AUC(scratch), medium

| Arm | N=50 | N=100 | N=200 | N=500 | N=1000 |
|---|---|---|---|---|---|
| `pt_all` | -0.021 [-0.029, -0.013] | -0.020 [-0.028, -0.010] | -0.014 [-0.019, -0.008] | -0.010 [-0.016, -0.003] | -0.014 [-0.022, -0.006] |
| `pt_offgen` | -0.013 [-0.025, -0.002] | -0.015 [-0.023, -0.005] | -0.009 [-0.012, -0.005] | -0.009 [-0.015, -0.002] | -0.010 [-0.015, -0.005] |
| `pt_shuffled` | -0.029 [-0.051, -0.011] | -0.015 [-0.036, 0.001] | -0.003 [-0.009, 0.004] | -0.003 [-0.008, 0.002] | 0.001 [-0.001, 0.004] |

Masked-loss on 10% held-out corpus patients (mean over replications):

| Family | Size | Corpus | Initial loss | Final loss |
|---|---|---|---|---|
| `ct_transformer` | large | `pt_all` | 0.3158 | 0.0473 |
| `ct_transformer` | medium | `pt_all` | 0.3261 | 0.0488 |
| `ct_transformer` | medium | `pt_offgen` | 0.2801 | 0.0449 |
| `ct_transformer` | medium | `pt_shuffled` | 0.3225 | 0.1713 |
| `ct_transformer` | small | `pt_all` | 0.3249 | 0.0533 |
| `grud` | large | `pt_all` | 0.1836 | 0.0467 |
| `grud` | medium | `pt_all` | 0.1894 | 0.0482 |
| `grud` | medium | `pt_offgen` | 0.1458 | 0.0447 |
| `grud` | medium | `pt_shuffled` | 0.1912 | 0.1717 |
| `grud` | small | `pt_all` | 0.2027 | 0.0506 |
| `ssm` | large | `pt_all` | 0.3244 | 0.0485 |
| `ssm` | medium | `pt_all` | 0.3471 | 0.0513 |
| `ssm` | medium | `pt_offgen` | 0.3043 | 0.0466 |
| `ssm` | medium | `pt_shuffled` | 0.3507 | 0.1697 |
| `ssm` | small | `pt_all` | 0.3534 | 0.0548 |

## 6. Scale (G1 AUC mean over replications, F3 families)

| Family | Arm | Size | N=100 | N=1000 |
|---|---|---|---|---|
| `grud` | scratch | small | 0.739 | 0.790 |
| `grud` | scratch | medium | 0.739 | 0.782 |
| `grud` | scratch | large | 0.739 | 0.779 |
| `grud` | pt_all | small | 0.723 | 0.778 |
| `grud` | pt_all | medium | 0.711 | 0.777 |
| `grud` | pt_all | large | 0.700 | 0.777 |
| `ct_transformer` | scratch | small | 0.737 | 0.760 |
| `ct_transformer` | scratch | medium | 0.736 | 0.772 |
| `ct_transformer` | scratch | large | 0.735 | 0.766 |
| `ct_transformer` | pt_all | small | 0.717 | 0.751 |
| `ct_transformer` | pt_all | medium | 0.722 | 0.741 |
| `ct_transformer` | pt_all | large | 0.721 | 0.741 |
| `ssm` | scratch | small | 0.744 | 0.766 |
| `ssm` | scratch | medium | 0.751 | 0.771 |
| `ssm` | scratch | large | 0.744 | 0.767 |
| `ssm` | pt_all | small | 0.728 | 0.769 |
| `ssm` | pt_all | medium | 0.732 | 0.766 |
| `ssm` | pt_all | large | 0.732 | 0.776 |

Medium minus small (scratch, N=1000, F3 mean): 0.0031 [-0.0039, 0.0109] (95%, descriptive).

## 7. Cross-generator tests (trained on G1 labels only; AUC mean, medium, scratch)

| Model | N | G1 AUC | G2 AUC | G3 AUC | G1 ECE | G1 Brier |
|---|---|---|---|---|---|---|
| `B1_SingleThreshold` | 1000 | 0.640 | 0.655 | 0.676 | 0.077 | 0.181 |
| `B2_Velocity` | 1000 | 0.550 | 0.544 | 0.552 | 0.064 | 0.209 |
| `B3_RegularizedHazard` | 1000 | 0.757 | 0.718 | 0.716 | 0.024 | 0.150 |
| `B4_GradientBoosting` | 1000 | 0.793 | 0.753 | 0.776 | 0.025 | 0.140 |
| `K3_JointModel` | 1000 | 0.785 | 0.762 | 0.778 | 0.025 | 0.149 |
| `grud` | 1000 | 0.782 | 0.739 | 0.746 | 0.033 | 0.146 |
| `gru_ode_bayes` | 1000 | 0.786 | 0.743 | 0.753 | 0.028 | 0.146 |
| `neural_cde` | 1000 | 0.761 | 0.713 | 0.710 | 0.026 | 0.148 |
| `ct_transformer` | 1000 | 0.772 | 0.731 | 0.715 | 0.033 | 0.149 |
| `gruwe` | 1000 | 0.776 | 0.733 | 0.742 | 0.038 | 0.149 |
| `ssm` | 1000 | 0.771 | 0.730 | 0.712 | 0.034 | 0.149 |

## 8. Cost (machine-dependent; measured on the machine that ran the study, one thread, 8 visits)

| Family | Size | Parameters | State bytes | Latency median ms | p95 ms |
|---|---|---|---|---|---|
| `ct_transformer` | small | 5731 | 22924 | 0.24 | 0.83 |
| `ct_transformer` | medium | 20149 | 80596 | 0.26 | 1.55 |
| `ct_transformer` | large | 75093 | 300372 | 0.28 | 1.33 |
| `gru_ode_bayes` | small | 4209 | 16836 | 4.42 | 17.28 |
| `gru_ode_bayes` | medium | 11985 | 47940 | 5.79 | 16.43 |
| `gru_ode_bayes` | large | 38289 | 153156 | 4.94 | 16.72 |
| `grud` | small | 3505 | 14020 | 0.71 | 2.35 |
| `grud` | medium | 9009 | 36036 | 0.70 | 1.81 |
| `grud` | large | 26161 | 104644 | 0.70 | 2.85 |
| `gruwe` | small | 3377 | 13508 | 0.61 | 2.46 |
| `gruwe` | medium | 8785 | 35140 | 0.64 | 2.46 |
| `gruwe` | large | 25745 | 102980 | 0.69 | 2.37 |
| `neural_cde` | small | 6161 | 24644 | 0.85 | 3.89 |
| `neural_cde` | medium | 22545 | 90180 | 1.18 | 3.30 |
| `neural_cde` | large | 86033 | 344132 | 1.67 | 2.38 |
| `ssm` | small | 2929 | 11716 | 0.55 | 1.23 |
| `ssm` | medium | 7361 | 29444 | 0.56 | 1.65 |
| `ssm` | large | 20833 | 83332 | 0.58 | 1.54 |

## 9. Export checks (safetensors exact round trip and ONNX parity, replication 0, N=1000 model)

| Family | Safetensors exact | ONNX max abs difference | Sequences |
|---|---|---|---|
| `ct_transformer` | True | 5.96e-07 | 50 |
| `gru_ode_bayes` | True | 1.19e-07 | 50 |
| `grud` | True | 1.19e-07 | 50 |
| `gruwe` | True | 1.79e-07 | 50 |
| `neural_cde` | True | 1.19e-07 | 50 |
| `ssm` | True | 1.79e-07 | 50 |

## 10. Selected hyper-parameters (development replications only; `hyperparameters.json`)

| Family | Scratch lr | Fine-tune lr |
|---|---|---|
| `grud` | 0.003 | 0.001 |
| `gru_ode_bayes` | 0.003 | n/a |
| `neural_cde` | 0.001 | n/a |
| `ct_transformer` | 0.001 | 0.001 |
| `gruwe` | 0.001 | n/a |
| `ssm` | 0.001 | 0.001 |

Designated family for H2: `gru_ode_bayes`. Baseline fits that failed and fell back to a constant prediction: 0.

## 11. Not built (PREREG section 4)

TabPFN-style prior-fitted networks, the contrastive pre-training objective, the adjoint and log-signature options of Neural CDE, and the GRU-ODE-Bayes variational observation model were not built and are not approximated.

