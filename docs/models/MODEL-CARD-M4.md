# Model Card: M4 — Resource-aware test escalation ladder

**Model Identifier:** `MODEL-M4-TEST-LADDER`  
**Model Version:** contract + engine as of Tier 2 (`feat/tier2-m4-ladder`)  
**Date:** 2026-10-19  
**Module Reference:** M4 engine/registry under `packages/vigil-ml` / API route (see `docs/ml/M4-CONTRACT.md`)  
**Governing Documents:** `docs/ml/M4-CONTRACT.md`, `docs/ml/M4-WORKED-EXAMPLES.md`, evidence E20–E22  
**Claim status:** Ladder logic and audited evidence ranges ship; **no UI workstation page yet (G-21 → PR4)**; availability/cost feedback loop not closed (J6).

---

## 1. Intended use
Suggest a next diagnostic step given resource constraints, with explicit sensitivity/specificity ranges and the statement that a **negative result does not exclude** disease. Clinician remains the decision-maker.

## 2. Safety
- Stale / illustrative evidence flags must surface when sources are not current.
- Never imply diagnosis from ladder step alone.
- Abstention when inputs are insufficient.

## 3. Limitations
- Evidence rows are literature-sourced or excluded per contract; partner local prevalence may differ.
- No claim of outcome improvement without a pre-registered study on real pathways.
