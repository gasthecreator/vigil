# VigilBench Phase 2 & 3: Longitudinal Surveillance & Advanced Modeling Benchmark

> **CLINICAL DISCLAIMER & SYNTHETIC DATA NOTICE:**  
> This benchmark was conducted exclusively on **SYNTHETIC DATA** (Tiers G1, G2, G3). All metrics, lead times, and calibration curves reflect synthetic cohort properties and simulator dynamics. They DO NOT represent clinical evidence of patient benefit, diagnostic accuracy, or regulatory validation.

**Benchmark Version:** VigilBench 2.0 (Phase 2 & 3 Core)  
**Execution Timestamp:** 2026-10-17 08:12:30 UTC  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.1-WP2.4, WP3.0-WP3.5; `docs/ML_PROGRAM.md` §3, §4, §6, §9  

---

## 1. Overall Model Leaderboard (Synthetic Tier G1 In-Distribution)

Evaluated on N=1,000 held-out synthetic patients with prospective horizon $\tau = 365$ days using Kaplan-Meier inverse probability of censoring weighting (Uno et al. 2007). Lead time evaluated at fixed 5% visit alert rate constraint (Condition R7 & RR9).

| Model ID | Family | IPCW ROC-AUC (V=10) | Brier Score | ECE | Lead Time (Conditional) | Latency (p95 CPU) |
|---|---|---|---|---|---|---|
| `B0_PREVALENCE` | Heuristic | 0.5000 | 0.2113 | 0.0199 | 0.0 days | 0.00 ms |
| `B1_SINGLE_THRESHOLD` | Clinical Rule | 0.6455 | 0.1737 | 0.0719 | 51.3 days | 0.01 ms |
| `B2_VELOCITY_RULE` | Kinetic Rule | 0.5533 | 0.1994 | 0.0533 | 120.1 days | 0.02 ms |
| `B3_REGULARIZED_HAZARD` | Discrete Survival | 0.7616 | 0.1431 | 0.0216 | 57.2 days | 0.64 ms |
| `B4_GRADIENT_BOOSTING` | Non-linear Tree | 0.8102 | 0.1333 | 0.0355 | 61.2 days | 1.34 ms |
| `K3_FAST_LANDMARK` | Bayesian Joint | 0.8027 | 0.1405 | 0.0206 | 56.6 days | 0.19 ms |
| `K1_KINETIC` | Mechanistic State-Space | 0.5703 | 0.2161 | 0.0550 | 106.5 days | 0.10 ms |

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
- **Study S9 (Cross-Generator Robustness):** [`reports/ml/S9_CROSS_GENERATOR/REPORT.md`](./S9_CROSS_GENERATOR/REPORT.md)
- **Retracted Studies (Condition R1):** Studies S4, S5 (v1), S6, and S10 are retracted to [`reports/ml/RETRACTED/`](./RETRACTED/) per Overseer Verdict P3 and deferred to sub-phases 3C and 3D.