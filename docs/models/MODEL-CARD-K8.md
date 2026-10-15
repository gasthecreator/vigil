# Model Card: Model K8 — Conformal Risk Control & Production Stacking Ensemble

**Model Identifier:** `MODEL-K8-CONFORMAL-ENSEMBLE`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.3; `docs/ML_PROGRAM.md` §3.3, §6, §9  
**Evaluation Status:** Evaluated on VigilBench G1, G2, G3 (`reports/ml/BENCHMARK_REPORT.md`)  

---

## 1. Model Overview and Intended Use
Model K8 is the production integration model of the Vigil surveillance suite. It unifies Vigil's diverse algorithmic paradigms—mechanistic ODE state-space modeling (K1), Bayesian joint longitudinal–survival modeling (K3), deep irregular-time neural architectures (K4), and regularized non-linear gradient boosted trees (B4)—into a calibrated stacking ensemble governed by distribution-free Conformal Risk Control (CRC).

### Core Components
1. **Calibrated Stacking Ensemble:** Blends predictions using validation-optimized meta-weights:
   - Model K1 (Kinetic Mechanistic ODE): $0.35$
   - Model K3 (Fast Landmark Joint Model): $0.25$
   - Model K4 (Deep Irregular Zoo): $0.20$
   - Model B4 (Gradient Boosted Trees): $0.20$
2. **Conformal Risk Control (CRC):** Guarantees a user-specified bound on the False Negative Rate ($\operatorname{FNR} \le \alpha_{\text{conf}}$) on unseen test distributions without parametric distributional assumptions (Angelopoulos et al. 2021).
3. **Adaptive Conformal Inference (ACI):** Online threshold tracking adapting to non-stationary hospital environment drifts (Gibbs & Candès 2021).
4. **Out-of-Distribution (OOD) Detector & Abstention Policy:** Rejects physiological anomalies and extreme epistemic uncertainty before generating clinical recommendations.

---

## 2. Mathematical Formulation & Guarantees
### Conformal Risk Control
Given validation calibration set $\{(X_i, Y_i)\}_{i=1}^n$ and loss function $L(f(X), Y) = \mathbf{1}\{Y=1, f(X) < \lambda\}$ (false negative indicator):
$$\hat{R}_n(\lambda) = \frac{1}{n_{\text{pos}}} \sum_{i: Y_i=1} \mathbf{1}\{f(X_i) < \lambda\}$$
Operating threshold $\hat{\lambda}$ is chosen such that:
$$\mathbb{E}[L(f(X_{n+1}), Y_{n+1})] \le \alpha_{\text{conf}}$$

### Adaptive Conformal Inference (ACI) Step
At step $t$ upon observing true outcome $Y_t$:
$$\lambda_{t+1} = \begin{cases}
\lambda_t - \gamma & \text{if } Y_t = 1 \text{ and } \hat{Y}_t = 0 \text{ (False Negative)} \\
\lambda_t + \gamma \alpha_{\text{conf}} & \text{if } Y_t = 0 \text{ and } \hat{Y}_t = 1 \text{ (False Alarm)} \\
\lambda_t & \text{otherwise}
\end{cases}$$

### Out-of-Distribution Mahalanobis Detector
$$D_M(x)^2 = (x - \mu)^\top \Sigma^{-1} (x - \mu)$$
If $D_M(x)^2 > \chi^2_{p, 0.9999}$, the engine triggers `ABSTAIN_OOD`, refusing to score unphysiological laboratory inputs.

---

## 3. VigilBench Benchmark Performance
- **Discrimination (IPCW ROC-AUC at 365 Days):**
  - Visit depth $V = 3$: $0.782$ $[0.741, 0.824]$
  - Visit depth $V = 10$: $0.824$ $[0.789, 0.858]$
  - Visit depth $V = 20$: $0.835$ $[0.801, 0.869]$
- **Calibration (Brier & ECE):** Brier Score $0.081$, Expected Calibration Error $\le 0.042$.
- **Preclinical Lead Time:** Median conditional lead time $248.5\text{ days}$ prior to clinical symptom threshold.
- **Workstation Inference Latency:** Single-patient evaluation $p95 = 2.15\text{ ms}$ on workstation CPU, easily exceeding the $< 100\text{ ms}$ budget.

---

## 4. Abstention & Safety Protocol
When K8 encounters inputs that violate clinical validity assumptions, it emits an explicit abstention code rather than an uncalibrated score:
- `ABSTAIN_OOD`: Mahalanobis distance exceeds critical chi-squared threshold.
- `ABSTAIN_HIGH_UNCERTAINTY`: Epistemic standard deviation between constituent models exceeds $0.25$.
- `ABSTAIN_MISSING_KEY_MARKERS`: Essential serial measurements missing with no historical baseline.
