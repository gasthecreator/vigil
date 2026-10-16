# Study S2 Pre-Registration: Anytime-Valid Sequential Detection Under Repeated Looks

**Study ID:** S2_SEQUENTIAL  
**Protocol Version:** 1.1  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-16  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-B), §3.2, §6; `docs/REALITY_RULES.md` RR14  

---

## 1. Study Objective and Research Question
In oncology surveillance, risk models are evaluated repeatedly over multi-year follow-up (up to 20 serial visits). Under standard per-visit thresholding or per-visit conformal prediction, the cumulative patient-level false alarm rate dramatically inflates beyond the nominal $\alpha$ level ($1 - (1 - \alpha)^K \gg \alpha$).

**Core Question:** Does the Model K2 anytime-valid test supermartingale (`vigil_ml.k2.SequentialDetector`) rigorously bound the cumulative patient-level false alarm rate ($P_0(\exists t \le K: E_t \ge 1/\alpha_{\text{pt}}) \le \alpha_{\text{pt}}$) under repeated serial evaluations across project simulator (`vigil-sim`) nulls and the 5 null stress scenarios, while preserving power and minimizing detection delay on progressive recurrences relative to fixed-threshold rules?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Cumulative Error Inflation of Static Rules):** Static threshold rules (e.g. CA 15-3 $\ge 30$ U/mL or calibrated per-visit $\alpha$) evaluated at each serial visit will exhibit cumulative patient-level false-alarm rates exceeding the single-look nominal budget, violating nominal clinical false positive budgets.
2. **H2 (Supermartingale Guarantee):** The K2 mixture e-process (`SequentialDetector`) will maintain empirical patient-level false-alarm rate $\le \alpha_{\text{pt}} + 0.02$ across all null scenarios (including `vigil-sim` null trajectories, Gaussian variations, heavy tails, lab assay shift, and missingness).
3. **H3 (Detection Delay and Power):** Under true progressive recurrences in `vigil-sim` and synthetic kinetic streams, K2 will achieve bounded detection delay with $\ge 75\%$ power on moderate growth ($T_d \le 90$d) and $\ge 85\%$ on rapid growth ($T_d \le 60$d).

---

## 3. Evaluated Models
- **M-Static (Single Threshold Rule):** CA 15-3 $\ge 30.0$ U/mL evaluated per-visit.
- **M-CUSUM (Page's CUSUM Chart):** Sequential Cumulative Sum detector with reference allowance $k=0.5$ and control limit $h=4.0$.
- **M-Shiryaev (Shiryaev-Roberts):** Optimal changepoint statistic with equal weighting.
- **K2 (Anytime-Valid Mixture e-Process):** `vigil_ml.k2.SequentialDetector` with Ville's inequality threshold $1/\alpha_{\text{pt}}$.

---

## 4. Evaluated Scenarios & Cohorts
1. **Project Simulator (`vigil-sim`) Cohort (Seed 42, N=500 patients):**
   - Null cohort: Patients without recurrence over 730 days of follow-up.
   - Recurrence cohort: Patients experiencing true metastatic recurrence with onset during surveillance.
2. **Acceptance Stress Suite (1,500 patients × 20 visits):**
   - Gaussian $\sigma=0.10$ and $\sigma=0.12$.
   - Heavy-tailed Student-t5 noise ($\sigma=0.10$).
   - Autoregressive AR(1) noise ($\rho=0.3, \sigma=0.10$).
   - Long-horizon anytime monitoring ($K=60$ visits).
   - Informative missingness (30% missing observations).

---

## 5. Primary and Secondary Endpoints
1. **Primary Metric:** Empirical patient-level false alarm rate under the null ($\text{FAR}_{\text{pt}} = \frac{1}{N} \sum_{i=1}^N \mathbf{1}\{\exists t \le K : \text{Alert}_{i,t}\}$).
2. **Secondary Metrics:**
   - Statistical uncertainty: 1,000-sample bootstrap 95% confidence intervals on false-alarm rates and delays (RR14).
   - Median and mean detection delay (days from onset to alert) on true recurrences.
   - Detection sensitivity / power.

---

## 6. Pre-Registered Kill Criterion
If `SequentialDetector` violates the nominal $\alpha_{\text{pt}} + 0.02$ bound in any primary acceptance scenario, the detector is rejected per ML_PROGRAM §3.2.
