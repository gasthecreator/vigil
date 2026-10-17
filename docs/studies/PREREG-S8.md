# Pre-Registration: Study S8 — Radiotherapy Treatment Continuity Policy Comparison (Digital Twin)

**Date of Pre-Registration:** 2026-10-17  
**Module:** M7 (Treatment Continuity Harm Model & Radiotherapy Triage)  
**Status:** Pre-Registered (Prior to Simulation Execution)  
**Pre-Registered Primary Script:** `scripts/run_study_s8.py`  
**Committed Results Output:** `reports/ml/STUDY_S8_CONTINUITY.json`

---

## 1. Background & Clinical Rationale
In resource-constrained cancer centres (such as Nigeria and sub-Saharan Africa, where an estimated 280-LINAC shortfall exists per IAEA guidelines; see evidence register E6), radiotherapy machines experience frequent unexpected breakdowns. Unplanned machine downtime interrupts ongoing curative courses (triggering accelerated clonogen repopulation) and forces waitlist expansion. Conventional First-Come, First-Served (FCFS) queuing treats all calendar delays identically, failing to account for biological tumor doubling time (e.g. TNBC vs hormone-positive post-lumpectomy) or acute palliative crises (e.g. bone metastases, spinal cord compression).

## 2. Pre-Registered Hypotheses
* **Hypothesis 1 (Primary Efficacy — Harm Reduction):**  
  The `HarmAware` CP-SAT allocation policy will achieve a statistically significant reduction in mean patient excess harm compared to naive First-Come, First-Served (`FCFS`).  
  *Criterion:* The 95% bootstrap confidence interval of the paired harm delta $\Delta H = H_{\text{FCFS}} - H_{\text{HarmAware}}$ must be strictly positive and exclude zero ($\Delta H > 0$).

* **Hypothesis 2 (Secondary Efficacy — vs. Clinical Urgency Heuristic):**  
  The `HarmAware` policy will achieve lower or equal total expected harm compared to a static priority `UrgencyHeuristic` by dynamically balancing marginal daily delay harm against machine-switching penalties and course contiguity.  
  *Criterion:* $\Delta H = H_{\text{Heuristic}} - H_{\text{HarmAware}} \ge 0$ with 95% bootstrap CI.

* **Hypothesis 3 (Algorithmic Equity & No Starvation):**  
  The `HarmAware` policy maintains a bounded subgroup wait disparity ($\le 5.0$ days) across demographic and geographic strata (e.g. rural public vs urban referral) while guaranteeing that no patient exceeds the starvation ceiling $W_{\max}$.  
  *Criterion:* Maximum observed wait time $\le W_{\max}$ and mean wait disparity $\le 5.0$ days across $\ge 1,000$ simulation runs.

---

## 3. Department Digital Twin Specification
* **Department Configuration:**  
  * 2 Linear Accelerators (`LINAC-01`, `LINAC-02`).
  * Nominal capacity: 25 patient fraction slots per day per machine (50 slots/day total).
* **Patient Arrival Stream:**  
  * Poisson arrival process with rate $\lambda = 2.5$ new patients/weekday.
  * Clinical context distribution calibrated to Nigerian breast cancer registry data (Huo 2009, Jedy-Agba 2016, E7):
    * `adjuvant_post_lumpectomy`: 30%
    * `adjuvant_post_mastectomy`: 35%
    * `curative_tnbc`: 25%
    * `palliative_bone_brain`: 10%
* **Machine Breakdown & Downtime Model (E6 Calibrated):**  
  * Machine failures follow a Poisson arrival process with $\lambda_{\text{down}} = 0.04$ breakdowns/day per machine (~1 breakdown every 25 operating days).
  * Mean Time to Repair (MTTR) follows a Log-Normal distribution ($\mu = 1.6$, $\sigma = 0.6$, median $\approx 5.0$ operating days, tail representing supply-chain replacement delays).
* **Simulation Horizon:**  
  * 60 operating days per replication.
  * Replications: $\ge 1,000$ independent Monte Carlo runs per policy.

---

## 4. Evaluated Policies
1. **`HarmAware` (Vigil M7 CP-SAT Solver):**  
   Dynamically solves constrained integer programming to minimize biological delay harm, course interruption penalties, and machine re-planning penalties subject to capacity, contiguity, and subgroup fairness bounds.
2. **`FCFS` (First-Come, First-Served):**  
   Strict queue based purely on elapsed arrival delay since diagnosis/surgery.
3. **`UrgencyHeuristic`:**  
   Static triage ranking: Ongoing Courses > Palliative > Curative TNBC > Post-Mastectomy > Lumpectomy.

---

## 5. Statistical Analysis Plan
* Primary metric: Mean excess harm per patient over the simulation horizon.
* Secondary metrics: Maximum wait time ($W_{\max}$), machine utilization rate, subgroup wait disparity (days), acute complication incidence.
* Uncertainty quantification: 95% percentile bootstrap confidence intervals computed across 1,000 bootstrap resamples.
* Sensitivity sweeps: Sensitivity evaluated across variation in MTTR (median 3 to 10 days) and arrival pressure ($\lambda = 2.0$ to $3.5$ patients/day).
