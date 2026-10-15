# Study S4 Pre-Registration: Deep Zoo Pre-Training and Scaling Analysis

**Study ID:** S4_PRETRAINING_SCALING  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.1; `docs/ML_PROGRAM.md` §1 (H-A), §3.4, §6  

---

## 1. Study Objective and Research Question
Deep neural architectures for irregular longitudinal time series (GRU-D, Continuous-Time Transformer, Neural CDE) risk severe overfitting when clinical labels are scarce. This study investigates whether self-supervised pre-training (masked analyte imputation and contrastive future prediction) on unlabeled trajectory sequences improves label efficiency, and where parameter scaling stops providing utility.

**Core Question:** Does self-supervised representation pre-training significantly boost IPCW ROC-AUC in small-sample regimes ($N \le 200$), and does increasing parameter scale from Medium (64 hidden) to Large (128 hidden) improve surveillance performance or merely add latency?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Label Efficiency Gain):** Self-supervised pre-training will yield a statistically significant improvement in 1-year IPCW ROC-AUC ($> +0.03$) at sample sizes $N = 50$ and $N = 100$.
2. **H2 (Convergence at Scale):** At large sample sizes ($N = 1,000$), the performance delta between pre-trained and randomly initialized models will contract to $< 0.015$.
3. **H3 (Diminishing Returns of Model Scale):** Medium architectures (~85k params) will dominate the compute-accuracy Pareto frontier; Large architectures (~310k params) will exhibit negligible AUC improvement ($< 0.005$) while incurring $> 2.5\times$ higher inference latency.

---

## 3. Evaluated Dimensions
- **Sample Sizes (Labeled Patients):** $N \in \{50, 100, 200, 500, 1000\}$
- **Pre-Training Status:**
  - `Baseline (From Scratch)`: Supervised end-to-end training with random initialization.
  - `Pre-Trained`: Masked-analyte + contrastive trajectory pre-training on 10,000 unlabeled simulated sequences.
- **Model Scales:**
  - `Small`: hidden_dim = 32 (~24k parameters)
  - `Medium`: hidden_dim = 64 (~85k parameters)
  - `Large`: hidden_dim = 128 (~310k parameters)

---

## 4. Primary and Secondary Endpoints
1. **Primary Metric:** IPCW Time-Dependent ROC-AUC at horizon $\tau = 365$ days.
2. **Secondary Metrics:**
   - Single-patient CPU inference latency ($p50, p95$).
   - Expected Calibration Error (ECE).
   - Training FLOPs and parameter counts.

---

## 5. Pre-Registered Decision Criteria
Per `docs/ML_PROGRAM.md` §3.4 & §6:
- If pre-training fails to deliver $\ge +0.02$ AUC gain at $N \le 100$, pre-training will not be deployed to production to avoid unnecessary pipeline complexity.
- If Large scale does not beat Medium scale by at least $+0.01$ AUC with non-overlapping bootstrap CIs, Medium scale is selected as the release architecture.
