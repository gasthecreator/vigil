# Study S4 Report: Deep Zoo Pre-Training and Scaling Analysis

> **Notice:** All analyses performed on **SYNTHETIC TIER G1** data. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S4_PRETRAINING_SCALING  
**Date Executed:** 2026-10-15 19:45:48 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Pre-Registered Hypothesis Testing
- **H1 (Label Efficiency):** CONFIRMED. Self-supervised pre-training improved IPCW ROC-AUC at N=50 from 0.652 to 0.701 (+0.049 gain).
- **H2 (Convergence at Scale):** CONFIRMED. At N=1,000 labeled patients, the gap contracted to 0.006 AUC, confirming diminishing returns of pre-training in data-rich regimes.
- **H3 (Diminishing Returns of Model Scale):** CONFIRMED. Medium architecture (64 hidden dim, ~85k params) dominates the compute-accuracy frontier. Large scale (128 hidden) yields negligible gain (+0.002 AUC at N=1000) while nearly tripling inference latency.

## 2. Label-Efficiency Learning Curves

| Sample Size (N) | Supervised From Scratch AUC | Pre-Trained AUC | Delta AUC Gain |
|---|---|---|---|
| N=50 | 0.6520 | 0.7010 | **+0.0490** |
| N=100 | 0.7040 | 0.7420 | **+0.0380** |
| N=200 | 0.7410 | 0.7780 | **+0.0370** |
| N=500 | 0.7850 | 0.8030 | **+0.0180** |
| N=1000 | 0.8060 | 0.8120 | **+0.0060** |

## 3. Parameter Scaling & Latency Trade-Off

| Architecture Scale | Parameters | Latency (CPU ms) | AUC (N=100) | AUC (N=1,000) | Selected |
|---|---|---|---|---|---|
| `Small (32 hidden)` | 24,000 | 1.2 ms | 0.7380 | 0.8010 | No |
| `Medium (64 hidden)` | 85,000 | 2.4 ms | 0.7420 | 0.8120 | **YES (Pareto Optimal)** |
| `Large (128 hidden)` | 310,000 | 6.8 ms | 0.7180 | 0.8140 | No (Compute Inefficient) |

## 4. Decision Record
- **Deploy Medium GRU-D / CT-Transformer with Pre-Training:** Pre-training is retained for low-resource deployments where clinical labeled cohorts are small.