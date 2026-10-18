# Study S8-K7: Causal Inference of Treatment Delay and Recurrence (Target-Trial Emulation)

**Study Identifier:** S8-K7
**Module:** K7 (Causal Analysis of Delay and Action) & M7 (Treatment Continuity Harm Model)
**Pre-Registration:** [docs/studies/PREREG-S8-K7.md](file:///docs/studies/PREREG-S8-K7.md)
**Date:** 2026-10-17T19:05:00Z
**Sample Size:** N = 5000 synthetic patients
**Bootstrap Replications:** 1000
**Execution Time:** 66.37s

---

## 1. Primary Target-Trial Emulation Results (Scenario A: Measured Confounding)

Ground truth marginal risk ratio of delayed radiotherapy (> 56 days) on 5-year recurrence: **$\text{RR}^* = 1.1436$**.

| Estimator | Estimated Risk Ratio (RR) | 95% Percentile Bootstrap CI | Absolute Bias ($|\widehat{\text{RR}} - \text{RR}^*|$) |
|---|---|---|---|
| **Augmented Inverse Probability Weighting (AIPW / Doubly Robust)** | **1.1883** | [1.0412, 1.3690] | **0.0447** |
| **Inverse Probability of Treatment Weighting (IPTW)** | 1.1859 | [1.0417, 1.3621] | 0.0423 |
| **G-computation (Outcome Regression)** | 1.1882 | [1.0468, 1.3613] | 0.0446 |
| **Naive Observational Estimator** (Unadjusted Association) | 1.2396 | [1.0998, 1.4104] | 0.0960 |

---

## 2. Covariate Balance Diagnostics

Standardized Mean Differences (SMD) across baseline confounders between delayed and timely radiotherapy:

| Covariate | Unweighted SMD | Weighted SMD (IPTW) | Balance Status ($\text{SMD} < 0.10$) |
|---|---|---|---|
| `subtype_pmrt` | 0.0641 | **0.0003** | BALANCED |
| `subtype_tnbc` | 0.1457 | **0.0090** | BALANCED |
| `age` | 0.1758 | **0.0090** | BALANCED |
| `stage` | 0.0067 | **0.0044** | BALANCED |
| `travel_distance_km` | 0.4756 | **0.0419** | BALANCED |
| `breakdown_exposure` | 0.2743 | **0.0008** | BALANCED |

- **Maximum Weighted SMD:** **0.0419** ($\le 0.10$).
- **Stabilized Weights Diagnostics:** Mean = 0.994, Min = 0.368, Max = 2.202, 99th Percentile = 2.202.

---

## 3. Sensitivity Analysis for Unmeasured Confounding (E-Values)

- **Scenario A (Point Estimate):** E-value = **1.6655** (CI Lower: 1.2483).
- **Scenario B (Injected Unmeasured Confounder $U$):**
  - Observed AIPW estimate without $U$: $\widehat{\text{RR}} = 1.4615$ (95% CI: [1.3136, 1.6321]).
  - E-value for Point Estimate: **2.2828**.
  - **Interpretation:** To explain away the observed effect in Scenario B, an unmeasured confounder must have a risk ratio association of at least **2.28** with both treatment delay and recurrence outcome. This matches the true strength of the injected confounder ($\text{RR} = 2.5 - 3.0$), verifying that E-values accurately identify the threshold for honest failure.

---

## 4. Pre-Registered Hypotheses Evaluation

### Hypothesis H1 (Ground Truth Recovery): SUPPORTED
- Ground truth $\text{RR}^* = 1.1436$ is contained within the AIPW 95% bootstrap CI [1.0412, 1.3690].
- AIPW bias (0.0447) is substantially lower than naive bias (0.0960).

### Hypothesis H2 (Covariate Balance): SUPPORTED
- Maximum weighted SMD is **0.0419** (Target: $< 0.10$).

### Hypothesis H3 (Unmeasured Confounding Detection): SUPPORTED
- E-value threshold is **2.2828** ($\ge 2.0$).
