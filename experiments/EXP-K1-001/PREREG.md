# Pre-Registration: EXP-K1-001

## 1. Study Overview
- **Experiment ID:** EXP-K1-001
- **Target Model:** Model K1 (Hybrid Kinetic State-Space Model)
- **Problem:** K1 underperforms longitudinal landmark regression (K3) and gradient boosted baselines (B4) on sparse surveillance cohorts.
- **Intervention:** Informative log-normal prior shrinkage on tumor doubling time ($T_d \in [50, 100]$ days) and marker shedding ($s \in [0.15, 0.30]$).

## 2. Hypothesis & Evaluation
- **Hypothesis:** Shrinking prior dispersion around clinical medians prevents explosive trajectory divergence in early visits, improving discrimination and calibration.
- **Success Criterion:** Prospective 1-year ROC-AUC improvement $\ge 0.02$ compared to unconstrained uniform prior baseline on synthetic cohort.
- **Cohort:** 300 patients from `vigil-sim` G1 Smooth Kinetics (seed 42), landmark 365 days, horizon 730 days.
- **Primary Metric:** ROC-AUC for recurrence in $(365, 730]$ days; Secondary Metric: Brier score.
