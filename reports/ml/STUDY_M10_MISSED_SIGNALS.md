# Study M10-V2: Missed-Signal Quality Audit Engine Evaluation

**Study Identifier:** M10-V2
**Pre-Registration:** [`docs/studies/PREREG-M10.md`](file:///Users/gsanni/.gemini/antigravity/scratch/vigil/docs/studies/PREREG-M10.md)
**Governance:** [`docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md`](file:///Users/gsanni/.gemini/antigravity/scratch/vigil/docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md)
**Consent Governance:** [`docs/adr/0017-quality-audit-consent-and-aggregate-use.md`](file:///Users/gsanni/.gemini/antigravity/scratch/vigil/docs/adr/0017-quality-audit-consent-and-aggregate-use.md)
**Status:** COMPLETE (All 5 Pre-Registered Hypotheses SUPPORTED)

---

## 1. Executive Summary

Study M10-V2 delivers a complete, non-circular re-evaluation of Vigil's retrospective oncology quality audit engine (`vigil_ml.quality`). Addressing Overseer Verdict P7B (Conditions P13-B, P13-C, P13-D, P13-F):
1. **Decoupled Algorithmic Detection:** Detection is performed dynamically by Model K2 anytime-valid sequential detection ($\alpha_{\text{pt}} = 0.05$) and Model M3 reference change value plausibility adjudication. Zero pre-labelled `alert_level` strings are used.
2. **Clinician Action Attribution:** `action_recorded` is credited solely to clinician events (`AlertAcknowledgement` or completed `FollowUpTask`). Automated system tasks that remain pending are never counted.
3. **Multi-Facility Diversity:** Validated across 5 independent facility archetypes.
4. **Zero Backdoor Flags:** Removed `expose_raw_for_testing` from production code.
5. **Consent Precedence (ADR 0017):** Patients who withdraw consent are strictly excluded from facility audit extraction.

---

## 2. Multi-Facility Performance Results

| Facility Profile | Total Patients | Signals Detected | Action Recorded | Action Not Recorded | Missed Rate | 95% Bootstrap CI |
|---|---|---|---|---|---|---|
| **Facility 1 (Mixed Referral Hospital)** | 503 | 233 | 121 | 112 | 48.07% | [41.63%, 54.51%] |
| **Facility 2 (Zero-Miss Center)** | 200 | 64 | 64 | 0 | 0.00% | N/A (0 missed) |
| **Facility 3 (Recurrence-Free Clinic)** | 300 | 0 | 0 | 0 | 0.00% | Specificity: 100.00% |
| **Facility 4 (High Benign Spikes)** | 200 | 0 | 0 | 0 | N/A | False Alarm: 0.00% |
| **Facility 5 (Pipeline-Only Facility)** | 200 | 93 | 0 | 93 | 100.00% | 100.0% unaddressed |

---

## 3. Pre-Registered Hypotheses Verification

### Hypothesis H1 — Sensitivity & Precision on Independent Truth
- **Sensitivity:** 96.55% (95% CI: [93.10%, 99.14%]) -> Criterion $\ge 80.0\%$ CI lower bound: **MET**
- **Precision:** 100.00% (95% CI: [100.00%, 100.00%]) -> Criterion $\ge 75.0\%$ CI lower bound: **MET**
- **Verdict:** **SUPPORTED**

### Hypothesis H2 — Signal Detection Lead Time & Timing Accuracy
- **Mean Delay Error:** 35.5 days (95% CI: [32.0, 39.1] days)
- **Criterion:** Mean delay error $\le 45$ days (within routine 90-day surveillance cycle)
- **Verdict:** **SUPPORTED**

### Hypothesis H3 — Specificity under Biological Noise & Benign Spikes
- **Recurrence-Free Specificity:** 100.00%
- **Benign Spike False Alarm Rate:** 0.00% (budget: $\le 5.0\%$)
- **Verdict:** **SUPPORTED**

### Hypothesis H4 — Pipeline-Only Decoupling Invariant
- **Facility 5 Missed Rate:** 100.00% (Signals: 93, Clinician Actions Recorded: 0)
- **Criterion:** Confirms that automated pipeline follow-up tasks do not mask unaddressed signals.
- **Verdict:** **SUPPORTED**

### Hypothesis H5 — Small-Cell Privacy Guarantee ($k \ge 5$)
- **Suppressed Strata Count:** 3
- **Unsuppressed Strata Leaks ($1 \le n < 5$):** 0
- **Verdict:** **SUPPORTED** (Zero unsuppressed micro-cells exposed)

---

## 4. Register & Privacy Audit

- **Neutral Descriptive Register:** VERIFIED (`verify_neutral_register` passes with zero forbidden punitive terms).
- **Backdoor Removal:** `expose_raw_for_testing` removed from production code; confirmed by static signature reflection and unit tests.
