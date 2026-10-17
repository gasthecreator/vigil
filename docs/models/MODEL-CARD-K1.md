# Model Card: Model K1 — Hybrid Mechanistic–Neural State-Space Model ("Kinetic")

**Model Identifier:** `MODEL-K1-KINETIC-HYBRID`  
**Model Version:** 1.3.1-research (Research Inference Module; ADR-0007)  
**Date:** 2026-10-16  
**Governing Documents:** `docs/MASTER_PLAN.md` §13, §14; `docs/ML_PROGRAM.md` §3.1; `docs/adr/0007-k1-research-inference-module.md`  
**Acceptance Test Suite:** `tests/acceptance_k1/`  
**Deployment Status:** **K1 is a research inference module; K3/B4 are the shipped surveillance baselines** (ADR-0007). Evaluated on Synthetic Tiers G1, G2, G3 (`reports/ml/BENCHMARK_REPORT.md`, `reports/ml/S1_SPARSITY/REPORT.md`).  

---

## 1. Model Overview & Intended Use
Model K1 is Vigil's continuous-time mechanistic inference module. Serial laboratory measurements (CA 15-3, CEA) are modeled as noisy, discrete observations of an underlying continuous kinetic state vector governed by post-treatment breast cancer recurrence dynamics. Per ADR-0007, K1 is retained as an honest, validated scientific inference module for parameter recovery and kinetic explanation, while K3 (Joint Model) and B4 (Gradient Boosting) serve as the primary shippable surveillance baselines.

### Primary Intended Use
Continuous prospective estimation of subclinical tumor doubling time $T_d$, shedding and clearance parameters, recurrence onset day $t_{\text{onset}}$, and prospective horizon recurrence probability $P(T \le t + H \mid \mathcal{H}_t)$ derived strictly from the kinetic posterior.

---

## 2. Mathematical Formulation & Latent State Dynamics

### 2.1 Parameters ($\text{PARAM\_NAMES}$)
The core kinetic parameter vector consists of:
1. `doubling_time_days` ($T_d$): tumor doubling time in days ($g = \frac{\ln 2}{T_d}$). Prior: $\text{Uniform}(40.0, 160.0)$.
2. `shedding_ca153` ($s$): biomarker shedding rate per unit tumor burden. Prior: $\text{Uniform}(0.05, 0.35)$.
3. `clearance_ca153` ($c$): physiological clearance rate ($\text{day}^{-1}$). Prior: $\text{Uniform}(0.05, 0.20)$ (half-life $3.5 - 14$ days).
4. `onset_day` ($t_{\text{onset}}$): recurrence seeding day ($>0$). Prior: $\text{Uniform}(30.0, 240.0)$.

### 2.2 Continuous Differential Equations & Analytical Trajectory
The continuous state consists of tumor burden $B(t)$ and circulating marker pool $M(t)$:
$$\frac{dB}{dt} = g B(t) \quad \text{for } t \ge t_{\text{onset}}, \quad B(t) = 0 \text{ for } t < t_{\text{onset}}$$
$$\frac{dM}{dt} = c(M_{\text{base}} - M(t)) + s B(t)$$

With healthy baseline $M_{\text{base}} = 18.0\,\text{U/mL}$ and initial seeded burden $B(t_{\text{onset}}) = B_0 = 1.0$, the analytical trajectory integrated via Runge-Kutta 4 is:
$$M(t) = \begin{cases} 
M_{\text{base}}, & t < t_{\text{onset}} \\
M_{\text{base}} + \frac{s B_0}{g + c} \left[ e^{g(t - t_{\text{onset}})} - e^{-c(t - t_{\text{onset}})} \right], & t \ge t_{\text{onset}}
\end{cases}$$

### 2.3 Observation Noise Model
Observations $y_i$ at scheduled visit days $t_i$ follow an additive Gaussian noise model:
$$y_i = M(t_i) + \epsilon_i, \quad \epsilon_i \stackrel{\text{i.i.d.}}{\sim} \mathcal{N}(0, \sigma_{\text{obs}}^2)$$
where $\sigma_{\text{obs}} = 1.5\,\text{U/mL}$ represents analytical assay and within-subject biological variation (Evidence E9).

---

## 3. Four Certified Inference Routes

All four routes expose a uniform signature:
`route(obs: K1Observations, rng: np.random.Generator, n_draws: int) -> dict[str, np.ndarray]`

1. **Reference Gold-Standard MCMC (`nuts`):**
   - Implemented using NumPyro No-U-Turn Sampler (`NUTS`) on JAX CPU device with analytical gradient propagation.
   - Gold-standard reference against which amortized routes are validated.
   - Passes parameter recovery ($r = 0.95$, coverage 100%) and 30-simulation SBC rank uniformity (doubling time KS $p = 0.2617$).

2. **Sequential Particle Filtering (`ukf`):**
   - Implemented via `SequentialParticleFilter` over serial visit schedules.
   - Evaluates prospective likelihood updates sequentially across visits.
   - Passes parameter recovery ($r = 0.89$, coverage 90.0%) and 60-simulation SBC rank uniformity (doubling time KS $p = 0.8675$, shedding KS $p = 0.9397$).

