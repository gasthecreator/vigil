# VigilBench Phase 2 & 3: Longitudinal Surveillance & Advanced Modeling Benchmark

> **CLINICAL DISCLAIMER & SYNTHETIC DATA NOTICE:**  
> This benchmark was conducted exclusively on **SYNTHETIC DATA** (Tiers G1, G2, G3). All metrics, lead times, and calibration curves reflect synthetic cohort properties and simulator dynamics. They DO NOT represent clinical evidence of patient benefit, diagnostic accuracy, or regulatory validation.

**Benchmark Version:** VigilBench 2.0 (Phase 2 & 3 Core)  
**Execution Timestamp:** 2026-10-15 19:45:51 UTC  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.1-WP2.4, WP3.0-WP3.5; `docs/ML_PROGRAM.md` §3, §4, §6, §9  

---

## 1. Overall Model Leaderboard (Synthetic Tier G1 In-Distribution)

Evaluated on N=1,000 held-out synthetic patients with prospective horizon $\tau = 365$ days using Kaplan-Meier inverse probability of censoring weighting (Uno et al. 2007).

| Model ID | Family | IPCW ROC-AUC (V=10) | Brier Score | ECE | Lead Time (Conditional) | Latency (p95 CPU) |
|---|---|---|---|---|---|---|
| `B0_PREVALENCE` | Heuristic | 0.5000 | 0.2113 | 0.0199 | 0.0 days | 0.00 ms |
| `B1_SINGLE_THRESHOLD` | Clinical Rule | 0.7218 | 0.1464 | 0.0427 | 142.9 days | 0.01 ms |
| `B2_VELOCITY_RULE` | Kinetic Rule | 0.5518 | 0.1966 | 0.0594 | 266.3 days | 0.02 ms |
| `B3_REGULARIZED_HAZARD` | Discrete Survival | 0.7704 | 0.1399 | 0.0217 | 363.1 days | 0.66 ms |
| `B4_GRADIENT_BOOSTING` | Non-linear Tree | 0.8142 | 0.1308 | 0.0344 | 278.8 days | 1.30 ms |
| `K3_FAST_LANDMARK` | Bayesian Joint | 0.7887 | 0.1341 | 0.0569 | 305.3 days | 0.06 ms |
| `K1_KINETIC_HYBRID` | ODE-Neural State-Space | 0.7023 | 0.1544 | 0.0257 | 102.9 days | 0.04 ms |
| `K4_DEEP_IRREGULAR_ZOO` | Deep Irregular (GRU-D) | 0.7002 | 0.1584 | 0.0375 | 107.4 days | 0.04 ms |
| `K8_PRODUCTION_ENSEMBLE` | Conformal Stacking | 0.7175 | 0.1614 | 0.0475 | 83.1 days | 0.03 ms |

---

## 2. Integrity and Anti-Degeneracy Audit
Per `docs/ML_PROGRAM.md` §10 (Stop-and-Think Triggers):
- **Zero AUC ~ 1.0 Claims:** All IPCW AUC values fall in the realistic range [0.50, 0.85]. No model exhibits trivial separability or target leakage.
- **No Unverified Claims:** All numbers are computed from deterministic simulation pipelines with recorded seeds.

---

## 3. Sim-to-Real Gap Analysis (MASTER_PLAN §14 WP2.4)
The primary vulnerability of algorithms developed in simulation is that synthetic mathematical noise underestimates real clinical entropy. Specifically:
1. **Pre-Analytical Errors (Hypothesis):** In vitro haemolysis and IV fluid dilution create spike artifacts that non-mechanistic decision trees misinterpret as disease acceleration.
2. **Inter-Laboratory Calibration Drifts (Hypothesis):** Facilities using different analyzer platforms (e.g. Roche Cobas vs Abbott Architect) exhibit systematic 5-15% offsets that invalidate unadjusted static cutoffs. Mitigated by Model K5 (Hierarchical Lab Harmonisation).
3. **Verification Bias (Supported by Study S3 Results):** Confirmatory imaging is ordered selectively for patients with symptoms or rising markers. In Study S3, naive complete-case evaluation severely overestimates sensitivity by +16.8 percentage points (0.880 complete-case vs 0.712 true IPW) because disease-free unverified patients are excluded, while specificity changes by only ~0.2 percentage points (0.912 vs 0.914).

These gaps will be directly addressed in Phase 3 (conformal risk control), Phase 4 (M3 Plausibility Adjudicator), and Phase 9 (retrospective validation on real hospital cohorts).

---

## 4. Pre-Registered Study Summaries
- **Study S1 (Visit Sparsity):** [`reports/ml/S1_SPARSITY/REPORT.md`](./S1_SPARSITY/REPORT.md)
- **Study S2 (Anytime-Valid Sequential Detection):** [`reports/ml/S2_SEQUENTIAL/REPORT.md`](./S2_SEQUENTIAL/REPORT.md)
- **Study S3 (Partial Verification Bias):** [`reports/ml/S3_VERIFICATION_BIAS/REPORT.md`](./S3_VERIFICATION_BIAS/REPORT.md)
- **Study S4 (Deep Zoo Pre-Training & Scaling):** [`reports/ml/S4_PRETRAINING_SCALING/REPORT.md`](./S4_PRETRAINING_SCALING/REPORT.md)
- **Study S5 (Multi-Site Lab Harmonisation):** [`reports/ml/S5_HARMONISATION/REPORT.md`](./S5_HARMONISATION/REPORT.md)
- **Study S6 (Active Sensing & Adaptive Scheduling):** [`reports/ml/S6_ACTIVE_SENSING/REPORT.md`](./S6_ACTIVE_SENSING/REPORT.md)
- **Study S9 (Cross-Generator Robustness):** [`reports/ml/S9_CROSS_GENERATOR/REPORT.md`](./S9_CROSS_GENERATOR/REPORT.md)
- **Study S10 (Multi-Site Synthetic Trial & Federated Learning):** [`reports/ml/S10_MULTISITE_SYNTHETIC_TRIAL/REPORT.md`](./S10_MULTISITE_SYNTHETIC_TRIAL/REPORT.md)