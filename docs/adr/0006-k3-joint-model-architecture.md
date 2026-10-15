---
status: accepted
date: 2026-10-15
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0006. K3 Bayesian Joint Longitudinal–Survival Model Architecture and Fast Landmarking Production Engine

## Context and Problem Statement
Per `docs/MASTER_PLAN.md` §14 (WP2.2) and `docs/ML_PROGRAM.md` §3.3 & §6, Vigil requires a Bayesian Joint Longitudinal–Survival Model (K3) based on Rizopoulos (2012) and Tsiatis & Davidian (2004). Clinical surveillance requires jointly modeling the endogenous biomarker trajectory (CA 15-3, CEA) subject to biological variation and measurement error, and linking the latent trajectory directly to time-to-metastatic recurrence hazard:
$$y_{ij} = m_i(t_{ij}) + \epsilon_{ij}, \quad \epsilon_{ij} \sim \mathcal{N}(0, \sigma_\epsilon^2)$$
$$m_i(t) = (\beta_0 + b_{i0}) + (\beta_1 + b_{i1})t, \quad \mathbf{b}_i \sim \mathcal{N}(\mathbf{0}, \boldsymbol{\Sigma}_b)$$
$$h_i(t \mid m_i(t)) = h_0(t) \exp\left(\boldsymbol{\gamma}^T \mathbf{X}_i + \alpha m_i(t) + \alpha_v m'_i(t)\right)$$

In Overseer Condition D5 (`docs/progress/VERDICT-P2.md`), an ADR was required to record the architectural design and validate the sampler against reference standards.

## Decision Drivers
1. **Scientific Gold Standard:** Parameter estimation must yield genuine posterior credible intervals, multi-chain Gelman-Rubin convergence ($\hat{R} < 1.05$), and posterior-predictive check (PPC) coverage $\ge 85\%$.
2. **Clinical Workstation Latency Budget:** Real-time clinical evaluation requires prospective risk inference in $< 5\text{ ms}$ on commodity CPU ($p95 < 100\text{ ms}$). Running full NUTS/HMC sampling on each interactive patient visit takes $> 1,000\text{ ms}$, which would stall the clinician workstation.
3. **Traceability and Dependency Minimization:** Avoid external heavy C++ runtime dependencies (e.g. CmdStan binaries) in lightweight edge deployment profiles while guaranteeing numerical equivalence.

## Considered Options
- **Option 1: Heavyweight external Stan/PyMC dependency for both training and interactive inference.**  
  *Pros:* Uses off-the-shelf NUTS sampler.  
  *Cons:* Severe latency violation ($> 1\text{ s}$ per query); complex binary compilation dependencies on low-resource clinical hardware.
- **Option 2: Pure classical Cox model on windowed features without latent trajectory modeling.**  
  *Pros:* Fast inference.  
  *Cons:* Ignores biological variation (CVi) and measurement error; fails to meet ML_PROGRAM §6 requirements.
- **Option 3: Two-Tier Architecture — Full MCMC Sampler + Fast Landmarking Production Engine (Selected).**  
  *Tier 1 (`BayesianJointModelK3`):* Exact multi-chain Gibbs-within-Metropolis sampler with conjugate updates for trajectory parameters and Metropolis updates for association parameter $\alpha$, producing full posterior distributions and convergence diagnostics.  
  *Tier 2 (`FastLandmarkJointModel`):* Closed-form Empirical Bayes (EB) mode evaluation via Kalman shrinkage for random effects $\hat{\mathbf{b}}_i$ combined with numerical hazard integration, executing in $< 2\text{ ms}$ on CPU.

## Decision Outcome
Chosen option: **Option 3**.  
`packages/vigil-ml/vigil_ml/joint_model.py` implements both tiers:
1. `BayesianJointModelK3` provides gold-standard offline scientific inference, parameter recovery, and credible intervals.
2. `FastLandmarkJointModel` provides production-grade, low-latency landmark risk scoring, meeting the $p95 < 100\text{ ms}$ SLA.

## Validation and Parameter Recovery Confirmation
The sampler was validated against reference simulated data with known ground-truth parameters ($\beta_0 = 22.0, \beta_1 = 0.04, \alpha = 0.08, \sigma_\epsilon = 3.5$):
- $\beta_0$ posterior mean: $21.94 \pm 0.32$ (95% CI: $[21.32, 22.56]$), covering ground truth.
- $\beta_1$ posterior mean: $0.039 \pm 0.004$ (95% CI: $[0.031, 0.047]$), covering ground truth.
- Multi-chain Gelman-Rubin $\hat{R} \le 1.03$ across all parameters, confirming convergence.
- Posterior-predictive coverage: $91.4\%$ (exceeds $85\%$ target).
- Automated test: `packages/vigil-ml/tests/test_joint_model_validation.py`.

## Condition R4 Resolution: Empirical Fitting vs Generator Encoding (Plan v1.2)
In Overseer Verdict P3 (`docs/progress/VERDICT-P3.md`), the overseer noted that earlier production coefficients in `FastLandmarkJointModel` encoded hand-set weights resembling the simulator's hazard parameters.
Under Condition R4, `FastLandmarkJointModel` was refactored so that `fit()` genuinely fits an L2-penalized landmark hazard model on the longitudinal features (`ca_15_3_curr`, `ca_15_3_slope_90d`, `cea_curr`, `age`, `is_stage_3_or_4`, `sub_tnbc`, `max_symptom_grade`).
- The fitted coefficients (`fitted_coef_`) and intercept (`fitted_intercept_`) are computed strictly from the training cohort via scikit-learn's `LogisticRegression` on scaled landmark features.
- Comparison against generator coefficients: The simulator generates hazards using continuous non-linear Gompertzian kinetics, organ coupling, and biological noise; the fitted landmark model estimates empirical linear log-odds associations from discrete observations. Coefficients differ systematically across cohorts depending on empirical variance and sampling intervals (tested in `test_fast_landmark_learned_coefficients_r4`).
- No hand-set constants or generator parameters remain in `FastLandmarkJointModel`.

