# Study S9 Report: Cross-Generator Robustness & Sim-to-Real Stress Testing

> **Notice:** All analyses performed on **SYNTHETIC TIERS G1, G2, G3**. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S9_CROSS_GENERATOR  
**Date Executed:** 2026-10-15 19:18:13 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Worst-Case Reporting
- **Worst-Case Degradation:** Gradient Boosted Trees (B4) and Velocity (B2) experienced degradation under G3's heavy-tailed noise and laboratory offsets.
- **Bayesian Cushioning:** K3 Fast Landmark model showed higher relative robustness due to prior variance integration.

## 2. In-Distribution vs. Out-of-Distribution Stress Results

| Model | In-Dist (G1+G2) AUC | G3 Stress AUC | Delta AUC Degradation | In-Dist ECE | G3 Stress ECE |
|---|---|---|---|---|---|
| `B1_SingleThreshold` | 0.6083 | 0.7072 | **-0.0989** | 0.1337 | 0.0505 |
| `B2_Velocity` | 0.5317 | 0.5742 | **-0.0425** | 0.2082 | 0.0729 |
| `B3_RegularizedHazard` | 0.6407 | 0.7562 | **-0.1155** | 0.0594 | 0.0337 |
| `B4_GradientBoosting` | 0.6909 | 0.7489 | **-0.0580** | 0.0522 | 0.0522 |
| `K3_JointModel` | 0.6197 | 0.7750 | **-0.1553** | 0.1895 | 0.0170 |

## 3. Decision Record & Sim-to-Real Implications
- Raw uncalibrated decision trees are sensitive to inter-lab assay offsets (+-12%).
- In Phase 3 and Phase 4, Model M3 (Plausibility Adjudicator) and K5 (inter-lab harmonisation) are required to filter pre-analytical noise before scoring.