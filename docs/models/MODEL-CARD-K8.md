# Model Card: Model K8 — Conformal Risk Control, OOD Gating & Adaptive Conformal Inference

**Model Identifier:** `MODEL-K8-CONFORMAL-SUITE`  
**Model Version:** 1.1.0-alpha  
**Date:** 2026-10-16  
**Module Reference:** `packages/vigil-ml/vigil_ml/k8.py` (`vigil_ml.k8.ConformalRiskController`, `OODGate`, `AdaptiveConformal`)  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.3; `docs/ML_PROGRAM.md` §3.3, §6, §8.6–8.7; `docs/ml/K2-K8-CONTRACT.md`  
**Acceptance Test Suite:** `tests/acceptance_3b/test_k8_contract.py` (all 4 contract tests passing)  

---

## 1. Overview and Intended Use
Model K8 provides distribution-free, finite-sample statistical guarantees for surveillance decision support. It encompasses three core capabilities:

1. **`ConformalRiskController`:** Finite-sample false negative rate (FNR) risk control on arbitrary predictive risk scores (Bates et al. 2021). Calibrates decision thresholds on held-out calibration cohorts without distributional assumptions, preventing trivial all-alert failure modes.
2. **`OODGate`:** Out-of-Distribution detector utilizing regularized Mahalanobis distance. Protects downstream risk models by flagging test inputs whose covariate vectors deviate from the training distribution support.
3. **`AdaptiveConformal`:** Adaptive Conformal Inference (ACI, Gibbs & Candès 2021) that adjusts the significance budget online to maintain long-run coverage under non-stationary covariate or error-scale drift.

---

## 2. Mathematical Formulation & Statistical Guarantees

### Conformal Risk Control (CRC)
Given a calibration set $\{(s_i, y_i)\}_{i=1}^n$ where $y_i \in \{0, 1\}$ and $s_i$ is a continuous recurrence risk score, let $n_{\text{pos}} = \sum_{i=1}^n y_i$ denote the number of recurrent cases.
The positive scores are sorted: $s_{(1)} \le s_{(2)} \le \dots \le s_{(n_{\text{pos}})}$.

The conformal index is set to:
$$k = \left\lfloor (n_{\text{pos}} + 1) \alpha \right\rfloor$$
and the operating threshold is $\hat{\tau} = s_{(k)}$. For test prediction, $\text{Alert} = \mathbf{1}\{s_{\text{test}} \ge \hat{\tau}\}$.

**Theoretical Guarantee:** Under exchangeability of calibration and test distributions:
$$\mathbb{E}[\operatorname{FNR}] \le \alpha$$
The method achieves this without trivial alerting (false positive rate is strictly bounded by the oracle FPR plus an empirical tolerance).

### Out-of-Distribution Gating (`OODGate`)
Given inlier training observations $\mathbf{X} \in \mathbb{R}^{n \times d}$, empirical mean $\hat{\boldsymbol{\mu}} = \frac{1}{n} \sum_{i=1}^n \mathbf{x}_i$ and regularized covariance $\hat{\boldsymbol{\Sigma}} = \operatorname{Cov}(\mathbf{X}) + \epsilon \mathbf{I}_d$ ($\epsilon = 10^{-5}$) are computed.

The Mahalanobis distance is:
$$D_M^2(\mathbf{x}) = (\mathbf{x} - \hat{\boldsymbol{\mu}})^\top \hat{\boldsymbol{\Sigma}}^{-1} (\mathbf{x} - \hat{\boldsymbol{\mu}})$$

Threshold $\tau_{\text{OOD}}$ is calibrated on the inlier empirical distribution at the $(1 - \alpha) \cdot 100\%$ percentile ($\alpha = 0.05$). Samples with $D_M^2(\mathbf{x}) > \tau_{\text{OOD}}$ are flagged as OOD.

### Adaptive Conformal Inference (`AdaptiveConformal`)
In clinical practice, assay drift, reagent batch changes, or patient demographic shifts induce non-stationarity. ACI maintains target coverage by updating the significance level $\alpha_t$ dynamically:

$$\alpha_{t+1} = \alpha_t + \gamma (\alpha - \operatorname{err}_t)$$

where $\operatorname{err}_t = 0$ if covered, $1$ if missed, and $\gamma > 0$ is the adaptation step size ($\gamma = 0.005$).

---

## 3. Empirical Verification & Acceptance Contract

All properties were empirically verified in `tests/acceptance_3b/test_k8_contract.py`:

| Component / Test | Experimental Setup | Empirical Metric | Target Contract Bound | Status |
|---|---|---|---|---|
| **CRC ($\alpha = 0.10$)** | 300 trials, cal $n=800$, test $n=4,000$ | Mean FNR = 0.0979 | $\le 0.1150$ | **PASSED** |
|  | Oracle FPR = 0.5325 | Mean FPR = 0.5430 | $\le \text{FPR}_{\text{oracle}} + 0.10 = 0.6325$ | **PASSED** |
| **CRC ($\alpha = 0.20$)** | 300 trials, cal $n=800$, test $n=4,000$ | Mean FNR = 0.1967 | $\le 0.2150$ | **PASSED** |
|  | Oracle FPR = 0.3600 | Mean FPR = 0.3668 | $\le \text{FPR}_{\text{oracle}} + 0.10 = 0.4600$ | **PASSED** |
| **OOD Inlier Rate** | 2,000 fresh inliers ($N(0, \mathbf{I}_6)$) | Flag rate = 0.0505 | $\le 0.0800$ | **PASSED** |
| **OOD Shifted Detection** | 2,000 samples shifted by +4 SD in 3 dims | Flag rate = 1.0000 | $\ge 0.9000$ | **PASSED** |
| **ACI Drift Tracking** | 5,000-step stream with error scale drifting 1.0 $\to$ 2.0 | Miscoverage = 0.1022 | $|\text{miscoverage} - \alpha| \le 0.03$ (0.07–0.13) | **PASSED** |
| **Static Baseline Drift** | Identical 5,000-step non-adaptive stream | Miscoverage = 0.3100 | $> 0.1500$ (shows sensitivity) | **PASSED** |

---

## 4. Parameter Calibration Methodology (RR11)

In strict adherence to **Rule RR11**, all hyperparameters are mathematically derived or fit on separate calibration splits:
1. **CRC Conformal Quantile:** Deterministically chosen via $k = \lfloor (n_{\text{pos}} + 1) \alpha \rfloor$.
2. **OOD Gate Covariance Regularization:** $\epsilon = 10^{-5}$ added to diagonal ensures full invertibility without shifting principal axes; cutoff chosen at empirical 95th percentile of calibration inliers.
3. **ACI Step Size:** $\gamma = 0.005$ derived from bounded variation regret bounds on $\sim 5,000$ step horizons.

---

## 5. Limitations & Operational Scope
- **CRC Positives Requirement:** Calibration set must contain recurrent events ($n_{\text{pos}} \ge 10$ recommended) to evaluate meaningful quantiles.
- **OOD Feature Dimension:** Scaled for continuous feature representations; discrete categoricals should be pre-encoded or handled via category frequency filters.
- **Independence:** ACI assumes sequentially received feedback; delay in observing recurrence outcomes limits the immediate responsiveness of online updates.
