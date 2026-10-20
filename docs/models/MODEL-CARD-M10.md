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

<!-- measured:start -->
## Measured results (script-written)

Source: `reports/ml/STUDY_M10_MISSED_SIGNALS.json` (pre-registered `docs/studies/PREREG-M10.md`; synthetic facilities with injected ground truth).

These statuses are preserved as the original script output. Q-6 invalidated K2's anytime-valid guarantee, and the M10 facility path used unvalidated M3 inputs; they are not current validation evidence.

| Hypothesis | Historical result |
|---|---|
| H1_sensitivity_precision | historical result: SUPPORTED |
| H2_delay_accuracy | historical result: SUPPORTED |
| H3_specificity_and_benign_spikes | historical result: SUPPORTED |
| H4_pipeline_only_decoupling | historical result: SUPPORTED |
| H5_small_cell_privacy | historical result: SUPPORTED |

- Sensitivity 0.966, precision 1.000; mean delay error 35.5 days.
- Privacy: k-anonymity floor 5, neutral register verified: True.
- Facility-derived statistics are disabled by ADR-0054 until the detector and analyte-specific assumptions are validated.
<!-- measured:end -->