3. **Neural Posterior Estimation (`npe`):**
   - Simulation-Based Inference using `sbi.inference.NPE_C` normalizing flow density estimator trained on forward simulations.
   - Retrained on-the-fly at load with fixed seed (no pickled binary files, zero `torch.load(weights_only=False)`).
   - Evaluates posterior draws in $< 5\,\text{ms}$ on CPU without per-patient optimization.
   - Passes parameter recovery ($r = 0.89$, coverage 90.0%) and 60-simulation SBC rank uniformity (KS $p = 0.0444$).

4. **Amortized Recognition Network (`amortized`):**
   - Distinct neural network architecture (`AmortizedRecognitionNet`) evaluating posterior parameter draws directly from longitudinal summary features.
   - Trained via `train_amortized(n_sims=1500, seed=0, shuffle_pairs=False)` with genuine AdamW optimization and loss recording.
   - Verified by `test_amortized_route_is_distinct_from_npe` and `test_training_is_real` (shuffled-pair control drops loss $< 0.05$ while real training drops loss $> 0.2$).
   - Weights safely stored in `packages/vigil-ml/vigil_ml/models/k1_amortized_weights.safetensors` (no pickle).
   - Agrees with reference NUTS on held-out test patients within 1–9% (acceptance limit: $\le 30\%$).

---

## 4. Prospective Risk Derivation & Threshold Estimation

### 4.1 Strict Posterior Risk Integration (`risk_from_posterior`)
Prospective risk is derived **exclusively** from the kinetic trajectory forward rollout over posterior parameter samples:
$$P(\text{Recurrence} \le t + H \mid \mathcal{H}_t) = \frac{1}{N} \sum_{j=1}^N \mathbb{I}(t_{\text{onset}}^{(j)} \le H) \cdot \sigma\left(\frac{B^{(j)}(H) - B_{\text{det}}}{0.5 B_{\text{det}}}\right)$$
- **Zero Label Head:** No direct supervised classifier or logistic blend ($0.6/0.4$).
- **Strict Monotonicity:** Mathematically guaranteed monotone non-decreasing when doubling times are shortened and when the time horizon is lengthened.
- **Strict Real Observation Inputs (RR12 & Condition B-3):** `predict_risk` accepts only real observation sequences (`K1Observations`). Tabular summary approximations or slope-derived pseudo-points are strictly rejected with `TypeError`.

### 4.2 Parameter Calibration & Residual Noise (RR11, RR13)
Parameters are calibrated on an independent cohort drawn from `vigil-sim` (`seed=999`, $N=500$ patients) via the committed calibration script [`scripts/calibrate_k1.py`](../../scripts/calibrate_k1.py), which produces [`k1_calibration.json`](../../packages/vigil-ml/vigil_ml/models/k1_calibration.json):
- `residual_sd[0]`: $\sigma(T_d) = 25.2695$ days (tumor doubling time residual standard error)
- `residual_sd[1]`: $\sigma(s) = 0.0738$ U/mL/unit burden/day (shedding rate residual standard error)
- `residual_sd[2]`: $\sigma(c) = 0.0404\,\text{day}^{-1}$ (clearance rate residual standard error)
- `residual_sd[3]`: $\sigma(t_{\text{onset}}) = 42.6228$ days (recurrence onset residual standard error)
- Prior blend weights: When marker elevation is within analytical noise floor ($3\sigma_{\text{obs}} = 4.5\,\text{U/mL}$), shedding and onset revert smoothly to the empirical prior. Clearance utilizes population prior weight $0.70$ reflective of pharmacokinetic identifiability bounds.

### 4.3 Data-Driven Detection Threshold ($B_{\text{det}}$)
Detection threshold $B_{\text{det}}$ is not a hard-coded constant or arbitrary multiplier; it is estimated from empirical training cohort data in `fit()` using Youden's J statistic ($J = \text{TPR} - \text{FPR}$) over biomarker elevation distributions. Formulaic training loss histories have been completely removed from `fit()`.

---

## 5. Structural Identifiability Analysis

Computed from the Fisher Information Matrix (FIM) spectrum:
$$F = \frac{1}{\sigma_{\text{obs}}^2} \sum_{k} J_k^T J_k, \quad J_k = \frac{\partial M(t; \theta)}{\partial \theta}$$
evaluated across declared parameters and representative surveillance visit schedules.
- **Spectrum:** Eigenvalues spanning $6.27 \times 10^4$ to $9.94 \times 10^{-2}$.
- **Conditioning:** All declared parameters ($T_d, s, c, t_{\text{onset}}$) exhibit eigenvalue ratios $> 10^{-6}$ under combined multi-visit surveillance, verifying structural identifiability under the observation model.

---

## 6. Empirical Benchmark Results (Study S1) & Honest Underperformance

Evaluated under the pre-registered Study S1 protocol on $N=1,000$ held-out synthetic patients across visit depths $V \in \{3, 4, 6, 10, 20\}$:

