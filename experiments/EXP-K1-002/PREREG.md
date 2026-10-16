# Pre-Registration: EXP-K1-002

## 1. Study Overview
- **Experiment ID:** EXP-K1-002
- **Target Model:** Model K1 (Hybrid Kinetic State-Space Model)
- **Problem:** Fixed measurement variance $\sigma_{\text{obs}}^2$ leads to over-confident likelihood weighting on tightly-spaced or clustered visits.
- **Intervention:** Visit interval-adaptive noise scaling: scale measurement variance dynamically by interval $\Delta t_j / \Delta t_{\text{nominal}}$ during sequential trajectory scoring.

## 2. Hypothesis & Evaluation
- **Hypothesis:** Scaling likelihood variance inversely with sampling frequency regularizes sequential filter innovations, preventing overfitting to short-interval measurement clusters.
- **Success Criterion:** Prospective 1-year ROC-AUC improvement $\ge 0.02$ compared to unscaled fixed-noise baseline on synthetic cohort.
- **Cohort:** 300 patients from `vigil-sim` G1 Smooth Kinetics (seed 43), landmark 365 days, horizon 730 days.
- **Primary Metric:** ROC-AUC for recurrence in $(365, 730]$ days; Secondary Metric: Brier score.
