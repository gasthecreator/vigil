> **RETRACTED (2026-10-18).** Do not cite anything below. The study that followed this file returned literal dictionaries. Replaced by `experiments/EXP-K6-001/PREREG.md` (see `reports/ml/RETRACTED/README.md`).

# Study S6 Pre-Registration: Active Sensing & Adaptive Surveillance Scheduling

**Study ID:** S6_ACTIVE_SENSING  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-K), §3.6, §6  

---

## 1. Study Objective and Research Question
Routine post-treatment breast cancer follow-up historically mandates rigid, fixed-interval clinic visits (e.g., every 3 months for years 1–2, every 6 months for years 3–5). In resource-constrained health systems, this imposes severe financial toxicity, appointment bottlenecks, and high travel burdens on patients who are biologically quiescent, while delaying re-testing in patients developing early, aggressive subclinical recurrence.

**Core Question:** Does Bayesian active sensing (K6) achieve equivalent or superior preclinical detection lead times compared to intensive fixed 3-month schedules, while reducing cumulative follow-up costs and test volume by $\ge 40\%$?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Surveillance Waste in Fixed Schedules):** Over 5 years of surveillance, fixed 3-month schedules generate 20 visits per patient regardless of risk, with $> 80\%$ of visits occurring during periods of zero tumor growth.
2. **H2 (Adaptive Cost-Efficiency):** By conditioning surveillance intervals on posterior risk and epistemic uncertainty, K6 Active Sensing will match the preclinical detection delay of 3-month follow-up (difference $\le 7$ days) while reducing total test visits by $\ge 40\%$.
3. **H3 (Panel Stratification Value):** Utilizing Tier 1 (cheap liver/bone chemistry, ~$5) during quiescent periods and reserving Tier 3 comprehensive multi-marker diagnostics (~$120) for elevated-risk states will deliver $> 45\%$ total expenditure reduction compared to uniform multi-marker testing.

---

## 3. Evaluated Surveillance Policies
1. **Policy 1 (Fixed Intensive):** Strict 90-day intervals, standard Tier 2 panel (Enzymes + CA 15-3).
2. **Policy 2 (Fixed Relaxed):** Strict 180-day intervals, standard Tier 2 panel.
3. **Policy 3 (Clinician Heuristic):** Annual visits for stage I, 6-month for stage II, 3-month for stage III.
4. **Policy 4 (K6 Active Sensing Engine):** Fully dynamic Bayesian experimental design:
   - Quiescent low-risk: 180-day interval with Tier 1/2.
   - Intermediate/uncertain: 45-day rapid re-test with Tier 2.
   - High-risk surge: 14-day confirmatory workup with Tier 3.

---

## 4. Evaluated Cohort & Simulation Protocol
- $N = 1,000$ synthetic patients simulated over a 5-year post-adjuvant trajectory using the calibrated multi-compartment kinetic generator.
- All policies evaluated on identical synthetic patient cohort under locked random seed.

---

## 5. Primary and Secondary Endpoints
1. **Primary Metric:** Cumulative 5-year surveillance cost per patient ($USD) versus mean detection delay (days).
2. **Secondary Metrics:**
   - Total number of laboratory visits attended over 5 years.
   - Fraction of early recurrences detected within 60 days of kinetic onset.
   - Overdetection fraction (false positive imaging referrals triggered).

---

## 6. Pre-Registered Decision Criteria
Per `docs/ML_PROGRAM.md` §3.6 & §6:
- If K6 Active Sensing fails to reduce costs by at least $25\%$ without increasing detection delay by more than 14 days, the adaptive scheduling policy will ship only as an informational suggestion rather than a core clinical recommendation.
