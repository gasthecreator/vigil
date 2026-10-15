# Study S3 Pre-Registration: Partial Verification Bias Correction

**Study ID:** S3_VERIFICATION_BIAS  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.1/WP2.4; `docs/ML_PROGRAM.md` §6, §9  

---

## 1. Study Objective and Research Question
In real-world oncology follow-up and surveillance cohorts, definitive disease verification (PET/CT, MRI, biopsy) is not performed randomly. Clinicians selectively order imaging for patients with elevated biomarker trajectories or clinical symptoms. If an evaluation harness assesses risk models only on verified patients ("complete-case analysis"), diagnostic accuracy metrics suffer severe partial verification bias (typically underestimating specificity and overestimating sensitivity).

**Core Question:** By how much does naive complete-case analysis distort surveillance performance relative to ground-truth disease state in simulation, and which correction estimator (Inverse Probability Weighting vs. Latent-Class EM) recovers the true population sensitivity and specificity with minimal bias?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Complete-Case Distortion):** Naive complete-case evaluation will underestimate population true-negative rate (specificity) by $> 10$ percentage points compared to true latent disease status, because non-verified asymptomatic patients (who are overwhelmingly disease-free) are discarded.
2. **H2 (IPW Recovery):** Inverse Probability Weighting (IPW) using estimated verification propensity scores:
   $$e(X) = P(V=1 \mid X)$$
   will reduce bias in sensitivity and specificity to $< 3$ percentage points when verification is missing at random (MAR) conditional on observed biomarker levels.
3. **H3 (Latent-Class Robustness):** Latent-class Expectation-Maximization (EM) will maintain robust discrimination bounds even when verification imaging sensitivity is imperfect ($< 1.0$).

---

## 3. Evaluated Estimators
- **Estimator 1 (Complete-Case):** Conventional unadjusted evaluation restricted strictly to patients receiving confirmatory imaging ($V_i = 1$).
- **Estimator 2 (IPW - Inverse Probability Weighting):** Propensity-score reweighted estimator where each verified case is weighted by $1 / \hat{e}(X_i)$ to re-establish population representation.
- **Estimator 3 (Latent-Class EM):** Expectation-Maximization estimator treating unverified disease status as a latent variable with parameter priors.

---

## 4. Simulation Environment and Verification Mechanism
- **Data Generator:** Synthetic G1 Multi-Compartment Simulator with enabled selective imaging policy (`selective_imaging = True`).
- **Verification Model:**
  $$P(V_i = 1 \mid \text{CA 15-3}_i, \text{Symptoms}_i) = \text{logit}^{-1}\left(\gamma_0 + \gamma_1 \log(\text{CA 15-3}_i) + \gamma_2 \text{Symptom}_i\right)$$
  Calibrated such that overall imaging verification rate is $\approx 25\text{--}35\%$ of the cohort.
- **Sample Size:** $N = 2,500$ patients with ground-truth latent disease status preserved for unbiased recovery benchmark.
- **Replications:** 10 independent Monte Carlo replications with fixed seeds (101..110).

---

## 5. Endpoints and Assessment Metrics
1. **Absolute Parameter Bias:**
   $$\text{Bias}(\text{Sens}) = |\hat{\text{Sens}} - \text{Sens}_{\text{true}}|$$
   $$\text{Bias}(\text{Spec}) = |\hat{\text{Spec}} - \text{Spec}_{\text{true}}|$$
2. **Corrected ROC-AUC:** Area under the verification-adjusted ROC curve compared to the oracle full-cohort ROC curve.
3. **Confidence Interval Coverage:** 95% empirical bootstrap coverage under 1,000 resamples.

---

## 6. Pre-Registered Protocol and Fallback
- Report all three estimators transparently alongside oracle ground-truth in `reports/ml/S3_VERIFICATION_BIAS/REPORT.md`.
- Ship the estimator that minimizes total mean squared error ($\text{MSE} = \text{Bias}^2 + \text{Var}$) across simulation replications as the default production evaluation setting in `vigil-eval`.
