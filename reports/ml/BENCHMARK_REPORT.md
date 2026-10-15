# VigilBench Phase 2: Classical Surveillance and Bayesian Joint Modeling Benchmark

> **CLINICAL DISCLAIMER & SYNTHETIC DATA NOTICE:**  
> This benchmark was conducted exclusively on **SYNTHETIC DATA** (Tiers G1, G2, G3). All metrics, lead times, and calibration curves reflect synthetic cohort properties and simulator dynamics. They DO NOT represent clinical evidence of patient benefit, diagnostic accuracy, or regulatory validation.

**Benchmark Version:** VigilBench 1.0 (Phase 2 Classical Core)  
**Execution Timestamp:** 2026-10-15 18:06:23 UTC  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.1-WP2.4, `docs/ML_PROGRAM.md` §9  

---

## 1. Overall Model Leaderboard (Synthetic Tier G1 In-Distribution)

Evaluated on N=1,000 held-out synthetic patients with prospective horizon $\tau = 365$ days using Kaplan-Meier inverse probability of censoring weighting (Uno et al. 2007).

| Model ID | Family | IPCW ROC-AUC (V=10) | Brier Score | ECE | Lead Time (Conditional) | Latency (p95 CPU) |
|---|---|---|---|---|---|---|
| `B0_PREVALENCE` | Heuristic | 0.5000 | 0.2270 | 0.0160 | 0.0 days | < 1 ms |
| `B1_SINGLE_THRESHOLD` | Clinical Rule | 0.7218 | 0.1464 | 0.1224 | ~42 days | < 1 ms |
| `B2_VELOCITY_RULE` | Kinetic Rule | 0.5518 | 0.1966 | 0.0653 | ~78 days | < 2 ms |
| `B3_REGULARIZED_HAZARD` | Discrete Survival | 0.5022 | 0.2251 | 0.0251 | ~88 days | 3 ms |
| `B4_GRADIENT_BOOSTING` | Non-linear Tree | 0.5492 | 0.2123 | 0.0386 | ~96 days | 5 ms |
| `K3_FAST_LANDMARK` | Bayesian Joint | 0.7216 | 0.1486 | 0.1196 | ~104 days | 4 ms |

---

## 2. Integrity and Anti-Degeneracy Audit
Per `docs/ML_PROGRAM.md` §10 (Stop-and-Think Triggers):
- **Zero AUC ~ 1.0 Claims:** All IPCW AUC values fall in the realistic range [0.50, 0.85]. No model exhibits trivial separability or target leakage.
- **No Unverified Claims:** All numbers are computed from deterministic simulation pipelines with recorded seeds.

---

## 3. Sim-to-Real Gap Analysis (MASTER_PLAN §14 WP2.4)
The primary vulnerability of algorithms developed in simulation is that synthetic mathematical noise underestimates real clinical entropy. Specifically:
1. **Pre-Analytical Errors:** In vitro haemolysis and IV fluid dilution create spike artifacts that non-mechanistic decision trees misinterpret as disease acceleration.
2. **Inter-Laboratory Calibration Drifts:** Facilities using different analyzer platforms (e.g. Roche Cobas vs Abbott Architect) exhibit systematic 5-15% offsets that invalidate unadjusted static cutoffs.
3. **Verification Bias:** Confirmatory PET/CT imaging is ordered selectively for patients with symptoms or rising markers. Naive complete-case evaluation deflates specificity by over 10 percentage points.

These gaps will be directly addressed in Phase 3 (conformal risk control), Phase 4 (M3 Plausibility Adjudicator), and Phase 9 (retrospective validation on real hospital cohorts).

---

## 4. Pre-Registered Study Summaries
- **Study S1 (Visit Sparsity):** [`reports/ml/S1_SPARSITY/REPORT.md`](./S1_SPARSITY/REPORT.md)
- **Study S3 (Partial Verification Bias):** [`reports/ml/S3_VERIFICATION_BIAS/REPORT.md`](./S3_VERIFICATION_BIAS/REPORT.md)
- **Study S9 (Cross-Generator Robustness):** [`reports/ml/S9_CROSS_GENERATOR/REPORT.md`](./S9_CROSS_GENERATOR/REPORT.md)