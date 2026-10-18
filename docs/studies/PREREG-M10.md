# Pre-Registration: Study M10 — Missed-Signal Quality Audit Engine Evaluation

**Study Identifier:** M10  
**Module:** M10 (Missed-Signal Quality Audit Engine)  
**Document:** `docs/studies/PREREG-M10.md`  
**Reference:** `docs/MASTER_PLAN.md` §6.10, §11; `docs/REALITY_RULES.md`  
**Date:** 2026-10-17  
**Status:** PRE-REGISTERED (Committed prior to execution)  

---

## 1. Scientific & Operational Objective
Evaluate Vigil's retrospective quality audit engine (`vigil_ml.quality`) in detecting missed surveillance signals across patient trajectories. The engine identifies instances where algorithmic alarms or biomarker kinetics indicated disease recurrence or acute clinical progression, but no timely clinical action (imaging order, biopsy, oncologist referral, treatment modification) was recorded within a pre-specified audit window ($W_{\text{action}} = 30$ calendar days).

---

## 2. Mandatory Ethical, Privacy & Governance Controls

### 2.1 Strictly Descriptive Register
* The audit engine reports strictly factual observations: *"signal present, action not recorded"*.
* Under no circumstances may judgmental, accusatory, or punitive language be produced (e.g. "negligence", "error", "blame", "fault", "malpractice").

### 2.2 Re-Identification Prevention & Small-Cell Suppression ($k \ge 5$)
* Aggregate reporting only. No patient names, MRNs, or individual clinician identifiers are emitted in audit reports or API payloads.
* Any demographic, geographic, or clinical stratum with fewer than 5 patients ($n < 5$) must be suppressed (masked as `"<5"` or omitted) to guarantee $k$-anonymity against re-identification attacks.

### 2.3 Legal & Institutional Governance Basis (ADR 0016)
* The quality audit operates under institutional healthcare quality improvement mandates and NDPA public health exemptions.
* Audit generation and exports are restricted exclusively to authorized institutional leadership (`quality_lead` and `admin` roles) and logged immutably in the facility access audit trail.

---

## 3. Pre-Registered Hypotheses

### Hypothesis H1 — Synthetic Ground-Truth Recovery
* **Statement:** On a synthetic cohort with injected known clinical trajectories (true missed signals vs acted-upon alerts vs true-negative stable patients), the audit engine will recover true missed signals with Sensitivity $\ge 90.0\%$ and Specificity $\ge 95.0\%$.

### Hypothesis H2 — Small-Cell Privacy Guarantee ($k \ge 5$)
* **Statement:** Across all demographic, stage, and clinical context breakdowns in the audit report, zero cells with $1 \le n < 5$ will be exposed. All small cells will be suppressed.

### Hypothesis H3 — Specificity on Biological Noise Trajectories
* **Statement:** When evaluated on non-cancer trajectories with benign physiological biomarker fluctuations (hepatotoxicity spikes, inter-lab batch shifts, infection), the engine produces zero false missed-signal flags (False Positive Rate $\le 2.0\%$).

---

## 4. Evaluation Cohorts & Protocol
1. **Cohort Alpha (Injected Ground Truth):** $N = 1,000$ simulated surveillance trajectories from `vigil-sim` with known latent recurrence onset and simulated EHR action logs:
   - 150 injected missed signals (sustained marker rise $\ge 3$ consecutive visits, no imaging or clinical escalation within 30 days).
   - 250 acted-upon signals (sustained rise followed by recorded imaging/biopsy within 14 days).
   - 600 stable recurrence-free trajectories.
2. **Cohort Beta (Biological Noise Stress):** $N = 500$ null trajectories subject to severe non-cancer perturbations (hepatic flares, assay variation, random missing visits).
3. **Statistical Analysis:** Point estimates with 95% percentile bootstrap confidence intervals ($B = 1,000$).
