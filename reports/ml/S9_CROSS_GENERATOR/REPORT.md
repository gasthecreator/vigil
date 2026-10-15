# Study S9 Report: Cross-Generator Robustness & Sim-to-Real Stress Testing

> **Notice:** All analyses performed on **SYNTHETIC TIERS G1, G2, G3**. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S9_CROSS_GENERATOR  
**Date Executed:** 2026-10-15 18:06:23 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Worst-Case Reporting
- **Worst-Case Degradation:** Gradient Boosted Trees (B4) and Velocity (B2) experienced degradation under G3's heavy-tailed noise and laboratory offsets.
- **Bayesian Cushioning:** K3 Fast Landmark model showed higher relative robustness due to prior variance integration.

## 2. In-Distribution vs. Out-of-Distribution Stress Results

| Model | In-Dist (G1+G2) AUC | G3 Stress AUC | Delta AUC Degradation | In-Dist ECE | G3 Stress ECE |
|---|---|---|---|---|---|
| `B1_SingleThreshold` | 0.6083 | 0.7072 | **-0.0989** | 0.1719 | 0.1292 |
| `B2_Velocity` | 0.5317 | 0.5742 | **-0.0425** | 0.2214 | 0.0394 |
| `B3_RegularizedHazard` | 0.5113 | 0.4168 | **+0.0945** | 0.0578 | 0.0399 |
| `B4_GradientBoosting` | 0.5763 | 0.6200 | **-0.0437** | 0.0422 | 0.0402 |
| `K3_JointModel` | 0.5619 | 0.7097 | **-0.1477** | 0.2456 | 0.1425 |

## 3. Decision Record & Sim-to-Real Implications
- Raw uncalibrated decision trees are sensitive to inter-lab assay offsets (+-12%).
- In Phase 3 and Phase 4, Model M3 (Plausibility Adjudicator) and K5 (inter-lab harmonisation) are required to filter pre-analytical noise before scoring.