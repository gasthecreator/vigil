# Model Card: M10 — Missed-signal quality audit

**Model Identifier:** `MODEL-M10-MISSED-SIGNALS`  
**Model Version:** M10-V2 rebuild (reproducible study artefact)  
**Date:** 2026-10-19  
**Module Reference:** study scripts + quality audit APIs (Phase 7b/8a)  
**Governing Documents:** `docs/studies/PREREG-M10.md`, `reports/ml/STUDY_M10_MISSED_SIGNALS.json`, ADR-0016/0017  
**Claim status:** Simulation / synthetic evaluation only. Circular validation issues found historically were rebuilt (P14); treat committed JSON as script-owned.

---

## 1. Intended use
Aggregate quality-audit signals for missed follow-up / missed escalation patterns under consent and privacy controls. Not a per-patient diagnosis.

## 2. Privacy
Consent-gated aggregate use; raw patient export paths must remain closed (acceptance suites).

## 3. Limitations
Partner real-world performance unknown until Phase 9. Reproduction via `make reproduce` / study verify scripts.
