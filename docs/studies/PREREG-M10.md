# Pre-Registration: Study M10-V2 — Missed-Signal Quality Audit Engine Evaluation

**Study Identifier:** M10-V2  
**Module:** M10 (Missed-Signal Quality Audit Engine)  
**Document:** `docs/studies/PREREG-M10.md`  
**Reference:** `docs/MASTER_PLAN.md` §6.10, §11; `docs/REALITY_RULES.md`; `docs/progress/VERDICT-P7B.md` (Conditions P13-B, P13-C, P13-D, P13-F)  
**Date:** 2026-10-18  
**Status:** PRE-REGISTERED (Committed prior to execution)  
**Supersedes:** PREREG-M10 (v1 retracted due to circular label coupling identified in VERDICT-P7B)

---

## 1. Scientific & Operational Objective

Evaluate Vigil's retrospective quality audit engine (`vigil_ml.quality`) in detecting missed oncology surveillance signals across patient trajectories without circularity or synthetic data contamination:

1. **Independent Injected Truth:** The ground-truth trajectory generator must be strictly decoupled from the detector. The generator simulates underlying latent tumor kinetics (exponential growth with variable doubling times $T_d \in [45, 120]$ days), visit jitter, informative missingness, assay noise, and transient benign fluctuations. It never writes an `alert_level` label.
2. **Dynamic Algorithmic Detection:** The audit detector executes the validated Model K2 anytime-valid sequential detection e-process (`SequentialDetector`, $\alpha_{\text{pt}} = 0.05$) and Model M3 Plausibility Adjudicator (`adjudicate`) at fixed false-alert rates directly over raw $(t, y)$ series.
3. **Clinician Action Attribution:** `action_recorded` is determined strictly by clinician-attributable actions (e.g. `AlertAcknowledgement` with disposition, clinician-completed follow-up review, or ordered diagnostic imaging). Automated system task generation alone does NOT constitute clinical action.
4. **Multi-Facility Diversity:** Validates across 5 distinct facility profiles:
   - *Facility 1 (Mixed Referral Hospital):* High volume, realistic missed signals.
   - *Facility 2 (Zero-Miss Center):* Diligent clinical staff where 100% of signals receive timely action.
   - *Facility 3 (Recurrence-Free Clinic):* 100% stable/benign trajectories (tests specificity under null).
   - *Facility 4 (High Benign Spike Clinic):* High rate of transient non-malignant biomarker elevations (tests resilience against false alarms).
   - *Facility 5 (Pipeline-Only Facility):* System tasks created automatically but never acknowledged or completed by a clinician (verifies that automated pipeline tasks do not mask missed signals; expected missed rate $\ne 0$).

---

## 2. Mandatory Privacy & Governance Controls

1. **Strictly Neutral Descriptive Register:** Text output must adhere strictly to factual non-punitive terminology (*"signal present, action not recorded"*). Forbidden punitive terms (`negligence`, `error`, `blame`, `fault`, `malpractice`, `careless`) are scanned and rejected by automated assertions.
2. **$k \ge 5$ Small-Cell Suppression:** Any demographic, subtype, or clinical stratum with $1 \le n < 5$ must be masked as `"<5"` with rates nulled out. Zero raw unsuppressed data may be leaked or exposed by production code paths.
3. **Consent Opt-Out Enforcement (ADR 0017):** Facility data extraction must strictly exclude any patient who has withdrawn consent or lacks active consent.

---

## 3. Pre-Registered Hypotheses

### Hypothesis H1 — Sensitivity & Precision on Independent Truth
* **Statement:** On diverse non-circular synthetic trajectories, the audit engine will detect true missed signals with Sensitivity $\ge 85.0\%$ and Precision $\ge 80.0\%$.
* **Criterion:** 95% percentile bootstrap confidence interval lower bounds satisfy $\text{Sensitivity}_{\text{lower}} \ge 0.80$ and $\text{Precision}_{\text{lower}} \ge 0.75$.

### Hypothesis H2 — Signal Detection Lead Time & Timing Accuracy
* **Statement:** The detected signal day tracks the true latent kinetic escalation point with mean absolute delay error $\le 45$ days (within one routine follow-up cycle).

### Hypothesis H3 — Specificity under Biological Noise & Benign Spikes
* **Statement:** Across recurrence-free and high-benign-spike cohorts, the false-positive alert rate remains $\le 5.0\%$ (conforming to the K2 anytime-valid design budget $\alpha \le 0.05$).

### Hypothesis H4 — Pipeline-Only Decoupling Invariant
* **Statement:** A facility where follow-up tasks are created by the ingestion pipeline but never completed or acknowledged by a clinician will yield an action-not-recorded rate $> 0$ (confirming that automated tasks do not falsely register as clinician actions).

### Hypothesis H5 — Small-Cell Privacy Guarantee ($k \ge 5$)
* **Statement:** Across all breakdown strata, exactly zero cells with $1 \le n < 5$ are exposed in audit reports or API responses.

---

## 4. Evaluation Protocol & Statistical Methods

- **Replications:** 1,000 independent bootstrap replications ($B = 1,000$) over patient trajectories to compute 95% percentile confidence intervals for all primary metrics.
- **Reporting:** Point estimates, standard errors, and percentile bootstrap CIs committed to `reports/ml/STUDY_M10_MISSED_SIGNALS.json` and rendered in Markdown.
