# Study S9 Pre-Registration: Cross-Generator Robustness and Sim-to-Real Stress Testing

**Study ID:** S9_CROSS_GENERATOR  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.4; `docs/ML_PROGRAM.md` §4.6, §6, §9  

---

## 1. Study Objective and Research Question
A fundamental failure mode in synthetic algorithmic medicine is "generator overfitting"—where an algorithm learns mathematical artifacts of the specific differential equation or stochastic model used to generate data, creating illusory high performance that collapses on real clinical data.

**Core Question:** When classical baselines (B1 threshold, B2 velocity, B3 hazard, B4 gradient boosting) and the K3 joint longitudinal–survival model are trained on multi-compartment kinetic (G1) and stochastic jump (G2) generators, how much does discriminative and calibration performance degrade when evaluated on an unseen, structurally divergent generator (G3) with heavy-tailed measurement noise, random assay calibration shifts, and irregular sampling?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Tree Brittleness):** Gradient boosted trees (B4), which learn sharp decision boundaries over engineered windowed features, will experience the steepest discrimination degradation ($\Delta \text{AUROC} > 0.08$) and calibration breakdown ($\Delta \text{ECE} > 0.10$) when exposed to G3's assay shifts and heavy-tailed measurement errors.
2. **H2 (Bayesian Priors Cushion):** The K3 joint model will exhibit smaller relative degradation ($\Delta \text{AUROC} \le 0.05$) due to Bayesian shrinkage of random effects and Gaussian observational noise integration.
3. **H3 (Threshold Instability under Assay Offsets):** Fixed single-threshold decision rules (B1, CA 15-3 $\ge 30$) will suffer large shifts in false-positive rates when tested on G3 with inter-laboratory offset perturbations ($\pm 15\%$).

---

## 3. Evaluated Models
- **B1:** Single Threshold Baseline (CA 15-3 $\ge 30$ U/mL).
- **B2:** Velocity Baseline (Annualized slope).
- **B3:** Regularized Hazard Baseline (L2 penalized discrete-time logistic hazard).
- **B4:** Gradient Boosted Trees (XGBoost).
- **K3:** Bayesian Joint Longitudinal–Survival Model (Fast Landmarking production approximation).

---

## 4. Training and Stress Evaluation Regimes
1. **Training Cohort ($D_{\text{train}}$):**
   - $N = 2,000$ synthetic patients (1,000 from G1 kinetic + 1,000 from G2 jump-diffusion).
   - Standard observation schedule (3–6 month intervals).
2. **In-Distribution Test Cohort ($D_{\text{test, in}}$):**
   - $N = 1,000$ held-out patients from G1 + G2.
3. **Out-of-Distribution Stress Cohort ($D_{\text{test, G3}}$):**
   - $N = 1,000$ patients generated strictly via G3 (`vigil_sim.stress_generator` / G3 configurations):
     - Student-t ($\nu = 4$) heavy-tailed measurement noise.
     - Inter-laboratory instrument offsets ($\pm 20\%$ log-scale shifts).
     - Informative missing-not-at-random (MNAR) dropout and clinic non-attendance.
     - Accelerated marker shedding in aggressive triple-negative subtypes.

---

## 5. Endpoints and Assessment Metrics
1. **Performance Transfer Gap:**
   $$\Delta \text{AUROC} = \text{AUROC}(D_{\text{test, in}}) - \text{AUROC}(D_{\text{test, G3}})$$
   $$\Delta \text{Brier} = \text{Brier}(D_{\text{test, G3}}) - \text{Brier}(D_{\text{test, in}})$$
   $$\Delta \text{ECE} = \text{ECE}(D_{\text{test, G3}}) - \text{ECE}(D_{\text{test, in}})$$
2. **Decision Curve Analysis (DCA):** Net benefit delta across clinical risk threshold range $p_t \in [0.05, 0.30]$.
3. **Worst-Case Reporting:** All reports must prominently display the worst-case OOD performance numbers rather than in-distribution averages.

---

## 6. Pre-Registered Decision Criteria
- If any model's AUROC drops below 0.60 on G3, classify the model family as unsafe for transfer without domain-adaptation or online recalibration.
- If K3 degradation exceeds B4 degradation, log an investigation into trajectory misspecification under non-Gaussian noise.
- Commit all findings (positive, neutral, or negative) with full reproducibility instructions.
