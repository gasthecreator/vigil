# Module M5: Verified Narrative Worked Clinical Journeys

**Governing Documents:** `docs/MASTER_PLAN.md` §6.5, §14 WP4.2; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` RR7, RR14

This document contains three canonical worked clinical journeys generated deterministically by `vigil_ml.m5.generate_worked_journey`. Each journey demonstrates the end-to-end integration of Module M3 (Plausibility Adjudication) with Module M5 (Provenance-Verified Narrative Generation). Every narrative was verified by `vigil_ml.m5.verify_narrative` without violations.

---

## Journey J2: Surprising Marker Spike (Analytical Error) Adjudicated to Repeat

**Journey Identifier:** `j2_surprising_repeat`  
**Clinical Context:** Patient on surveillance with stable CA 15-3 (~18 U/mL). Day 360 shows sudden jump to 180 U/mL.  
**Adjudicated Action:** `needs_repeat`  
**Verification Status:** `PASSED` (Zero violations)

### Structured Rationale Facts Table (Module M3)

| Fact ID | Fact Type | Fact Value | Description |
|---|---|---|---|
| `f_rcv` | `rcv` | **0.3099** | Derived by Bayesian generative model |
| `f_observed_change` | `observed_change` | **10.0022** | Derived by Bayesian generative model |
| `f_p_real` | `p_real` | **0.0000** | Derived by Bayesian generative model |
| `f_p_error` | `p_error` | **1.0000** | Derived by Bayesian generative model |
| `f_p_stable` | `p_stable` | **0.0000** | Derived by Bayesian generative model |
| `f_action` | `action` | **needs_repeat** | Derived by Bayesian generative model |

### Generated Provenance-Verified Narrative (Module M5)

> "The calculated probability of true progression is 0%. The calculated probability of analytical or pre-analytical error is 100%. The calculated probability of baseline biological stability is 0%. The biological reference change value threshold is 31%. The observed marker ratio is 10.00 relative to baseline. The recommended clinical action is needs_repeat."

---

## Benign Fluctuation: Biological Noise Within RCV Adjudicated as Explained

**Journey Identifier:** `false_alarm_explained`  
**Clinical Context:** Patient on surveillance. CA 15-3 increases from 20 to 23 U/mL (1.15x), below RCV threshold.  
**Adjudicated Action:** `explained`  
**Verification Status:** `PASSED` (Zero violations)

### Structured Rationale Facts Table (Module M3)

| Fact ID | Fact Type | Fact Value | Description |
|---|---|---|---|
| `f_rcv` | `rcv` | **0.3099** | Derived by Bayesian generative model |
| `f_observed_change` | `observed_change` | **1.1502** | Derived by Bayesian generative model |
| `f_p_real` | `p_real` | **0.0114** | Derived by Bayesian generative model |
| `f_p_error` | `p_error` | **0.0046** | Derived by Bayesian generative model |
| `f_p_stable` | `p_stable` | **0.9840** | Derived by Bayesian generative model |
| `f_action` | `action` | **explained** | Derived by Bayesian generative model |

### Generated Provenance-Verified Narrative (Module M5)

> "The calculated probability of true progression is 1%. The calculated probability of analytical or pre-analytical error is 0%. The calculated probability of baseline biological stability is 98%. The biological reference change value threshold is 31%. The observed marker ratio is 1.15 relative to baseline. The recommended clinical action is explained."

---

## True Recurrence: Biomarker Elevation Exceeding RCV Adjudicated to Escalate

**Journey Identifier:** `real_progression_escalate`  
**Clinical Context:** Patient on surveillance. CA 15-3 surges from 15 to 37.8 U/mL (2.5x), exceeding RCV.  
**Adjudicated Action:** `escalate`  
**Verification Status:** `PASSED` (Zero violations)

### Structured Rationale Facts Table (Module M3)

| Fact ID | Fact Type | Fact Value | Description |
|---|---|---|---|
| `f_rcv` | `rcv` | **0.3099** | Derived by Bayesian generative model |
| `f_observed_change` | `observed_change` | **2.5036** | Derived by Bayesian generative model |
| `f_p_real` | `p_real` | **0.9874** | Derived by Bayesian generative model |
| `f_p_error` | `p_error` | **0.0126** | Derived by Bayesian generative model |
| `f_p_stable` | `p_stable` | **0.0000** | Derived by Bayesian generative model |
| `f_action` | `action` | **escalate** | Derived by Bayesian generative model |

### Generated Provenance-Verified Narrative (Module M5)

> "The calculated probability of true progression is 99%. The calculated probability of analytical or pre-analytical error is 1%. The calculated probability of baseline biological stability is 0%. The biological reference change value threshold is 31%. The observed marker ratio is 2.50 relative to baseline. The recommended clinical action is escalate."

---
