# Module M5: Synthetic Illustrations of Structured-Fact Narratives

**Governing Documents:** `docs/MASTER_PLAN.md` §6.5, §14 WP4.2; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` RR7, RR14

This document contains three illustrative synthetic scenarios generated deterministically by `vigil_ml.m5.generate_worked_journey`. The values and scenario labels are not clinical observations or ground-truth evidence for model performance. M3 outputs are conditional on unvalidated model assumptions; M5 verification checks that narrative sentences match structured facts, not whether those facts are medically correct. Nothing here establishes recurrence, benignity, analytical error, or clinical utility.

---

## Synthetic scenario: 10x marker change; model output is needs_repeat

**Journey Identifier:** `j2_surprising_repeat`
**Evidence status:** `synthetic illustration only`
**Synthetic scenario:** Illustrative generated values only: prior CA 15-3 values are near 18 U/mL; the current generated value is 180 U/mL.
**M3 model output:** `needs_repeat`
**Assumption config:** `m3_synthetic_contract_v1`
**Assumption config SHA-256:** `34af88445a43cadb25e74c8d9dbeb52ca7121916ef78d363dce272519d25daef`
**M5 fact-to-text check:** `PASSED` (zero template derivation violations; this is not model validation)

### Structured Rationale Facts Table (Module M3)

| Fact ID | Fact Type | Fact Value | Description |
|---|---|---|---|
| `f_rcv` | `rcv` | **0.3099** | Experimental M3 output under fixed illustrative assumptions |
| `f_observed_change` | `observed_change` | **10.0022** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_real` | `p_real` | **0.0000** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_error` | `p_error` | **1.0000** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_stable` | `p_stable` | **0.0000** | Experimental M3 output under fixed illustrative assumptions |
| `f_action` | `action` | **needs_repeat** | Experimental M3 output under fixed illustrative assumptions |

### Generated Provenance-Verified Narrative (Module M5)

> "Under the model assumptions, the real-change probability is 0%. Under the model assumptions, the gross-error probability is 100%. Under the model assumptions, the stable-component probability is 0%. The biological reference change value threshold is 31%. The observed marker ratio is 10.00 relative to baseline. The recommended clinical action is needs_repeat."

---

## Synthetic scenario: 1.15x marker change; model output is explained

**Journey Identifier:** `false_alarm_explained`
**Evidence status:** `synthetic illustration only`
**Synthetic scenario:** Illustrative generated values only: CA 15-3 changes from 20 to 23 U/mL; this scenario does not establish the cause or clinical significance of the change.
**M3 model output:** `explained`
**Assumption config:** `m3_synthetic_contract_v1`
**Assumption config SHA-256:** `34af88445a43cadb25e74c8d9dbeb52ca7121916ef78d363dce272519d25daef`
**M5 fact-to-text check:** `PASSED` (zero template derivation violations; this is not model validation)

### Structured Rationale Facts Table (Module M3)

| Fact ID | Fact Type | Fact Value | Description |
|---|---|---|---|
| `f_rcv` | `rcv` | **0.3099** | Experimental M3 output under fixed illustrative assumptions |
| `f_observed_change` | `observed_change` | **1.1502** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_real` | `p_real` | **0.0114** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_error` | `p_error` | **0.0046** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_stable` | `p_stable` | **0.9840** | Experimental M3 output under fixed illustrative assumptions |
| `f_action` | `action` | **explained** | Experimental M3 output under fixed illustrative assumptions |

### Generated Provenance-Verified Narrative (Module M5)

> "Under the model assumptions, the real-change probability is 1%. Under the model assumptions, the gross-error probability is 0%. Under the model assumptions, the stable-component probability is 98%. The biological reference change value threshold is 31%. The observed marker ratio is 1.15 relative to baseline. The recommended clinical action is explained."

---

## Synthetic scenario: 2.5x marker change; model output is escalate

**Journey Identifier:** `real_progression_escalate`
**Evidence status:** `synthetic illustration only`
**Synthetic scenario:** Illustrative generated values only: CA 15-3 changes from 15 to 37.8 U/mL; this scenario does not establish recurrence or its cause.
**M3 model output:** `escalate`
**Assumption config:** `m3_synthetic_contract_v1`
**Assumption config SHA-256:** `34af88445a43cadb25e74c8d9dbeb52ca7121916ef78d363dce272519d25daef`
**M5 fact-to-text check:** `PASSED` (zero template derivation violations; this is not model validation)

### Structured Rationale Facts Table (Module M3)

| Fact ID | Fact Type | Fact Value | Description |
|---|---|---|---|
| `f_rcv` | `rcv` | **0.3099** | Experimental M3 output under fixed illustrative assumptions |
| `f_observed_change` | `observed_change` | **2.5036** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_real` | `p_real` | **0.9874** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_error` | `p_error` | **0.0126** | Experimental M3 output under fixed illustrative assumptions |
| `f_p_stable` | `p_stable` | **0.0000** | Experimental M3 output under fixed illustrative assumptions |
| `f_action` | `action` | **escalate** | Experimental M3 output under fixed illustrative assumptions |

### Generated Provenance-Verified Narrative (Module M5)

> "Under the model assumptions, the real-change probability is 99%. Under the model assumptions, the gross-error probability is 1%. Under the model assumptions, the stable-component probability is 0%. The biological reference change value threshold is 31%. The observed marker ratio is 2.50 relative to baseline. The recommended clinical action is escalate."

---
