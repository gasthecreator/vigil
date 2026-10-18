# Pre-Registration: Study S8-K7 — Causal Inference of Treatment Delay and Recurrence (Target-Trial Emulation)

**Study Identifier:** S8-K7  
**Module:** K7 (Causal Analysis of Delay and Action) & M7 (Treatment Continuity Harm Model)  
**Document:** `docs/studies/PREREG-S8-K7.md`  
**Reference:** `docs/ML_PROGRAM.md` §3.7, §6 (Study S8)  
**Date:** 2026-10-17  
**Status:** PRE-REGISTERED (Committed prior to execution)  

---

## 1. Scientific Objective
Evaluate whether doubly-robust and propensity-weighted causal estimators (IPTW, AIPW / Doubly-Robust) recover known synthetic treatment delay effects on 5-year breast cancer recurrence under realistic clinical confounding (indication, subtype, stage, geography, and socio-demographics), and verify that VanderWeele & Ding E-value sensitivity analysis correctly flags honest failure when unmeasured confounding is present.

---

## 2. Target-Trial Emulation Protocol (Hernán & Robins 2016)

| Target Trial Component | Emulation in Observational / Synthetic Cohort |
|---|---|
| **Eligibility Criteria** | Adult women ($\ge 18$ years) with histologically confirmed Stage I–III invasive breast carcinoma following definitive surgical resection (lumpectomy or mastectomy) with clinical indication for adjuvant radiotherapy. |
| **Treatment Strategies** | **Arm 0 (Timely RT):** Radiation therapy initiated $\le 56$ calendar days (8 weeks) following surgical resection.<br>**Arm 1 (Delayed RT):** Radiation therapy initiated $> 56$ calendar days following resection. |
| **Assignment Procedure** | Observational assignment emulated under conditional exchangeability given measured clinical and access confounders: breast cancer subtype (Lumpectomy ER+, PMRT High-Risk, Curative TNBC), tumor stage, age, travel distance (km), and facility equipment breakdown exposure. |
| **Time Zero ($T_0$)** | Date of definitive surgical resection (lumpectomy or mastectomy). |
| **Follow-up & Outcome** | 5-year locoregional recurrence or distant metastasis (binary 5-year recurrence indicator). |
| **Causal Contrast** | Marginal Risk Ratio ($\text{RR}$) and Average Treatment Effect on the Treated ($\text{ATT}$) of Delayed vs. Timely RT. |
| **Analysis Plan** | Primary: Augmented Inverse Probability Weighting (AIPW / Doubly Robust) with cross-fitting.<br>Secondary: Stabilized Inverse Probability of Treatment Weighting (IPTW), G-computation (outcome modeling), Naive unadjusted observational estimator. |

---

## 3. Causal Identification Assumptions
1. **Conditional Exchangeability (No Unmeasured Confounding):**  
   $$Y(a) \perp\!\!\perp A \mid X$$  
   where $Y(a)$ is the potential recurrence outcome under treatment strategy $a \in \{0, 1\}$, $A$ is the treatment indicator, and $X$ is the vector of measured baseline confounders.
2. **Positivity:**  
   $$0.01 < P(A = 1 \mid X = x) < 0.99 \quad \forall x \in \text{supp}(X)$$  
   Diagnosed via propensity score overlap plots and maximum stabilized weights $\le 10.0$.
3. **Consistency & SUTVA:**  
   $Y = A Y(1) + (1 - A) Y(0)$; no interference between patients regarding radiation biological efficacy.

---

## 4. Estimator Specifications
1. **Naive Observational Estimator:** Unadjusted empirical risk ratio:
   $$\widehat{\text{RR}}_{\text{naive}} = \frac{\bar{Y}_{A=1}}{\bar{Y}_{A=0}}$$
2. **Inverse Probability of Treatment Weighting (IPTW):**
   Propensity model $e(X) = P(A=1 \mid X)$ estimated via logistic regression. Stabilized weights:
   $$W_i = A_i \frac{P(A=1)}{e(X_i)} + (1 - A_i) \frac{P(A=0)}{1 - e(X_i)}$$
   Truncated at 99th percentile to enforce positivity bounds.
3. **Augmented Inverse Probability Weighting (AIPW / Doubly Robust):**
   Combines propensity model $e(X)$ and outcome regression models $\mu_a(X) = E[Y \mid A=a, X]$:
   $$\widehat{\mu}_1 = \frac{1}{N} \sum_{i=1}^N \left[ \frac{A_i Y_i}{e(X_i)} - \frac{A_i - e(X_i)}{e(X_i)} \mu_1(X_i) \right]$$
   $$\widehat{\mu}_0 = \frac{1}{N} \sum_{i=1}^N \left[ \frac{(1 - A_i) Y_i}{1 - e(X_i)} + \frac{A_i - e(X_i)}{1 - e(X_i)} \mu_0(X_i) \right]$$
   $$\widehat{\text{RR}}_{\text{AIPW}} = \frac{\widehat{\mu}_1}{\widehat{\mu}_0}$$
4. **Sensitivity Analysis (E-Values):**
   VanderWeele & Ding (2017) E-value for the point estimate and lower confidence limit:
   $$\text{E-value} = \text{RR} + \sqrt{\text{RR}(\text{RR} - 1)}$$

---

## 5. Pre-Registered Hypotheses

### Hypothesis H1 — Recovery of Ground Truth Effect under Confounding
* **Statement:** Under measured confounding by clinical indication and healthcare access, AIPW and IPTW will recover the known ground-truth risk ratio ($\text{RR}^* \approx 1.15$) within the 95% paired bootstrap confidence interval:
  $$\text{RR}^* \in [\text{CI}_{\text{lower}}, \text{CI}_{\text{upper}}]$$
  whereas the Naive unadjusted estimator will exhibit significant confounding bias ($|\widehat{\text{RR}}_{\text{naive}} - \text{RR}^*| > |\widehat{\text{RR}}_{\text{AIPW}} - \text{RR}^*|$).

### Hypothesis H2 — Covariate Balance Post-Weighting
* **Statement:** IPTW weighting will balance all measured baseline confounders between delayed and timely groups, achieving absolute Standardized Mean Differences ($\text{SMD}$) $< 0.10$ for all covariates.

### Hypothesis H3 — Sensitivity to Injected Unmeasured Confounding (Honest Failure)
* **Statement:** When an unmeasured aggressive biology confounder ($U \sim \text{Bernoulli}(0.3)$) is injected that increases both treatment delay ($\text{OR} = 3.0$) and recurrence hazard ($\text{RR} = 2.5$), the causal estimators without $U$ will exhibit bias, but the computed E-value will correctly indicate that an unmeasured confounder with strength $\ge 2.5$ is sufficient to explain the discrepancy.

---

## 6. Experimental Design & Statistical Analysis
- **Cohort Size:** $N = 5,000$ synthetic patient trajectories generated from `vigil-sim` / known data-generating process with realistic Nigerian tertiary center distributions.
- **Uncertainty Quantification:** 1,000 bootstrap resamples for all risk ratios and causal contrasts.
- **Reporting Protocol:** All estimators (Naive, IPTW, AIPW, G-computation) reported side-by-side with SMD balance tables, propensity overlap histograms, and E-values.
