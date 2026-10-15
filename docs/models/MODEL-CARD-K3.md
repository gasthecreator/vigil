# Model Card: Model K3 — Bayesian Joint Longitudinal–Survival Model

**Model Identifier:** `MODEL-K3-JOINT-SURVIVAL`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.2; `docs/ML_PROGRAM.md` §6, §9  
**Evaluation Status:** Evaluated on Synthetic Tiers G1, G2, G3 (`reports/ml/BENCHMARK_REPORT.md`)  

---

## 1. Model Overview and Intended Use
Model K3 is a Bayesian joint longitudinal–survival model designed for continuous decision-support in breast cancer post-treatment follow-up. Unlike static point-in-time classifiers or naive threshold rules, Model K3 explicitly couples the underlying trajectory of longitudinal serum biomarkers (e.g. CA 15-3, CEA) with a time-to-event survival submodel.

### Dual-Implementation Architecture
1. **Full Bayesian MCMC Sampler (`BayesianJointSurveillanceModel`):**
   - Conjugate Gibbs updates for fixed effects $(\beta_0, \beta_1)$ and observational variance $\sigma_\epsilon^2$.
   - Adaptive Metropolis-Hastings update for survival association parameter $\alpha$.
   - Multi-chain Gelman-Rubin convergence diagnostics ($\hat{R} \le 1.05$) and effective sample size tracking.
   - Posterior-predictive checks to identify model misspecification.
2. **Fast Landmarking Production Approximation (`FastLandmarkJointModel`):**
   - Closed-form Empirical Bayes (EB) random effect estimation via generalized ridge shrinkage.
   - Vectorized evaluation executing in $< 5$ ms on CPU, meeting the p95 $< 100$ ms workstation latency budget.

---

## 2. Mathematical Formulation
### Longitudinal Submodel
For patient $i$ at visit time $t_{ij}$:
$$y_{ij} = (\beta_0 + b_{i0}) + (\beta_1 + b_{i1}) t_{ij} + \epsilon_{ij}, \quad \epsilon_{ij} \sim \mathcal{N}(0, \sigma_\epsilon^2)$$
$$\begin{pmatrix} b_{i0} \\ b_{i1} \end{pmatrix} \sim \mathcal{N}\left(\mathbf{0}, \boldsymbol{\Sigma}_b\right)$$

### Survival Submodel
The instantaneous hazard of recurrence at time $t$ conditional on true latent trajectory $m_i(t) = (\beta_0 + b_{i0}) + (\beta_1 + b_{i1}) t$:
$$h_i(t \mid m_i(t)) = h_0(t) \exp\left(\mathbf{z}_i^\top \boldsymbol{\gamma} + \alpha m_i(t)\right)$$

where $\alpha$ quantifies the association between circulating biomarker concentration and recurrence hazard.

---

## 3. Evaluation on VigilBench Phase 2
- **Discrimination (Uno IPCW ROC-AUC):** $0.74\text{--}0.78$ on held-out synthetic G1 data ($N = 1,000$ test patients).
- **Calibration (ECE):** Expected calibration error $\le 0.12$.
- **Sparsity Stability (Study S1):** Maintains consistent discrimination across visit depths $V \in \{3, 4, 6, 10, 20\}$, significantly outperforming unregularized velocity finite-difference rules under sparse sampling.
- **Cross-Generator Degradation (Study S9):** Exhibits smaller AUROC degradation ($\Delta \text{AUC} = -0.05$) when transferred to heavy-tailed noise generator G3 compared to decision trees ($-0.09$).

---

## 4. Caveats, Failure Modes, and Safe Degradation
1. **Linear Trajectory Assumption:** The K3 linear trajectory model assumes steady exponential growth on log-scale. Sudden step-changes or burst shedding (Generator G2) can temporarily violate this assumption.
2. **Pre-Analytical Spikes:** In vitro haemolysis or sample handling errors can distort single-point measurements. Production deployment requires pre-filtering via Model M3 (Plausibility Adjudicator).
3. **Synthetic Domain Limitation:** All reported metrics are established on synthetic data. Real clinical performance must be evaluated in Phase 9 on retrospective hospital cohorts.
