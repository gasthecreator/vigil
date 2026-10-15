# Study S10 Report: Multi-Site Synthetic Trial & Federated Learning Feasibility (M12)

> **Notice:** All analyses performed on **SYNTHETIC MULTI-SITE DATA**. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S10_MULTISITE_SYNTHETIC_TRIAL  
**Date Executed:** 2026-10-15 19:45:51 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Pre-Registered Hypothesis Testing
- **H1 (Local Silo Failure):** CONFIRMED. Low-volume under-resourced centers suffered severe discrimination drops when trained strictly on local data (Site C Rural Mission: 0.691 AUC; Site E Community: 0.684 AUC).
- **H2 (Federated Parity):** CONFIRMED. M12 Federated Partial Pooling matched Centralized Pooling within a tiny utility delta of 0.0068 AUC (well below the pre-registered <= 0.030 threshold).
- **H3 (Equity Boost):** CONFIRMED. Participating in the federated consortium delivered an equity boost of +0.095 AUC to Site C and +0.094 AUC to Site E.

## 2. Multi-Site Consortium Benchmark

| Clinic Archetype | Patients (N) | Local-Only AUC | Centralized Pooling AUC | M12 Federated AUC | Federated vs Local Gain |
|---|---|---|---|---|---|
| `Site A Tertiary Academic` | 1,200 | 0.8120 | 0.8250 | 0.8210 | **++0.0090** |
| `Site B Regional General` | 600 | 0.7740 | 0.8140 | 0.8080 | **++0.0340** |
| `Site C Rural Mission` | 150 | 0.6910 | 0.7950 | 0.7860 | **++0.0950** |
| `Site D Cancer Center` | 400 | 0.7980 | 0.8200 | 0.8160 | **++0.0180** |
| `Site E Community Outreach` | 150 | 0.6840 | 0.7890 | 0.7780 | **++0.0940** |

## 3. Consortium Summary Metrics
- **Mean Centralized AUC:** 0.8086
- **Mean Federated AUC:** 0.8018
- **Utility Penalty ($\Delta$ AUC):** 0.0068 (Threshold: $\le 0.030$ -> **PASSED**)

## 4. Decision Record
- **Approve M12 Federated Training Architecture:** Federated empirical Bayes training preserves privacy while lifting under-resourced hospital performance to near-tertiary accuracy.