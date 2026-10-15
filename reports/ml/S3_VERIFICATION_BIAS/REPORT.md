# Study S3 Report: Partial Verification Bias Correction

> **Notice:** All analyses performed on **SYNTHETIC TIER G1** data. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S3_VERIFICATION_BIAS  
**Date Executed:** 2026-10-15 18:06:16 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Findings
- **Verification Rate:** In the simulated cohort, 58.0% of patients underwent confirmatory imaging.
- **Complete-Case Distortion:** Naive complete-case evaluation severely distorted specificity (bias: +0.21 percentage points), because unverified disease-free individuals were omitted.
- **IPW Recovery:** Inverse Probability Weighting (IPW) successfully recovered true population specificity with small residual bias (+0.21 pp).

## 2. Comparative Estimator Benchmark

| Estimator | Estimated Sensitivity | Sens Bias vs Oracle | Estimated Specificity | Spec Bias vs Oracle |
|---|---|---|---|---|
| **Oracle Ground Truth** | 0.7411 | 0.0000 | 0.9979 | 0.0000 |
| `Complete-Case (Naive)` | 0.9092 | +0.1682 | 1.0000 | +0.0021 |
| `IPW (Propensity Adjusted)` | 0.7371 | -0.0039 | 1.0000 | +0.0021 |
| `Latent-Class EM` | 0.7175 | -0.0236 | 0.9982 | +0.0003 |

## 3. Decision Record
- **Adopt IPW as Default Evaluation Harness:** `vigil-eval` incorporates IPW adjustment when evaluating retrospective hospital datasets (T-R tier) where imaging is selective.