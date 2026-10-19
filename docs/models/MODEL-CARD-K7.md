# Model Card: K7 — Causal delay / action analysis (Study S8)

**Model Identifier:** `MODEL-K7-CAUSAL`  
**Model Version:** research / simulation-validated estimators only  
**Date:** 2026-10-19  
**Module Reference:** `packages/vigil-ml/vigil_ml/causal_k7.py`  
**Governing Documents:** `docs/MASTER_PLAN.md` §6 / ML_PROGRAM §3.7; `docs/studies/PREREG-S8-K7.md`; `reports/ml/STUDY_S8_K7_CAUSAL.json`  
**Claim status:** Estimators validated on **synthetic** cohorts with known effects. **No real-data causal claim.** Literature priors remain the clinical fallback (E8) until partner data.

---

## 1. Intended use
Recover known causal risk ratios under measured confounding on simulation (Study S8), so method failure is visible before any real analysis. Not a bedside predictor; not wired as a clinician-facing risk score.

## 2. Methods
IPTW / AIPW (and related) estimators over a synthetic causal cohort generator with optional unmeasured confounding injection. Property tests in `packages/vigil-ml/tests/test_causal_k7.py`.

## 3. Limitations
- Synthetic only until Phase 9 partner data.
- Unmeasured confounding can bias estimators; the suite documents that failure mode.
- Results files must be script-written; hand edits are defects (P14/P15 history).

## 4. Evaluation
See committed `reports/ml/STUDY_S8_K7_CAUSAL.json` and phase reports for S8. Numbers are **synthetic**.
