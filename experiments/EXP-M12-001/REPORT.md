# EXP-M12-001 report (written by `run.py`; do not edit)

> **SYNTHETIC DATA ONLY.** Five simulated sites with analyser offsets, visit frequency and missingness. FederatedAveraging is in-process (no network). DP-SGD and the moments accountant are implemented in `vigil_ml.m12`. (ε, δ)-DP is not an NDPA/GDPR determination. Pre-registration: `PREREG.md`.

Replications: 10 (frozen). Mean headline ε̂ (max over sites, δ = 1/910): 45.959. Canary (σ = 100) mean pooled AUC: 0.5237. **VOID:** False. Run time 33 s.

## Hypotheses (computed)

| Hypothesis | Result | Detail |
|---|---|---|
| H1 (local silos, descriptive) | NOT met | mean 0.1096, 95pct interval [0.0621, 0.1597] ; lower bound > 0.10 would support silo failure |
| H2 (FedAvg within 3 pp of central) | NOT met | mean 0.0617, bonferroni interval [0.0067, 0.1179] ; need point and Bonferroni UB ≤ 0.03 |
| H3 (FedAvg+DP within 3 pp of central) — kill | met | mean -0.0506, bonferroni interval [-0.0994, -0.0034] ; need point and Bonferroni UB ≤ 0.03 |
| H4 (NB@0.10 drop, descriptive) | NOT met | mean 0.1187, 95pct interval [0.1035, 0.1348] ; same 0.03 rule, not in the primary family |

**Kill rule fires:** False. Fallback if it fires: federated evaluation only. Nothing here is wired into a pipeline or a pilot.

## Strongest baseline first (mean pooled IPCW AUC at 365 days)

| Arm | Mean pooled AUC |
|---|---|
| B4 gradient boosting (descriptive ceiling) | 0.8277 |
| C central MLP | 0.6602 |
| F FedAvg | 0.5985 |
| D FedAvg + DP-SGD | 0.7108 |

## Per-site mean IPCW AUC

| Site | L local | C central | F FedAvg | D FedAvg+DP |
|---|---|---|---|---|
| A | 0.6764 | 0.6534 | 0.5947 | 0.7221 |
| B | 0.6101 | 0.6899 | 0.6161 | 0.7379 |
| C | 0.5188 | 0.6446 | 0.5864 | 0.6441 |
| D | 0.5971 | 0.6662 | 0.6106 | 0.7555 |
| E | 0.5656 | 0.6591 | 0.5796 | 0.6728 |

## Drops versus central (pooled)

| Contrast | Mean | Interval |
|---|---|---|
| AUC_C − AUC_F | 0.0617 | bonferroni [0.0067, 0.1179] |
| AUC_C − AUC_D | -0.0506 | bonferroni [-0.0994, -0.0034] |
| NB_C − NB_D at 0.10 | 0.1187 | 95pct [0.1035, 0.1348] |

## Limits (carried from the pre-registration)
Synthetic data; one MLP; one-row-per-patient DP; in-process FedAvg (no Flower process); no Opacus; no real multi-site data; not a legal privacy claim; not a pilot.

