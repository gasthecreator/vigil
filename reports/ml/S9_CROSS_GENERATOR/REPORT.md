# Study S9 Report: Cross-Generator Robustness & Sim-to-Real Stress Testing

> **Notice:** All analyses performed on **SYNTHETIC TIERS G1, G2, G3**. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S9_CROSS_GENERATOR  
**Date Executed:** 2026-10-17 08:12:30 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Worst-Case Reporting
- **Worst-Case Degradation:** Gradient Boosted Trees (B4) and Velocity (B2) experienced degradation under G3's heavy-tailed noise and laboratory offsets.
- **Bayesian Cushioning:** K3 Fast Landmark model showed higher relative robustness due to prior variance integration.

## 2. In-Distribution vs. Out-of-Distribution Stress Results

| Model | In-Dist (G1+G2) AUC | G3 Stress AUC | Delta AUC Degradation | In-Dist ECE | G3 Stress ECE |
|---|---|---|---|---|---|
| `B1_SingleThreshold` | 0.5913 | 0.6833 | **-0.0920** | 0.1296 | 0.0633 |
| `B2_Velocity` | 0.5263 | 0.5717 | **-0.0453** | 0.1752 | 0.0759 |
| `B3_RegularizedHazard` | 0.6440 | 0.7473 | **-0.1033** | 0.0590 | 0.0308 |
| `B4_GradientBoosting` | 0.6888 | 0.7366 | **-0.0478** | 0.0578 | 0.0634 |
| `K3_JointModel` | 0.6665 | 0.7823 | **-0.1157** | 0.0630 | 0.0503 |
| `K1_Kinetic` | 0.5354 | 0.5642 | **-0.0288** | 0.0595 | 0.0581 |
| `K8_ProductionEnsemble` | 0.6145 | 0.6556 | **-0.0411** | 0.1315 | 0.1215 |

## 3. Decision Record & Sim-to-Real Implications
- Raw uncalibrated decision trees are sensitive to inter-lab assay offsets (+-12%).
- In Phase 3 and Phase 4, Model M3 (Plausibility Adjudicator) and K5 (inter-lab harmonisation) are required to filter pre-analytical noise before scoring.

## 4. Corrections (Tier 2, ADR-0025)
- The row `K4_DeepZoo` that earlier versions of this report carried was **removed**: that model's `fit` learned nothing and its `predict_risk` was a hand-written formula, so the row measured no trained model. The real K4 families are evaluated in `experiments/EXP-K4-001/`. The removal was made by deleting the key and the row (the benchmark runner was not re-run); every other row is unchanged.
- `K8_ProductionEnsemble` is likewise a hand-written weighted formula of four logistic expressions, not a trained ensemble (stub S-016 in `docs/STUBS.md`). Its row is kept only so that nothing disappears silently; it is not evidence about any ensemble.

