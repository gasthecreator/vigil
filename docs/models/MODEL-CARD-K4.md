# Model Card: Model K4 — Deep Irregular-Time Model Zoo

**Model Identifier:** `MODEL-K4-DEEP-IRREGULAR-ZOO`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.1; `docs/ML_PROGRAM.md` §3.4, §6, §9  
**Evaluation Status:** Evaluated across sample size ladders and model scales (`reports/ml/S4_PRETRAINING_SCALING/REPORT.md`)  

---

## 1. Model Overview and Intended Use
Model K4 implements a suite of deep neural network architectures specifically designed for sparse, irregular, and multi-analyte longitudinal clinical trajectories. Standard recurrent neural networks assume equally spaced discrete observations and fail when inter-visit intervals vary from weeks to months or when analytes are missing non-at-random (MNAR).

### Architectures Implemented
1. **GRU-D (Che et al. 2018):** Continuous exponential hidden state decay $\gamma_h(t) = \exp(-\max(0, W_h \Delta t))$ coupled with input feature decay toward historical running averages and explicit binary observation masks.
2. **Continuous-Time Transformer (CT-Transformer):** Causal multi-head self-attention with relative temporal exponential distance biases $\operatorname{Bias}(i, j) = -\lambda |t_i - t_j|$.
3. **Neural CDE (Kidger et al. 2020):** Continuous-time Controlled Differential Equations driven by cubic Hermite spline paths through irregular observations.
4. **GRU-ODE-Bayes (De Brouwer et al. 2019):** Continuous latent drift between irregular observations parameterized by neural vector fields with Bayesian update jumps at visit arrivals.

All sequence encoders are strictly forward-only (causal), preventing future temporal leakage.

---

## 2. Pre-Training & Label Efficiency (Study S4)
To overcome the extreme scarcity of clinical recurrence events, Model K4 incorporates two self-supervised pre-training tasks on unlabeled simulated trajectory sequences:
1. **Masked Analyte Imputation:** Self-supervised reconstruction of artificially masked biomarker values.
2. **Contrastive Future State Prediction:** InfoNCE contrastive objective distinguishing true multi-month patient futures from shuffled cohort distractors.

### Empirical Findings (Study S4)
- **Small Sample Gain:** Pre-training yields $+0.049$ IPCW ROC-AUC at $N = 50$ labeled patients ($0.701$ vs $0.652$) and $+0.038$ at $N = 100$ ($0.742$ vs $0.704$).
- **Pareto Optimal Scale:** The Medium architecture (hidden dimension $64$, $\sim 85\text{k parameters}$, single-patient CPU latency $2.4\text{ ms}$) achieves the optimal Pareto frontier. Large architectures ($128\text{ hidden}$, $\sim 310\text{k parameters}$, latency $6.8\text{ ms}$) show no statistically significant AUC gain ($+0.002$ at $N = 1000$) while increasing latency by $2.8\times$.

---

## 3. Input Feature Specification
- **Longitudinal Biomarkers (7 analytes):** CA 15-3, CEA, ALT, AST, ALP, total bilirubin, creatinine.
- **Continuous Time Features:** $\Delta t$ elapsed since prior visit, $\Delta t$ elapsed since adjuvant baseline.
- **Observation Indicators:** Binary mask $m_{ij} \in \{0, 1\}$ denoting whether analyte $j$ was drawn at visit $i$.
- **Baseline Clinical Context:** Patient age, primary tumor stage (I–IV), ER/PR status, HER2 amplification.

---

## 4. Limitations and Safety Constraints
1. **Black-Box Decision Surface:** Unlike Model K1, deep sequence representations lack closed-form analytical explanations. Integrated gradients and feature occlusions are used solely for auxiliary interpretability and are never presented as causal.
2. **Synthetic Pre-Training Gap:** Pre-training on simulator sequences must be supplemented with public electronic health record pre-training corpora (e.g. MIMIC-IV) prior to real-world deployment.
