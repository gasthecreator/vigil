# Model Card: Model K6 — Active Sensing Policy Engine

**Model Identifier:** `MODEL-K6-ACTIVE-SENSING`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-K), §3.6, §6  
**Evaluation Status:** Evaluated over 5-year longitudinal simulation (`reports/ml/S6_ACTIVE_SENSING/REPORT.md`)  

---

## 1. Model Overview and Intended Use
Routine breast cancer follow-up historically mandates rigid calendar schedules (e.g., rigid 3-month clinic visits for 2 years, followed by 6-month visits for 3 years). In resource-constrained global health environments, this schedule produces severe economic waste and appointment congestion for biologically quiescent patients, while failing to provide timely surveillance for aggressive subclinical recurrences.

Model K6 formulates post-treatment surveillance as a Bayesian experimental design problem:
- **Decision 1 (When to test next):** Adaptive inter-test intervals (14, 45, 90, 180, or 365 days) conditioning on posterior recurrence risk and epistemic uncertainty.
- **Decision 2 (Which panel to order):** Tiered analyte selection (Tier 1 Liver/Bone Enzymes $\sim \$5$; Tier 2 Standard Enzymes + CA 15-3 $\sim \$20$; Tier 3 Comprehensive Multi-Marker + Imaging $\sim \$120$).

---

## 2. Policy Optimization Objective
At each evaluation visit, the policy selects the next interval $\Delta t^*$ and panel $\mathcal{P}^*$ by maximizing Expected Information Gain (EIG) minus financial toxicity cost:

$$(\Delta t^*, \mathcal{P}^*) = \arg\max_{\Delta t, \mathcal{P}} \left[ \mathbb{E}[\Delta \operatorname{Var}(R(t + \Delta t)) \mid \mathcal{P}] - \lambda_{\text{cost}} \cdot \operatorname{Cost}(\mathcal{P}) \right]$$

### Clinical Action Logic
- **Quiescent Low-Risk ($R < 0.10, \sigma < 0.08$):** Schedule 180-day follow-up with Tier 2 standard panel. Reduces travel and test burden.
- **Intermediate / High Epistemic Uncertainty ($0.15 \le R \le 0.45$ or $\sigma > 0.15$):** Schedule rapid 45-day re-test with Tier 2 standard panel to resolve trajectory slope before committing to expensive imaging.
- **High Risk / Kinetic Surge ($R > 0.45$):** Schedule immediate 14-day confirmatory workup with Tier 3 comprehensive diagnostic confirmation.

---

## 3. Evaluation Findings (Study S6)
Over a 5-year post-adjuvant simulation across $N = 1,000$ synthetic patients:
1. **Detection Delay:** K6 achieved a mean detection delay of $47.6\text{ days}$ from kinetic onset, closely matching the intensive 3-month fixed schedule ($42.1\text{ days}$) and outperforming the 6-month relaxed schedule ($91.8\text{ days}$, a $44.2\text{-day}$ lead-time advantage).
2. **Visit Burden Reduction:** Total 5-year visits dropped from $20.0$ (fixed 3-month) to $11.2$ visits per patient (a $44.0\%$ reduction in clinic appointments).
3. **Financial Toxicity Reduction:** Cumulative 5-year surveillance cost dropped from $\$400.00$ to $\$204.00$ per patient (a $49.0\%$ total cost savings), meeting the low cost envelope of 6-month follow-up without its detection delay penalty.

---

## 4. Operational Boundaries
- **Advisory Role:** K6 generates decision-support scheduling suggestions. Treating oncologists retain final discretion over follow-up appointments.
- **Patient Autonomy:** Patient preference (e.g. anxiety, travel constraints) must be factored into policy weight $\lambda_{\text{cost}}$.
