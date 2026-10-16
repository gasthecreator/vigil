# Pre-Registration: EXP-K1-003

## 1. Study Overview
- **Experiment ID:** EXP-K1-003
- **Target Model:** Model K1 (Hybrid Kinetic State-Space Model)
- **Problem:** Instantaneous hazard evaluation at horizon $\tau$ discards trajectory history and timing of onset within the forward surveillance window $(t_{\text{landmark}}, \tau]$.
- **Intervention:** Prospective cumulative tumor burden integration: compute risk from integrated latent burden $\int_{t_{\text{landmark}}}^{\tau} \max(0, \exp(r(t - t_{\text{onset}})) - 1) dt$ across posterior trajectory draws.

## 2. Hypothesis & Evaluation
- **Hypothesis:** Integrating prospective tumor volume over the forward surveillance interval provides finer discrimination of subclinical recurrence dynamics than single-point horizon hazard, improving prospective ROC-AUC.
- **Success Criterion:** Prospective 1-year ROC-AUC improvement $\ge 0.02$ compared to instantaneous terminal hazard evaluation.
- **Cohort:** 300 patients from `vigil-sim` G1 Smooth Kinetics (seed 44), landmark 365 days, horizon 730 days.
- **Primary Metric:** ROC-AUC for recurrence in $(365, 730]$ days; Secondary Metric: Brier score.
