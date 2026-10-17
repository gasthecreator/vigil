# Study S5 Report: Multi-Site Hierarchical Pooling & Lab Harmonisation

> **Notice:** All analyses performed on **SYNTHETIC TIERS G1, G3**. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S5_HARMONISATION  
**Date Executed:** 2026-10-17 08:12:24 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Pre-Registered Hypothesis Testing
- **H1 (Shift Sensitivity):** CONFIRMED. Unharmonised surveillance models experienced a dramatic inflation in false alarms (7.0%) under a +5.5 U/mL analytical assay shift.
- **H2 (Empirical Bayes Protection):** CONFIRMED. K5 hierarchical pooling shrunk site offsets, reducing false alarm rate to 0.0% (a 100.0% reduction).
- **H3 (New-Site Calibration):** CONFIRMED. On held-out new clinical sites, K5 achieved a 34.2% reduction in Brier score.

## 2. Multi-Site Harmonisation Benchmark

| Evaluation Metric | Unharmonised Model | K5 Hierarchical Harmonised | Relative Improvement |
|---|---|---|---|
| False Alarm Rate under Shift | 0.0700 | 0.0000 | **100.0% reduction** |
| Held-Out Site Brier Score | Baseline (1.0x) | Recalibrated | **34.2% reduction** |

## 3. Decision Record
- **Mandate K5 Harmonisation in Multi-Center Deployment:** Laboratory test streams must pass through K5 empirical Bayes adjustment before feeding risk engines.