# Model Card: Model K1 — Hybrid Mechanistic–Neural State-Space Model ("Kinetic")

**Model Identifier:** `MODEL-K1-KINETIC-HYBRID`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §3.1, §6, §9  
**Evaluation Status:** Evaluated on Synthetic Tiers G1, G2, G3 (`reports/ml/BENCHMARK_REPORT.md`, `reports/ml/S1_SPARSITY/REPORT.md`)  

---

## 1. Model Overview and Intended Use
Model K1 is Vigil's flagship continuous-time mechanistic surveillance engine. It formulates post-treatment breast cancer monitoring as a continuous-discrete state-space filtering problem where latent disease burden evolves continuously according to coupled physiological differential equations, while blood biomarkers and clinical assessments are observed at discrete, sparse, and irregular intervals.

### Primary Intended Use
Continuous estimation of subclinical metastatic burden across anatomical compartments (locoregional, bone, liver, lung, brain) and anytime-valid recurrence risk computation, providing interpretable biological parameters (tumor doubling times, shedding rates, organ injury states) rather than black-box point probabilities.

---

## 2. Mathematical Formulation & Latent State Dynamics
### Latent State Vector $z(t) \in \mathbb{R}^9$
- $B_{\text{loco}}(t), B_{\text{bone}}(t), B_{\text{liver}}(t), B_{\text{lung}}(t), B_{\text{brain}}(t)$: Tumor burdens across 5 anatomical niches.
- $M_{\text{ca153}}(t), M_{\text{cea}}(t)$: Circulating vascular marker pools (filtered integrals of tumor shedding minus metabolic clearance).
- $O_{\text{liver}}(t), O_{\text{bone}}(t)$: Organ dysfunction / cellular injury states (elevated transaminases, alkaline phosphatase).

### Continuous Dynamics (Coupled ODE / SDE)
$$\frac{d B_c}{dt} = g_c B_c \left(1 - \frac{B_c}{K_c}\right) + f_\theta(z(t))_c$$
$$\frac{d M_k}{dt} = \sum_{c=1}^5 s_{k,c} B_c - c_k M_k$$
$$\frac{d O_m}{dt} = \kappa_m B_m - \gamma_m O_m$$

where $g_c$ is compartment-specific exponential growth rate, $K_c$ is carrying capacity, $s_{k,c}$ is shedding rate, $c_k$ is clearance rate (e.g. CA 15-3 clearance $c \approx 0.085/\text{day}$, half-life ~8 days), and $f_\theta$ is a bounded Lipschitz continuous neural residual drift capturing non-linear biological couplings.

---

## 3. Four Supported Inference Routes
1. **Sub-10ms Online Filtering (UKF / Particle Filter):**
   - Continuous-discrete Unscented Kalman Filter updating in $< 2.5\text{ ms}$ on single-core CPU.
   - Closed-form measurement updates handle arbitrary missing analyte patterns via observation selection masking.
2. **Amortized Variational Inference (Amortized VI):**
   - Bidirectional recognition network mapping irregular longitudinal sequences to approximate posterior distributions over latent initial states and kinetic parameters.
3. **Simulation-Based Inference (SNPE):**
   - Sequential Neural Posterior Estimation for amortized parameter recovery without explicit likelihood evaluation.
4. **Reference Gold-Standard MCMC (NUTS):**
   - Hamiltonian Monte Carlo / No-U-Turn Sampler baseline for posterior verification and Simulation-Based Calibration (SBC).

---

## 4. Verification & Validation Metrics
- **Simulation-Based Calibration (SBC):** Exact conjugate posterior rank test satisfies Kolmogorov-Smirnov uniformity test ($p > 0.05$).
- **Parameter Recovery:** Tumor doubling time recovery achieves correlation $r > 0.90$ with 90% credible interval empirical coverage $\ge 85\%$.
- **Online Filtering Latency:** Mean $1.8\text{ ms}$, p95 $3.2\text{ ms}$ on workstation CPU (target $< 10\text{ ms}$).
- **Discrimination (VigilBench Synthetic G1):** IPCW ROC-AUC $0.78\text{--}0.82$ across visit sparsity depths $V \in \{3, 4, 6, 10, 20\}$.

---

## 5. Failure Modes and Guardrails
1. **Severe Model Misspecification:** When tested on Generator G3 (heavy-tailed noise, unmodeled laboratory assay shifts), raw kinetic state estimates degrade. Mitigated by upstream filtering through Model K5 (Lab Harmonisation) and Model M3 (Plausibility Adjudicator).
2. **In vitro Hemolysis Spikes:** Transient pre-analytical contamination could be misattributed to aggressive tumor shedding. Guarded by the UKF innovation gate and Student-t measurement noise bounds.
3. **Synthetic Foundation Notice:** All kinetics were validated on synthetic simulator cohorts. Clinical parameter distributions must be recalibrated against real multi-center retrospective cohorts in Phase 9.
