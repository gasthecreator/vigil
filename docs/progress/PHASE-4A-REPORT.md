# Vigil Phase 4a Engineering & Science Report

**Phase:** Phase 4a — Plausibility Adjudication (M3) and Verified Clinical Narrative (M5)  
**Governing Documents:** `docs/MASTER_PLAN.md` (v1.3); `docs/ML_PROGRAM.md` §6.3, §6.5; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` (RR1–RR14); `docs/EVIDENCE.md` E9  
**Execution Date:** 2026-10-16  
**Active Branch:** `feat/phase-4a-m3-m5`  
**Maturity Level:** L0 — Honest Prototype (Phases 0, 1, 2, 3A, 3B, and 4a Verified)  

---

## 1. Executive Summary

Phase 4a delivers the core safety features that constitute Vigil's primary clinical reason to exist:
1. **Module M3 (Plausibility Adjudicator):** An intelligent Bayesian adjudication engine that quantifies analytical and within-subject biological variation via Reference Change Values (RCV, Evidence E9) and evaluates single-visit deviations under a 3-way generative mixture model (real progression vs gross pre-analytical error vs physiological baseline fluctuation). Crucially, M3 enforces a strict **zero-dismissal clinical safety policy**: anomalous measurements are never dismissed as noise; they are categorized as `explained`, `needs_repeat`, or `escalate`.
2. **Module M5 (Provenance-Verified Clinical Narrative Engine):** A deterministic, template-based narrative generator and independent semantic verifier that converts structured rationale facts into clinician-facing notes with zero LLMs on any diagnostic or therapeutic critical path. Enforces forbidden-claim filtering, untraced number interception, swap detection across semantic clauses, and monotonic sub-narrative validity.
3. **Closing Phase 3B Overseer Conditions (B-1…B-4):**
   - **B-1 (Honest S2 Redo):** Pre-registration Protocol 1.2 committed first in `30b06e6`. $\hat{\sigma}_{\log} = 0.0590$ fitted on disjoint calibration nulls (seed 999). Evaluated K2 vs static threshold at matched patient-level false alarm rate ($0.0052$) with 1,000-sample bootstrap CIs and code-generated verdicts.
   - **B-2 (Tier Latch Accumulation):** Updated `vigil_ml/k2.py` so `update()` continues accumulating evidence after alert latching, allowing alert tiers to advance to `REVIEW` and `URGENT`.
   - **B-3 (K1 Calibration Script & Contract):** Committed `scripts/calibrate_k1.py` computing residual SDs `[25.2695, 0.0738, 0.0404, 42.6228]` to `models/k1_calibration.json`; corrected parameter labels to doubling time, shedding, clearance, onset; enforced `TypeError` in `predict_risk` for non-`K1Observations` inputs.
   - **B-4 (Acceptance Tests Invariance):** Maintained zero-line diff in overseer acceptance test suites `tests/acceptance_k1`, `tests/acceptance_3b`, and `tests/acceptance_p4`.

All 15 independent acceptance tests in `tests/acceptance_p4/` pass without modification.

---

## 2. Phase 4a Acceptance Gate Table

Every `MET` status in this table is backed by a named, passing test in the test suite (RR7):

| Gate Item | Target / Requirement | Observed Metric / Result | Evidence / Test Reference | Status |
|---|---|---|---|---|
| **M3-RCV** | Closed-form Gaussian & log-normal RCV | Gaussian: $2.77\sqrt{CV_a^2+CV_i^2}$; Log-normal: $(e^{z\sqrt{2}s}-1, e^{-z\sqrt{2}s}-1)$ | `tests/acceptance_p4/test_m3_contract.py::test_rcv_closed_forms` | **MET** |
| **M3-VALID** | Bounded probabilities, sum to 1, valid action | $p \in [0, 1], \sum p = 1.0000$, actions $\in \{\text{explained}, \text{needs\_repeat}, \text{escalate}\}$ | `tests/acceptance_p4/test_m3_contract.py::test_outputs_valid` | **MET** |
| **M3-CALIB-DISCRIM** | Discrimination on contract cohort ($N=3,000$) | AUROC(real vs stable) = **0.9961** ($\ge 0.85$); AUROC(error vs rest) = **0.9487** ($\ge 0.80$) | `tests/acceptance_p4/test_m3_contract.py::test_discrimination` | **MET** |
| **M3-CALIB-ECE** | Posterior calibration ($N=3,000$) | $p_{\text{real}}$ ECE = **0.0023** ($\le 0.06$); $p_{\text{error}}$ ECE = **0.0025** ($\le 0.06$) | `tests/acceptance_p4/test_m3_contract.py::test_calibration` | **MET** |
| **M3-CALIB-BRIER** | Brier score skill ratio | $p_{\text{real}}$ ratio = **0.1121** ($\le 0.85$); $p_{\text{error}}$ ratio = **0.2353** ($\le 0.85$) | `tests/acceptance_p4/test_m3_contract.py::test_calibration` | **MET** |
| **M3-POLICY** | Strict zero-dismissal safety policy | Explained only if $p_{\text{stable}}\ge 0.90$; Escalate only if $p_{\text{real}}\ge 0.60$; Repeat if $p_{\text{error}}\ge 0.30$ | `tests/acceptance_p4/test_m3_contract.py::test_no_dismissal_policy` | **MET** |
| **M3-LAB-CHANGE** | Inter-lab variance handling | 1.35x elevation lowers $p_{\text{real}}$ in **60/60 (100%)** of paired lab-switch cases | `tests/acceptance_p4/test_m3_contract.py::test_lab_change_lowers_real_probability` | **MET** |
| **M3-FACTS** | Provenance rationale facts table | Emits facts with `rcv`, `observed_change` (within 1% of ratio), $p_{\text{real}}, p_{\text{error}}, p_{\text{stable}}, \text{action}$ | `tests/acceptance_p4/test_m3_contract.py::test_rationale_facts` | **MET** |
| **M5-ROUND-TRIP** | Round-trip rendering & verification | 200/200 random fact tables render and verify `ok: True` | `tests/acceptance_p4/test_m5_contract.py::test_round_trip_verifies` | **MET** |
| **M5-MUTATION-REJECT** | Mutation & swap rejection | Mutated % (91%), swapped % across clauses, novel number ("14 days") rejected | `tests/acceptance_p4/test_m5_contract.py::test_number_mutations_rejected` | **MET** |
| **M5-SAFETY** | Forbidden claim interception | All 5 forbidden phrases rejected (`"You have cancer."`, `"Metastasis is confirmed."`, etc.) | `tests/acceptance_p4/test_m5_contract.py::test_forbidden_claims_rejected` | **MET** |
| **M5-SUB-NARRATIVE** | Empty facts & monotonic removal | Empty facts render safe abstention; removing sentences preserves `ok: True` | `tests/acceptance_p4/test_m5_contract.py::test_empty_facts_safe_and_removal_ok` | **MET** |
| **M5-JOURNEYS** | Three worked clinical journeys J2 | Generated by code in `reports/ml/M5_JOURNEYS.md` (J2, benign fluctuation, true recurrence) | `packages/vigil-ml/tests/test_m3_m5.py::test_m5_worked_journeys` | **MET** |
| **CI-P4A** | CI integration of Phase 4a contract | `VIGIL_ACCEPT_P4=1 uv run pytest tests/acceptance_p4 -v` wired into `.github/workflows/ci.yml` | `.github/workflows/ci.yml` line 52 | **MET** |

---

## 3. Condition Closures (B-1…B-4) Summary

### B-1: Study S2 Redo (Matched FAR & Honest Programmatic Verdicts)
- **Pre-Registration:** Protocol 1.2 pre-registered first in commit `30b06e6`.
- **Calibration Split:** $\hat{\sigma}_{\log} = 0.0590$ fitted on independent calibration nulls (`seed=999`, $N=500$ patients) disjoint from the evaluation cohort (RR11).
- **Matched False Alarm Rate:** On `vigil-sim` (seed 42), matched patient-level false alarm rate across entire 2-year monitoring horizon = **0.0052** [95% CI: 0.0000, 0.0156] for both Model K2 ($\alpha_{\text{pt}} = 0.15$) and the static threshold rule ($\ge 30.0\text{ U/mL}$).
- **Sensitivity & Delay Comparison:**
  - **Static Threshold ($\ge 30.0\text{ U/mL}$):** Sensitivity = **52.92%** [95% CI: 47.08%, 58.76%], median delay = **79.5 days**.
  - **Model K2 (SequentialDetector):** Sensitivity = **41.58%** [95% CI: 36.08%, 47.42%], median delay = **101.6 days**.
  - **Paired Sensitivity Difference:** $\Delta\text{Power} = \mathbf{-11.34\text{ percentage points}}$ [95% CI: -15.46 pp, -7.22 pp].
- **Honest Finding (Programmatic Verdicts in `reports/ml/S2_SEQUENTIAL/REPORT.md`):** Model K2 provides a mathematical anytime-valid patient-level false-alarm guarantee under indefinite monitoring, and on `vigil-sim` it pays an empirical power cost (-11.34 pp) compared to a static threshold. This finding is stated plainly in the report.

### B-2: K2 Tier Latch Accumulation
- In `packages/vigil-ml/vigil_ml/k2.py`, `update()` was modified so `log_e` continues accumulating evidence even after `self._alert` has latched.
- Tiers advance from `ALERT` ($E \ge 1/\alpha_{\text{pt}}$) to `REVIEW` ($E \ge 50$) and `URGENT` ($E \ge 200$) as evidence mounts, without reverting or freezing.
- Verified by passing all 13 tests in `tests/acceptance_3b/test_k2_contract.py` and `test_k8_contract.py`.

### B-3: K1 Calibration & Contract Cleanup
- Created standalone calibration script `scripts/calibrate_k1.py` fitting empirical residual SDs on calibration nulls: `[25.2695, 0.0738, 0.0404, 42.6228]` saved in `packages/vigil-ml/vigil_ml/models/k1_calibration.json`.
- Corrected descriptions in `k1.py` and `MODEL-CARD-K1.md` to: doubling time, shedding, clearance, onset.
- Enforced `TypeError` in `predict_risk` for non-`K1Observations` inputs.
- Verified by passing all 17 tests in `tests/acceptance_k1` (overseer world-test fix verified).

### B-4: Acceptance Tests Invariance
- Zero lines modified in `tests/acceptance_k1`, `tests/acceptance_3b`, or `tests/acceptance_p4` (empty git diff vs introducing commits).

---

## 4. Study S7: Plausibility Adjudication Under Pre-Analytical Error Injection

- **Pre-Registration:** Protocol 1.0 pre-registered in `reports/ml/S7_PLAUSIBILITY/PREREG.md` (commit `8ba7de9`).
- **Executed via:** `scripts/run_study_s7.py`.
- **In-Silico Contract Cohort ($N=3,000$ cases):**
  - **AUROC (True Recurrence vs Stable Baseline):** **0.9961** [95% CI: 0.9937, 0.9977] (Target $\ge 0.85$, lower CI $\ge 0.80$) $\to$ **CONFIRMED**.
  - **AUROC (Gross Error vs All Other States):** **0.9487** [95% CI: 0.9114, 0.9770] (Target $\ge 0.80$, lower CI $\ge 0.75$) $\to$ **CONFIRMED**.
  - **Posterior Calibration:** $p_{\text{real}}$ ECE = **0.0023** [95% CI: 0.0016, 0.0087]; $p_{\text{error}}$ ECE = **0.0025** [95% CI: 0.0022, 0.0067] (Target $\le 0.06$) $\to$ **CONFIRMED**.
  - **Brier Skill Ratios:** $p_{\text{real}}$ Brier ratio = **0.1121**; $p_{\text{error}}$ Brier ratio = **0.2353** (Target $\le 0.85$) $\to$ **CONFIRMED**.
  - **Zero-Dismissal Compliance:** **100.00%** compliance (zero dismissed cases) $\to$ **CONFIRMED**.
- **Project Simulator (`vigil-sim`, $N=500$ patients, 845 visits) Reality Check:**
  - **AUROC (Gross Error vs Non-Error Visits):** **0.8587** [95% CI: 0.8101, 0.9013].
  - **Sim-to-Contract Gap:** In the contract specification, true recurrence is modelled as an instantaneous single-step multiplicative elevation $f \sim \text{LogUniform}(1.4, 3.0)$ against the historical geometric baseline. In `vigil-sim`, tumor growth follows continuous ODE kinetics where early post-recurrence visits display minor elevations within the biological RCV noise band ($RCV \approx 31\%$). M3 correctly adjudicates these early visits as stable baseline variation (or indeterminate), demonstrating that M3 is an adjudication filter of single visits against laboratory error rather than a multi-visit trajectory forecaster (which is handled by K2 and K3).

---

## 5. Biological Variation Evidence Base (Evidence E9)

All biological variation estimates are registered and cited per Evidence E9:

| Analyte | $CV_i$ (%) | $CV_g$ (%) | Index of Individuality ($II$) | Evidence Status | Literature Reference |
|---|---|---|---|---|---|
| **CA 15-3** | **6.1%** | 43.1% | 0.14 | **PRIMARY-VERIFIED** | Aarsand et al. 2021 (EuBIVAS), PMID 33964202 |
| **CEA** | **12.7%** | 55.4% | 0.23 | **PRIMARY-VERIFIED** | Aarsand et al. 2021 (EuBIVAS), PMID 33964202 |
| **ALP** | 6.5% | 25.8% | 0.25 | **SECONDARY** | EFLM 2019 / Ricós et al. 1999 update |
| **ALT** | 19.4% | 41.6% | 0.47 | **SECONDARY** | EFLM 2019 / Ricós et al. 1999 update |
| **AST** | 12.3% | 22.8% | 0.54 | **SECONDARY** | EFLM 2019 / Ricós et al. 1999 update |

---

## 6. What Was NOT Made Real (Explicitly Registered Stubs)

In strict compliance with Master Plan v1.3 and reality rules (RR8), the following modules were deliberately NOT started or remained in the research backlog:
1. **Module M4 (Test Escalation Ladder):** Deferred to Phase 4b per Plan v1.3 (registered as `S-011` in `docs/STUBS.md`).
2. **Module K4 (Deep Zoo):** Research backlog; deferred to Phase 3C (registered as `S-004`).
3. **Module K5 (Hierarchical Lab Harmonisation):** Research backlog; deferred to Phase 3C (registered as `S-009`).
4. **Module K6 (Active Sensing Suggestion Engine):** Research backlog; deferred to Phase 3D (registered as `S-005`).
5. **Module M12 (Federated & Differential Privacy):** Research backlog; deferred to Phase 3D (registered as `S-006`).
6. **Platform Backend v2:** Scheduled for Phase 5 per Master Plan v1.3.
