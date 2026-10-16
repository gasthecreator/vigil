---
status: accepted
date: 2026-10-16
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0007. Model K1 Retained as Research Inference Module; K3 and B4 Shipped as Surveillance Baselines

## Context and Problem Statement
Model K1 was conceived in `docs/MASTER_PLAN.md` §14 (Phase 3A) and `docs/ML_PROGRAM.md` §3.1 as a hybrid mechanistic–neural state-space model for serial biomarker surveillance. Following extensive development across four genuine inference routes (amortized neural recognition, UKF particle filtering, NUTS MCMC, and neural posterior estimation), numerical verification confirmed that K1 successfully solves parameter recovery and simulation-based calibration within its own mechanistic generative world.

However, empirical evaluation across pre-registered Study S1 (`reports/ml/S1_SPARSITY/REPORT.md`) demonstrated that K1 achieves ROC-AUC of ~0.50–0.53 on `vigil-sim` cohort data, consistently losing to classical and semi-parametric baselines:
- In low-data visit regimes ($V=3$), K1 achieves AUC $0.502$ vs. K3 Joint Model ($0.730$) and B4 Gradient Boosting ($0.755$).
- Under dense surveillance ($V=10$), K1 achieves AUC $0.529$ vs. K3 ($0.808$) and B4 ($0.814$).
- Three pre-registered §13 attempts (`EXP-K1-001`, `EXP-K1-002`, `EXP-K1-003`) exploring informative prior shrinkage, interval-adaptive noise scaling, and cumulative burden integration yielded differences within bootstrap noise without closing the performance gap.

Per `docs/MASTER_PLAN.md` §13 / `docs/ML_PROGRAM.md` §3.1 / `docs/REALITY_RULES.md` RR10 ("Honest failure is a deliverable"), an explicit decision is required regarding deployment scope and project direction.

## Decision Drivers
1. **Clinical Surveillance Performance:** Patient safety requires shipping the most accurate, calibrated risk models. Deploying a model with AUC ~0.51 when validated alternatives achieve AUC > 0.80 would violate clinical safety criteria.
2. **Scientific Honesty and Truth Reset:** In accordance with `docs/REALITY_RULES.md` (RR1–RR14), engineering should not attempt to mask mechanistic model limitations with heuristic score blends or fabricated data points.
3. **Preservation of Sound Scientific Capabilities:** K1's four inference routes, ODE integrators, and identifiability analyses provide sound mechanistic inference of physiological parameters (doubling time, clearance, shedding) that remain valuable for research and counterfactual queries.

## Considered Options
- **Option 1: Continue iterative architectural rounds on K1 to force competitive AUC on vigil-sim.**  
  *Pros:* Keeps K1 as the intended flagship.  
  *Cons:* Diminishing returns; delays subsequent phases (K2, K8); risks overfitting or introducing synthetic blends.
- **Option 2: Completely delete Model K1 from the codebase.**  
  *Pros:* Simplifies the repository.  
  *Cons:* Destroys real, validated Bayesian/neural inference machinery (NumPyro NUTS, SBI NPE, particle filters, ODE solvers).
- **Option 3: Retain K1 as a research inference module; ship K3 and B4 as surveillance baselines (Selected).**  
  *Pros:* Fully aligns with MASTER_PLAN §13 fallback protocol; deploys superior predictive models (K3 Fast Landmark Joint Model and B4 Gradient Boosting) in clinical production pathways; retains K1 as a validated research module for kinetic parameter recovery and physiological explanation.

## Decision Outcome
Chosen option: **Option 3**.  
1. **Production Status:** K1 is formally closed as a research inference module and will not be deployed as the primary clinical risk predictor.
2. **Shipped Baselines:** K3 (`FastLandmarkJointModel`) and B4 (`GradientBoostingBaseline`) serve as the shipped surveillance baselines.
3. **Research Role:** K1 remains in `packages/vigil-ml/vigil_ml/k1.py` as an honest, fully validated inference module with four distinct routes (`amortized`, `ukf`, `nuts`, `npe`) for physiological parameter recovery and mechanistic explanation.
