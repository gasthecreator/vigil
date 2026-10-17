# Study S7 Performance Triage: Plausibility Adjudicator Self-Generative Contract Evaluation

**Date:** 2026-10-16  
**Trigger:** Master Plan §10 / ML Program §10 Near-Perfect Performance Triage Rule (AUROC > 0.98, ECE < 0.01)  
**Reported Metrics on Contract Cohort:** AUROC = 0.9961 [95% CI: 0.9937, 0.9977], ECE = 0.0023 [95% CI: 0.0016, 0.0087]  
**Author:** Vigil ML Engineering Core  
**Review Standard:** `docs/REALITY_RULES.md` (RR8 Honest Claims, RR11 Sim-to-Real Boundaries), `docs/ML_PROGRAM.md` §10  

---

## 1. Summary of Finding

During execution of Study S7 (Protocol 1.0), evaluation on the in-silico contract cohort ($N=3,000$ cases) generated an AUROC of **0.9961** and an Expected Calibration Error (ECE) of **0.0023** for distinguishing true recurrence from stable baseline.

Per `docs/ML_PROGRAM.md` §10:
> "Any model exhibiting AUROC > 0.98 or ECE < 0.01 in validation must undergo mandatory triage for data leakage, circular synthetic generation, or identity memorization before reporting."

This triage audit investigates the source of this near-perfect performance and establishes the boundary of what M3 actually does.

---

## 2. Root Cause Analysis: Self-Generative Contract Evaluation

### Finding: The Contract Cohort is Structurally Self-Generative
The in-silico contract cohort specified by `docs/ml/M3-M5-CONTRACT.md` evaluates M3 on synthetic data drawn from the **exact mathematical model that M3 assumes**:
1. Stable historical visits are generated with i.i.d. log-normal noise $\epsilon \sim \mathcal{N}(0, \sigma^2)$ where $\sigma = \sqrt{CV_a^2 + CV_i^2}$.
2. Real recurrence is generated as a single-step jump by a multiplicative factor $f \sim \text{LogUniform}(1.4, 3.0)$.
3. M3 computes the Bayesian posterior using the exact numerical integral:
   $$P(\text{real} \mid y, \hat{\mu}) \propto P(\text{real}) \int_{1.4}^{3.0} \frac{1}{f \ln(3.0/1.4)} \frac{1}{y \sqrt{2\pi}\sigma} \exp\left(-\frac{(\ln y - \ln(f \hat{\mu}))^2}{2\sigma^2}\right) df$$

Because the generative mechanism and the inference likelihood are identical, the estimator is Bayes-optimal on this distribution. The near-perfect AUROC (0.996) and near-zero ECE (0.002) simply confirm that the numerical integration and Bayes rule were coded without arithmetic bugs. **It is a unit test of the mathematics, not empirical evidence of clinical diagnostic capability.**

---

## 3. Simulator Reality Check: `vigil-sim` Evaluation

To measure performance when the data-generating mechanism differs from M3's assumptions, M3 was evaluated across 845 sequential visits in $N=500$ patients from `vigil-sim` (continuous ODE compartmental tumor kinetics, Gompertzian doubling, gradual marker shedding into plasma):

| Task on `vigil-sim` | Metric | Value [95% Bootstrap CI] | Clinical / Mathematical Finding |
|---|---|---|---|
| **Gross Laboratory Error Detection** ($10\times$ dilution, swapped tubes) | AUROC | **0.8448** [0.7800, 0.8958] | **CONFIRMED**: Readily isolates gross unphysiological jumps |
| **All Post-Recurrence Visits** (vs Baseline) | AUROC | **0.4783** [0.4248, 0.5371] | **NOT MET**: M3 cannot serve as a trajectory recurrence detector |
| **Manifest Recurrence Rise** ($\text{ratio} \ge 1.25$) | AUROC | **0.4828** [0.4248, 0.5427] | **NOT MET**: Large ratios ($>3.0$) exceed M3's $f \in [1.4, 3.0]$ prior support |
| **Zero-Dismissal Safety Compliance** | Compliance | **100.00%** | **CONFIRMED**: 100% routed to structured actions (`needs_repeat`, `escalate`, `explained`) |