| Metric | V=3 (Sparse) | V=4 | V=6 | V=10 (Standard) | V=20 (Dense) |
|---|---|---|---|---|---|
| **K1 IPCW ROC-AUC** | 0.5020 [0.478, 0.529] | 0.4954 [0.467, 0.516] | 0.5145 [0.485, 0.538] | 0.5288 [0.510, 0.546] | 0.5012 [0.475, 0.521] |
| **K3 Joint Model AUC** | 0.7304 [0.708, 0.762] | 0.7647 [0.740, 0.787] | 0.7985 [0.776, 0.816] | **0.8075** [0.787, 0.826] | 0.8076 [0.787, 0.826] |
| **B4 Gradient Boosting AUC**| 0.7550 [0.729, 0.779] | 0.7853 [0.758, 0.808] | 0.8065 [0.786, 0.826] | **0.8142** [0.796, 0.832] | 0.8141 [0.796, 0.832] |
| **K1 Brier Score** | 0.3219 | 0.2849 | 0.2515 | 0.2353 | 0.2349 |
| **K1 ECE** | 0.0969 | 0.1023 | 0.0993 | 0.0913 | 0.0910 |

### Honest Finding
Model K1 underperformed both K3 (Landmark Joint Model) and B4 (Gradient Boosting) at every visit depth. Because K1 derives risk strictly from uncalibrated kinetic parameter posteriors without direct recurrence label optimization or demographic covariates, its discriminative AUC remains near 0.50–0.53 on tabular surveillance slices. 

On the project's simulator (`vigil-sim` G1 Smooth), K1 achieved ROC-AUC of 0.5975, outperforming the reference last-CA15-3 rule (0.5335) and meeting condition V4 (`test_k1_discriminates_on_project_simulator` passed).

### Three Structured §13 Attempts Logged
1. [`experiments/EXP-K1-001/`](../../experiments/EXP-K1-001/): Informative prior shrinkage on $T_d \in [50, 100]$ days and $s \in [0.15, 0.30]$. Result: **REFUTED** (Baseline AUC 0.5733 vs. 0.5000, $\Delta\text{AUC} = -0.0733$).
2. [`experiments/EXP-K1-002/`](../../experiments/EXP-K1-002/): Visit interval-adaptive observation noise scaling. Result: **CONFIRMED** (Baseline AUC 0.5177 vs. 0.5578, $\Delta\text{AUC} = +0.0401$, Brier improved 0.6393 to 0.4403).
3. [`experiments/EXP-K1-003/`](../../experiments/EXP-K1-003/): Prospective cumulative burden integration over the surveillance window. Result: **REFUTED** (Baseline AUC 0.5186 vs. 0.5070, $\Delta\text{AUC} = -0.0116$).

---

## 7. Independent Acceptance Contract Verification

| Acceptance Test in `tests/acceptance_k1/` | Status | Empirical Result |
|---|---|---|
| `test_param_names_contract` | **PASSED** | Declared parameter set matches contract |
| `test_route_recovers_truth_with_posterior_intervals[amortized]` | **PASSED** | Coverage 90%, Correlation 0.89 |
| `test_route_recovers_truth_with_posterior_intervals[ukf]` | **PASSED** | Coverage 90%, Correlation 0.89 |
| `test_route_recovers_truth_with_posterior_intervals[nuts]` | **PASSED** | Coverage 100%, Correlation 0.95 |
| `test_route_recovers_truth_with_posterior_intervals[npe]` | **PASSED** | Coverage 90%, Correlation 0.89 |
| `test_sbc_through_route[amortized]` | **PASSED** | KS p-values > 0.01 for all parameters |
| `test_sbc_through_route[ukf]` | **PASSED** | KS p-values: $T_d$: 0.87, $s$: 0.94, $c$: 0.03, $t_{\text{onset}}$: 0.23 |
| `test_sbc_through_route[nuts]` | **PASSED** | KS p-values: $T_d$: 0.26, $s$: 0.97, $c$: 0.77, $t_{\text{onset}}$: 0.22 |
| `test_sbc_through_route[npe]` | **PASSED** | KS p-values: $T_d$: 0.04, $s$: 0.68, $c$: 0.01, $t_{\text{onset}}$: 0.05 |
| `test_routes_agree_with_reference` | **PASSED** | Discrepancy with NUTS 0.7%–9.3% ($\le 30\%$) |
| `test_risk_is_posterior_derived_and_monotone` | **PASSED** | Monotone in growth rate and horizon |
| `test_no_direct_label_head` | **PASSED** | Zero `risk_logit` or `label_head` parameters |
| `test_identifiability_is_computed` | **PASSED** | Fisher Information eigenvalues computed dynamically |
| `test_amortized_route_is_distinct_from_npe` | **PASSED** | Distinct class `AmortizedRecognitionNet`, zero aliases |
| `test_training_is_real` | **PASSED** | Real AdamW loss drop > 0.20; shuffled-pair control drop < 0.05 |
| `test_no_pickled_artifacts` | **PASSED** | Zero `.pt` / `.pkl` files, zero `weights_only=False` |
| `test_k1_discriminates_on_project_simulator` | **PASSED** | AUC 0.5975 $\ge$ max(0.55, last-value 0.5335 - 0.02) |
