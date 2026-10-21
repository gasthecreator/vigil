# Model Card: Model M5 — Structured-Fact Narrative Renderer (Research)

**Model Identifier:** `MODEL-M5-VERIFIED-NARRATIVE`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-16  
**Module Reference:** `packages/vigil-ml/vigil_ml/m5.py` (`vigil_ml.m5.render_clinician_note`, `vigil_ml.m5.verify_narrative`, `vigil_ml.m5.generate_worked_journey`)  
**Governing Documents:** `docs/MASTER_PLAN.md` §6.5, §14 WP4.2; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` RR7, RR14  
**Acceptance Test Suite:** `tests/acceptance_p4/test_m5_contract.py` (all 8 contract tests passing)  
**Synthetic Illustrations:** [`reports/ml/M5_JOURNEYS.md`](../../reports/ml/M5_JOURNEYS.md)

---

## 1. Clinical Rationale & Intended Use

In oncological decision support, free-form generative AI models (such as commercial Large Language Models) present severe patient-safety hazards, including hallucinations, numerical drift, inappropriate reassurance, uncalibrated diagnostic certainty, and unauthorized therapeutic advice.

Model M5 is a deterministic renderer for structured M3 facts. Its verifier checks that generated sentences are permitted by those facts; it does not validate M3's model assumptions, clinical correctness, calibration, or utility. M3 remains an unvalidated research component, so these outputs are not clinical findings or advice.

### Core Safety Principles:
1. **Zero LLM on Critical Paths:** Narrative generation is 100% deterministic template-driven; no language model operates on any diagnostic or therapeutic critical path.
2. **Forbidden Claim Enforcement:** The engine strictly forbids and intercepts phrases offering definitive diagnosis ("You have cancer", "Metastasis is confirmed"), unwarranted dismissal ("There is no need to worry", "This is definitely lab error"), or unauthorized clinical orders ("Start chemotherapy now").
3. **Strict Numerical Grounding:** Every percentage, ratio, and clinical action in the narrative must trace directly to a verified entry in the underlying rationale facts table.
4. **Anti-Swap Verification:** The verifier checks semantic bindings between clauses and numbers, rejecting texts where numbers are swapped across semantic domains.
5. **Monotonic Sub-Narrative Validity:** If a clinician or system removes a factual sentence, the shortened narrative remains fully valid; adding unwarranted claims or numbers immediately invalidates it.

---

## 2. Architecture & Pipeline Mechanics

```
┌─────────────────────────────────┐
│   Structured Rationale Facts    │
│ (p_real, p_error, rcv, action)  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Deterministic Template Engine │ ──> Clinician Note Narrative
│      render_clinician_note()    │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Provenance Semantic Verifier  │
│        verify_narrative()       │
├─────────────────────────────────┤
│ • Forbidden Phrase Check        │
│ • Clause Semantic Binding       │
│ • Swap Detection                │
│ • Untraced Number Interception  │
└────────────────┬────────────────┘
                 │
                 ▼
    {"ok": True, "violations": []}
```

### Deterministic Sentence Templates

| Fact Type | Template Sentence Structure | Example Output |
|---|---|---|
| `p_real` | `"Under the model assumptions, the real-change probability is {pct}%."` | `"Under the model assumptions, the real-change probability is 99%."` |
| `p_error` | `"Under the model assumptions, the gross-error probability is {pct}%."` | `"Under the model assumptions, the gross-error probability is 1%."` |
| `p_stable` | `"Under the model assumptions, the stable-component probability is {pct}%."` | `"Under the model assumptions, the stable-component probability is 0%."` |
| `rcv` | `"The biological reference change value threshold is {pct}%."` | `"The biological reference change value threshold is 31%."` |
| `observed_change` | `"The observed marker ratio is {ratio:.2f} relative to baseline."` | `"The observed marker ratio is 2.50 relative to baseline."` |
| `action` | `"The recommended clinical action is {action}."` | `"The recommended clinical action is escalate."` |

---

## 3. Semantic Verification Engine

The verifier executes four sequential validation layers on candidate texts:

1. **Forbidden Claim Detection:**
   Case-insensitive substring search against the safety blacklist:
   - `"you have cancer"`
   - `"metastasis is confirmed"`
   - `"there is no need to worry"`
   - `"start chemotherapy now"`
   - `"this is definitely lab error"`

2. **Clause-Level Semantic Binding & Swap Detection:**
   The text is segmented into sentences. Each sentence is analyzed for its semantic topic:
   - If a sentence discusses progression, its percentage must match `p_real` from facts.
   - If a sentence discusses analytical error, its percentage must match `p_error` from facts.
   - If a sentence discusses baseline stability, its percentage must match `p_stable` from facts.
   - If a sentence discusses RCV, its percentage must match `rcv` from facts.
   - If two percentages are swapped between sentences, both sentences trigger semantic binding violations and are rejected.

3. **Untraced Number Interception:**
   Every numeric token in the entire narrative is extracted and verified against the allowable values derived from the fact table. Unwarranted numbers (e.g. `"Expected delay is 14 days."` or mutated `"91%"`) trigger immediate rejection.

4. **Monotonic Sub-Narrative Invariance:**
   Any subset of valid factual sentences is accepted, allowing flexible downstream UI display while ensuring partial text remains truthful.

---

## 4. Worked Clinical Journeys

Three synthetic illustrations are generated by code (`reports/ml/M5_JOURNEYS.md`). Their scenario labels are not clinical truth, and verifier success only means that narrative text matches structured facts:

1. **Synthetic scenario (10x marker change $\to$ model output `needs_repeat`):**
   - Context: Illustrative generated values near 18 U/mL followed by 180 U/mL. The scenario does not establish the cause of the change.
   - Adjudication: $p_{\text{error}} = 100\%$, $p_{\text{real}} = 0\%$, action = `needs_repeat`.
   - Narrative: *"The calculated probability of true progression is 0%. The calculated probability of analytical or pre-analytical error is 100%. The calculated probability of baseline biological stability is 0%. The biological reference change value threshold is 31%. The observed marker ratio is 10.00 relative to baseline. The recommended clinical action is needs_repeat."*
   - Verifier Status: **`ok: True`** (0 violations).

2. **Synthetic scenario (1.15x marker change $\to$ model output `explained`):**
   - Context: Illustrative generated values change from 20 to 23 U/mL. The scenario does not establish benignity or clinical significance.
   - Adjudication: $p_{\text{stable}} = 98\%$, action = `explained`.
   - Verifier Status: **`ok: True`** (0 violations).

3. **Synthetic scenario (2.5x marker change $\to$ model output `escalate`):**
   - Context: Illustrative generated values change from 15 to 37.8 U/mL. This does not establish recurrence or its cause.
   - Adjudication: $p_{\text{real}} = 99\%$, action = `escalate`.
   - Verifier Status: **`ok: True`** (0 violations).

---

## 5. Verification & Acceptance Testing

Verified by independent test suite `tests/acceptance_p4/test_m5_contract.py`:
- `test_round_trip_verifies`: 200 random fact tables render and verify `ok: True`.
- `test_number_mutations_rejected`: Replaced percentage (e.g. 91%), swapped percentages, and novel numbers are strictly rejected.
- `test_forbidden_claims_rejected`: All five forbidden sentences rejected.
- `test_empty_facts_safe_and_removal_ok`: Empty facts produce safe default note; sentence removal preserves validity.
