# Study S1 Pre-Registration: Sparsity Regime Analysis

**Study ID:** S1_SPARSITY  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.2/WP2.4; `docs/ML_PROGRAM.md` §6, §9  

---

## 1. Study Objective and Research Question
In resource-constrained and routine oncology follow-up environments, patients frequently present with sparse, irregularly spaced visits. The primary objective of Study S1 (Phase 2 Classical Arm) is to establish the baseline performance envelope of classical decision rules (B0, B1, B2), regularized discrete-time hazard models (B3), gradient boosted decision trees (B4), and the K3 Bayesian joint longitudinal–survival model under systematically restricted longitudinal visit depths:
$$\text{Visits } V \in \{3, 4, 6, 10, 20\}$$

**Core Question:** Does joint longitudinal–survival modeling (K3) preserve discrimination and calibration under extreme longitudinal sparsity ($V \le 4$) compared to tabular windowed feature engineering (B4)?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Sparsity Degradation):** Windowed derivative baselines (B2 velocity) and tree-based ensembles (B4) will exhibit pronounced discrimination loss (drop in IPCW ROC-AUC $> 0.08$) when visit depth decreases from $V = 10$ to $V = 3$, driven by high sample variance in two-point finite difference approximations.
2. **H2 (Bayesian Shrinkage Advantage):** The K3 joint longitudinal–survival model, by shrinking patient-specific random slope and intercept parameters toward the population mean, will maintain significantly higher calibration stability (ECE $< 0.15$) and superior net benefit at low visit counts ($V \in \{3, 4\}$) relative to unregularized velocity rules.
3. **H3 (Threshold Invariance):** Static biomarker thresholding (B1, CA 15-3 $\ge 30$ U/mL) will show flat discrimination across visit strata but poor sensitivity and negative net benefit at decision threshold $p_t = 0.15$.

---

## 3. Evaluated Models
- **B0 (Prevalence Baseline):** Constant incidence rate prediction.
- **B1 (Single Threshold Baseline):** CA 15-3 $\ge 30$ U/mL binary threshold mapped to risk score.
- **B2 (Velocity Baseline):** Annualized rate of change in CA 15-3 ($\Delta / \Delta t$) mapped to risk.
- **B3 (Regularized Hazard Baseline):** Discrete-time logistic hazard model with L2 penalty trained on windowed features (level, 90d velocity, acceleration, CV).
- **B4 (Gradient Boosting Baseline):** XGBoost classifier with shallow depth ($d=3$) and L2 regularization trained on windowed features.
- **K3 (Bayesian Joint Model - Landmark Production Approximation):** Empirical Bayes linear mixed-effects trajectory estimator coupled with survival hazard regression.

---

## 4. Dataset and Stratification
- **Data Tier:** Synthetic G1 Multi-Compartment Kinetic Simulator (`vigil_sim.mechanistic`).
- **Sample Size:** $N = 2,000$ synthetic patients (1,000 training, 1,000 held-out test).
- **Test Set Discipline:** Single evaluation pass on frozen test set; seed = 42.
- **Sparsity Slicing:** For each evaluation run, patient longitudinal histories are truncated at the first $V$ visits ($V \in \{3, 4, 6, 10, 20\}$). Patients with fewer than $V$ visits are evaluated on their total available trajectory up to $V$.

---

## 5. Primary and Secondary Endpoints
1. **Primary Metric:** IPCW Time-Dependent ROC-AUC (Uno et al. 2007) at horizon $\tau = 365$ days with Kaplan-Meier censoring inverse weighting.
2. **Secondary Metrics:**
   - Expected Calibration Error (ECE, 10 equal-quantile bins).
   - IPCW Brier score at $\tau = 365$ days.
   - Survival Decision Curve Analysis (DCA) Net Benefit at clinical threshold $p_t = 0.15$.
   - Lead time (days prior to clinical presentation) and overdetection rate.
3. **Uncertainty Estimation:** Clustered patient-level bootstrap with $B = 1,000$ resamples; all metrics reported as point estimate [95% CI].

---

## 6. Pre-Registered Decision and Kill Criteria
Per `docs/ML_PROGRAM.md` §6:
- If K3 joint model yields net benefit $\le$ B4 gradient boosting across $V \le 4$ sparse visits, trigger pre-registered kill protocol: document failure of two-stage linear mixed effects under sparsity and prioritize K1 single-compartment ODE / Kalman formulation in Phase 3.
- If any model yields IPCW ROC-AUC $> 0.97$, immediately trigger Stop-and-Think investigation for synthetic target leakage before reporting.
