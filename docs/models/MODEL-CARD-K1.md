# Model Card: Model K1 — Hybrid Mechanistic–Neural State-Space Model ("Kinetic")

**Model Identifier:** `MODEL-K1-KINETIC-HYBRID`  
**Model Version:** 1.1.0-phase3a  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0 (Phase 3A); `docs/ML_PROGRAM.md` §3.1, §6, §9  
**Evaluation Status:** Evaluated on Synthetic Tiers G1, G2, G3 (`reports/ml/BENCHMARK_REPORT.md`, `reports/ml/S1_SPARSITY/REPORT.md`)  

---

## 1. Model Overview & Intended Use
Model K1 is Vigil's flagship continuous-time mechanistic surveillance model. Rather than treating serial laboratory measurements as ungrounded tabular sequences, K1 models them as noisy, discrete observations of an underlying 9-dimensional continuous biological state vector $z(t)$ governing post-treatment breast cancer recurrence.

### Primary Intended Use
Continuous prospective estimation of subclinical metastatic tumor burden across anatomical compartments (locoregional, bone, liver, lung, brain), tumor doubling time $T_d$, and 1-year horizon recurrence probability $P(T \le t + 365 \mid \mathcal{H}_t)$ with credible intervals.

---

## 2. Mathematical Formulation & Latent State Dynamics

### 2.1 Latent State Vector $z(t) \in \mathbb{R}^9$
- Compartmental burdens: $b(t) = [B_{\text{loco}}, B_{\text{bone}}, B_{\text{liver}}, B_{\text{lung}}, B_{\text{brain}}]^T$
- Circulating marker pools: $m(t) = [M_{\text{ca153}}, M_{\text{cea}}]^T$
- Coupled organ injury states: $o(t) = [O_{\text{liver}}, O_{\text{bone}}]^T$

### 2.2 Continuous Differential Equations (SDE / ODE)
1. **Tumor Burden Outgrowth:**
   $$\frac{d B_c}{dt} = g_c (1 - \alpha_{\text{treat}} a(t)) B_c \left[1 - \frac{B_c}{K}\right]^+ + f_\theta(z(t), a(t), t)_c$$
   where $g_c \in [0.005, 0.065]\,\text{day}^{-1}$ is the compartment-specific growth rate (corresponding to tumor doubling time $T_d = \frac{\ln 2}{g_c} \in [11, 140]\,\text{days}$), $K = 1000.0$ mass units saturation limit, $a(t)$ is adjuvant therapy status, and $f_\theta$ is a bounded Lipschitz neural residual drift ($\|f_\theta\|_\infty \le 0.05$).

2. **Circulating Biomarker Kinetics (Filtered Integrals):**
   $$\frac{d M_k}{dt} = \sum_{c=1}^5 s_{k,c} B_c - c_k M_k$$
   where $s_{k,c}$ are shedding rates, and $c_k$ are physiological first-order clearance rates:
   - CA 15-3: $c_0 = 0.085\,\text{day}^{-1}$ (half-life $t_{1/2} = \frac{\ln 2}{0.085} \approx 8.2\,\text{days}$, Evidence E9).
   - CEA: $c_1 = 0.140\,\text{day}^{-1}$ (half-life $t_{1/2} = \frac{\ln 2}{0.140} \approx 5.0\,\text{days}$, Evidence E1).

3. **Organ Dysfunction Coupling:**
   $$\frac{d O_{\text{liver}}}{dt} = \gamma_{\text{liver}} B_{\text{liver}} - \delta_{\text{liver}} O_{\text{liver}} + \beta_{\text{chemo}} a_{\text{chemo}}(t)$$
   $$\frac{d O_{\text{bone}}}{dt} = \gamma_{\text{bone}} B_{\text{bone}} - \delta_{\text{bone}} O_{\text{bone}}$$
   coupling metastatic parenchymal infiltration to serum transaminases (ALT/AST) and osteolytic turnover to alkaline phosphatase (ALP).

### 2.3 Numerical Integration
Implemented via 4th-order Runge-Kutta (`rk4_step` / `integrate`):
$$z(t + \Delta t) = z(t) + \frac{\Delta t}{6}(k_1 + 2k_2 + 2k_3 + k_4)$$
Verified against analytical closed-form solutions:
- Pure marker clearance ($B=0$): $M(t) = M(0) e^{-c t}$ (relative error $< 10^{-4}$).
- Uncoupled exponential growth ($B \ll K$): $B(t) = B(0) e^{g t}$ (relative error $< 5 \times 10^{-3}$).
- Step-size convergence: truncation error decreases by order $\ge O(\Delta t^2)$ upon halving step size.

---

## 3. Inference Routes

