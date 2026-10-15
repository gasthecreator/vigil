# Study S2 Pre-Registration: Anytime-Valid Sequential Detection Under Repeated Looks

**Study ID:** S2_SEQUENTIAL  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-B), §3.2, §6  

---

## 1. Study Objective and Research Question
In oncology surveillance, risk models are evaluated repeatedly over multi-year follow-up (up to 20 serial visits). Under standard per-visit thresholding or per-visit conformal prediction, the cumulative patient-level false alarm rate dramatically inflates beyond the nominal $\alpha$ level ($1 - (1 - \alpha)^K \gg \alpha$).

**Core Question:** Does the K2 anytime-valid test supermartingale (e-process) rigorously bound the cumulative patient-level false alarm rate ($P_0(\exists t \le K: E_t \ge 1/\alpha_{\text{pt}}) \le \alpha_{\text{pt}}$) under repeated serial evaluations across 5 null scenarios, while minimizing detection delay relative to fixed-threshold rules?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Cumulative Error Inflation of Static Rules):** Static threshold rules (e.g. CA 15-3 $\ge 30$ U/mL) evaluated at each of $K=15$ visits will exhibit cumulative patient-level false-alarm rates exceeding $0.35$, violating nominal clinical false positive budgets.
2. **H2 (Supermartingale Guarantee):** The K2 mixture e-process will maintain empirical patient-level false-alarm rate $\le \alpha_{\text{pt}} + 0.02$ across all 5 null stress scenarios (biological variation, heavy tails, lab assay shift, transient hepatotoxicity, severe MNAR missingness).
3. **H3 (Detection Delay Advantage):** Under true metastatic progression, K2 will achieve shorter expected detection delay ($EDD$) than static single-threshold rules by accumulating evidence over sequential visits.

---

## 3. Evaluated Models
- **M-Static (Single Threshold Rule):** CA 15-3 $\ge 30.0$ U/mL evaluated per-visit.
- **M-CUSUM (Page's CUSUM Chart):** Sequential Cumulative Sum detector with reference allowance $k=0.5$ and control limit $h=4.0$.
- **M-Shiryaev (Shiryaev-Roberts):** Optimal changepoint statistic with equal weighting.
- **K2 (Anytime-Valid Mixture e-Process):** Nonnegative test supermartingale integrating over candidate doubling times with Ville's inequality threshold $1/\alpha_{\text{pt}}$.

---

## 4. Evaluated Scenarios & Cohorts
- **Sample Size:** $N = 500$ null synthetic patients evaluated over $K=15$ serial visits for each scenario.
- **Null Scenarios (Stress Suite):**
  1. Standard Gaussian biological variation ($\sigma = 2.2$).
  2. Heavy-tailed Student-t noise ($\text{df} = 3, \sigma = 2.5$).
  3. Inter-laboratory assay step change ($+4.5\text{ U/mL}$ at visit 8).
  4. Adjuvant therapy transient hepatotoxicity spike ($+12\text{ U/mL}$ at visit 5).
  5. Informative MNAR missingness (35% skipped tests during quiescent intervals).

---

## 5. Primary and Secondary Endpoints
1. **Primary Metric:** Empirical patient-level false alarm rate under the null ($\text{FAR}_{\text{pt}} = \frac{1}{N} \sum_{i=1}^N \mathbf{1}\{\exists t \le K : \text{Alert}_{i,t}\}$).
2. **Secondary Metrics:**
   - Average Run Length under null ($ARL_0$).
   - Expected Detection Delay ($EDD$) in days on progressive recurrences.
   - Alert burden per recurrence detected.

---

## 6. Pre-Registered Kill Criterion
If the learned e-process violates the nominal $\alpha_{\text{pt}} + 0.02$ bound in more than one null stress scenario, the learned score function is rejected and Vigil falls back to the K1-likelihood-ratio e-process per ML_PROGRAM §3.2.