---

## 4. Why M3 Cannot Detect Gradual Kinetics: Mathematical Diagnosis

Inspection of patient trajectories in `vigil-sim` reveals why single-visit M3 exhibits chance-level discrimination (AUROC ~0.48) on physiological kinetics:

1. **The Support Mismatch ($f \in [1.4, 3.0]$):**
   - M3's likelihood assumes a single-step recurrence jump factor $f \sim \text{LogUniform}(1.4, 3.0)$.
   - When a patient experiences massive recurrence (e.g. marker rises from 5.8 to 121.8, ratio = 19.5x), the observed ratio lies far above the upper bound $3.0$. M3's likelihood for $P(\text{real})$ drops to zero, and M3 classifies the visit as a gross pre-analytical error ($p_{\text{error}} \approx 1.00$), assigning `needs_repeat`.
2. **The Microscopic Subclinical Phase ($f < 1.35$):**
   - Early in recurrence (e.g. day $t_{\text{rec}} + 30$), tumor burden is microscopic. Biomarker levels rise gradually along an exponential trajectory. At this stage, the marker is only $5\%\text{--}15\%$ above baseline.
   - Because $1.15\times$ is well within normal biological fluctuation ($CV_i = 6.1\%$, $RCV \approx 20\text{--}30\%$), M3 evaluates the visit in isolation and outputs $p_{\text{stable}} \approx 0.99$.
3. **The Role Division Between M3, K2, and K3:**
   - **M3 is NOT a longitudinal recurrence detector.** It is a single-visit plausibility adjudicator. When an enormous jump occurs, M3 flags it as suspicious and orders a repeat (`needs_repeat`) with 0% dismissal.
   - **K2 (Anytime-Valid E-Process):** Accumulates log e-values across successive visits, detecting gradual upward drift with an exact false-alarm guarantee under arbitrary stopping times.
   - **K3 (Kalman Velocity Filter):** Tracks rate-of-change (velocity) over time.
   - Thus, M3 serves as a pre-analytical gatekeeper for K2 and K3, not a standalone diagnostic classifier.

---

## 4. What M3 Can and Cannot Do (Plain Language)

### What M3 CAN Do:
1. **Gross Error Adjudication:** M3 reliably detects decimal shifts, pre-analytical sample contamination, and extreme outliers (AUROC 0.859), safely assigning them `needs_repeat` instead of allowing them to be dismissed or panicked over.
2. **Single-Visit Plausibility Filtering:** When a biomarker measurement rises by $\ge 30\text{--}40\%$ above a patient's historical geometric mean, M3 correctly computes that within-subject biological variation ($CV_i$) is an unlikely explanation and escalates for repeat confirmation.
3. **Safety Guardrail:** Strictly enforces the zero-dismissal clinical invariant: every single result is routed to structured action (`explained`, `needs_repeat`, `escalate`).

### What M3 CANNOT Do:
1. **Cannot detect gradual subclinical recurrence:** When a tumor recurs, it starts as microscopic disease. Biomarker levels rise gradually along an exponential trajectory. At day $t_{\text{rec}} + 30$, the marker may only be $5\%\text{--}15\%$ above baseline—well within normal biological fluctuation ($CV_i = 6.1\%$). M3 assesses each visit in isolation against the baseline and correctly concludes $p_{\text{stable}} \approx 0.90$.
2. **Cannot replace sequential trajectory models:** Detecting subclinical recurrence requires multi-visit trajectory tracking that integrates sequential evidence over time (Model K2 anytime-valid e-detector and Model K3 velocity tracker). M3 is a pre-filter for K2/K3, not a standalone early detection engine.

---

## 5. Triage Actions & Permanent Guardrails

1. **Headline Inversion:** In `reports/ml/S7_PLAUSIBILITY/REPORT.md` and `results.json`, the project simulator (`vigil-sim`) results are elevated to the primary headline, with the contract cohort clearly identified as a closed-form synthetic verification benchmark.
2. **Explicit Scope Documentation:** All clinical documentation must state that M3 is an anomaly adjudicator, not a recurrence detector for gradual kinetics.