1. **Amortized Variational Inference (`AmortizedRecognitionNetwork`):**
   - Neural recognition network $q_\phi(z_0, g \mid \mathcal{H}_t)$ encoding clinical history into posterior distributions over initial burden and growth kinetics.
   - Genuinely trained via Adam optimizer ($lr = 10^{-3}$, weight decay $10^{-4}$) on patient-split cohorts, logging train and validation losses per epoch.

2. **Online Continuous-Discrete Filter (`UnscentedKalmanFilterK1`):**
   - Sub-10ms sequential filtering ($< 1.0\text{ ms}$ per visit on CPU) updating latent state as new laboratory results arrive.
   - Includes real-time filter consistency checks evaluating **Normalized Innovation Squared (NIS)** against 95% $\chi^2$ confidence bounds:
     $$\epsilon_{\nu, j} = \tilde{y}_j^T S_j^{-1} \tilde{y}_j \in [\chi^2_{0.025}/N, \chi^2_{0.975}/N]$$

3. **Reference Gold-Standard & SBI Inversion:**
   - Numerical ODE inversion via bounded scalar optimization for parameter recovery.
   - Exact likelihood grid posterior evaluation for Simulation-Based Calibration (SBC).

---

## 4. Empirical Performance & Study S1 Benchmark Results

Evaluated under pre-registered protocol in Study S1 on $N=1,000$ held-out synthetic patients across visit depths $V \in \{3, 4, 6, 10, 20\}$:

| Metric | V=3 (Sparse) | V=4 | V=6 | V=10 (Standard) | V=20 (Dense) |
|---|---|---|---|---|---|
| **IPCW ROC-AUC** | 0.7077 [0.682, 0.738] | 0.7549 [0.731, 0.775] | 0.7823 [0.765, 0.804] | **0.7953** [0.776, 0.818] | 0.7995 [0.780, 0.815] |
| **Brier Score** | 0.2030 | 0.1770 | 0.1565 | 0.1487 | 0.1485 |
| **ECE** | 0.1276 | 0.1351 | 0.1344 | 0.1412 | 0.1419 |
| **Net Benefit ($p_t=0.15$)** | 0.3112 | 0.2520 | 0.1985 | 0.1724 | 0.1718 |
| **Lead Time (5% alert rate)**| 38.5 days | 38.5 days | 38.5 days | **38.5 days** | 38.5 days |
| **Latency (p95 CPU)** | — | — | — | **0.84 ms** | — |

---

## 5. What is Real, What is Estimated, and What Underperformed

### 5.1 What is Real
- **Continuous Numerical Integration:** Real 9-compartment RK4 continuous-time integration with closed-form unit tests and step-size convergence verification.
- **Genuine Neural Training:** `fit()` performs real backpropagation via Adam, logging train/val losses per epoch on patient-level splits.
- **Posterior Risk Derivation:** `predict_risk()` rolls forward posterior samples through kinetic dynamics to compute the prospective recurrence integral exceeding detection mass $B_{\text{det}} = 12.0$.
- **Online Filtering & Consistency:** UKF evaluates Normalized Innovation Squared (NIS) against theoretical $\chi^2$ bounds.
- **Simulation-Based Calibration (SBC):** SBC rank statistics evaluated against uniform distribution via Kolmogorov-Smirnov test ($p = 0.4588 > 0.01$, PASSED).
- **Parameter Recovery:** Tumor doubling time recovery achieves Pearson $r = 0.8706$ with $88.0\%$ empirical 90% credible interval coverage (PASSED).

### 5.2 What is Estimated
- **Tumor Doubling Time ($T_d$):** Estimated from longitudinal analyte trajectories via numerical ODE inversion.
- **Subclinical Burden ($B_{\text{total}}$):** Inferred latent cell mass (arbitrary units, detection threshold 12.0).
- **Organ Damage Coupling:** Estimated from transaminase and alkaline phosphatase trajectories.

### 5.3 What Underperformed / Limitations
- **Identifiability Under Sparse Schedules:** Structural identifiability analysis demonstrates that while aggregate growth rate $g$, total shedding $s$, and clearance $c$ are well-conditioned (positive Fisher information eigenvalues), individual compartment shedding rates ($s_{\text{loc}}, s_{\text{lung}}, s_{\text{brain}}$) are collinear and non-identifiable without organ-specific imaging or tissue biopsies. Regularizing shrinkage priors are mandatory.
- **Calibration Error (ECE 0.1412):** Raw kinetic risk outputs exhibit higher calibration error than the landmark baseline (K3 ECE 0.0202), caused by the sigmoid threshold mapping on latent burden. Conformal temperature scaling and recalibration (Phase 3B) are required before release.
- **Lead Time at Low Alert Rate:** At a strict 5% visit alert rate constraint, median lead time is 38.5 days. Unconstrained thresholding yields longer lead times (~115 days) but at the expense of higher false alarm rates.
