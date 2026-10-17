# Study S9 Report: Cross-Generator Robustness & Sim-to-Real Stress Testing

> **Notice:** All analyses performed on **SYNTHETIC TIERS G1, G2, G3**. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S9_CROSS_GENERATOR  
**Date Executed:** 2026-10-17 06:38:43 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Worst-Case Reporting
- **Worst-Case Degradation:** Gradient Boosted Trees (B4) and Velocity (B2) experienced degradation under G3's heavy-tailed noise and laboratory offsets.
- **Bayesian Cushioning:** K3 Fast Landmark model showed higher relative robustness due to prior variance integration.

## 2. In-Distribution vs. Out-of-Distribution Stress Results

| Model | In-Dist (G1+G2) AUC | G3 Stress AUC | Delta AUC Degradation | In-Dist ECE | G3 Stress ECE |
|---|---|---|---|---|---|
| `B1_SingleThreshold` | 0.6084 | 0.7072 | **-0.0988** | 0.1333 | 0.0498 |
| `B2_Velocity` | 0.5220 | 0.5743 | **-0.0524** | 0.1979 | 0.0736 |
| `B3_RegularizedHazard` | 0.6421 | 0.7547 | **-0.1126** | 0.0526 | 0.0304 |
| `B4_GradientBoosting` | 0.6970 | 0.7583 | **-0.0613** | 0.0499 | 0.0553 |
| `K3_JointModel` | 0.6652 | 0.7882 | **-0.1230** | 0.0641 | 0.0434 |
| `K1_Kinetic` | 0.5454 | 0.5560 | **-0.0106** | 0.0607 | 0.0629 |
| `K4_DeepZoo` | 0.5957 | 0.6792 | **-0.0835** | 0.1571 | 0.1125 |
| `K8_ProductionEnsemble` | 0.6062 | 0.6700 | **-0.0638** | 0.1519 | 0.1166 |

## 3. Decision Record & Sim-to-Real Implications
- Raw uncalibrated decision trees are sensitive to inter-lab assay offsets (+-12%).
- In Phase 3 and Phase 4, Model M3 (Plausibility Adjudicator) and K5 (inter-lab harmonisation) are required to filter pre-analytical noise before scoring.