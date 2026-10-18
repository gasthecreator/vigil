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

## 3. Headline Finding: Estimator Failure Under Unmeasured Confounding and E-Value Quantification

### Scenario B as Headline Finding (Severe Estimator Bias under Unmeasured Confounder $U$)
- **Ground Truth Marginal Effect:** $\text{RR}^* = 1.1247$.
- **Naive Observational Estimator:** $\widehat{\text{RR}} = 1.5085$ (95% CI: [1.3609, 1.6852]).
- **AIPW Estimator:** $\widehat{\text{RR}} = 1.4615$ (95% CI: [1.3136, 1.6321]).
- **Severe Residual Bias:** Absolute bias is $+0.3368$ (about 30% relative inflation). AIPW fails to recover the causal effect when key prognostic factors are unmeasured.
- **Critical Reality Rule:** Nothing in the computational pipeline alerts or flags that the estimator is biased. Without structural verification of unconfoundedness, causal estimators will report spurious effect sizes with false precision.

### Role of the E-Value (Quantification, Not Detection)
- **Scenario B E-value:** **2.2828** (CI Lower: 1.9554).
- **Scenario A E-value:** **1.6655** (CI Lower: 1.2483).
- **Methodological Role:** An E-value does **not** detect confounding; it is a mathematical property of the estimate quantifying the minimum risk ratio association that an unmeasured confounder must have with both treatment delay and recurrence to nullify the point estimate. Here, an unmeasured confounder with $\text{RR} \ge 2.28$ explains away the apparent delay effect, matching the injected synthetic confounder ($\text{RR} \approx 2.5 - 3.0$). Honest finding: **AIPW fails under unmeasured confounding and the E-value only quantifies how strong a confounder would need to be.**

---

## 4. Pre-Registered Hypotheses Evaluation

### Hypothesis H1 (Ground Truth Recovery): SUPPORTED
- Ground truth $\text{RR}^* = 1.1436$ is contained within the AIPW 95% bootstrap CI [1.0412, 1.3690].
- AIPW bias (0.0447) is substantially lower than naive bias (0.0960).

### Hypothesis H2 (Covariate Balance): SUPPORTED
- Maximum weighted SMD is **0.0419** (Target: $< 0.10$).

### Hypothesis H3 (AIPW Failure Under Unmeasured Confounding & E-Value Quantification): CONFIRMED FAILURE MODE
- **Headline Finding:** AIPW fails under unmeasured confounding ($\widehat{\text{RR}} = 1.4615$ vs truth $1.1247$, bias $+0.3368$).
- **E-Value Interpretation:** The E-value (2.2828) quantifies how strong a confounder must be; it does not detect or correct confounding.
- **Verdict:** **CONFIRMED FAILURE MODE** (Pipeline does not detect unmeasured confounding; E-values quantify sensitivity bounds).

