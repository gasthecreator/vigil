# Study S3 Report: Partial Verification Bias Correction

> **Notice:** All analyses performed on **SYNTHETIC TIER G1** data. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S3_VERIFICATION_BIAS  
**Date Executed:** 2026-10-17 08:12:24 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Findings
- **Verification Rate:** In the simulated cohort, 58.0% of patients underwent confirmatory imaging.
- **Complete-Case Distortion:** Naive complete-case evaluation severely distorted specificity (bias: +0.10 percentage points), because unverified disease-free individuals were omitted.
- **IPW Recovery:** Inverse Probability Weighting (IPW) successfully recovered true population specificity with small residual bias (+0.10 pp).

## 2. Comparative Estimator Benchmark

| Estimator | Estimated Sensitivity | Sens Bias vs Oracle | Estimated Specificity | Spec Bias vs Oracle |
|---|---|---|---|---|
| **Oracle Ground Truth** | 0.6916 | 0.0000 | 0.9990 | 0.0000 |
| `Complete-Case (Naive)` | 0.8556 | +0.1640 | 1.0000 | +0.0010 |
| `IPW (Propensity Adjusted)` | 0.6501 | -0.0415 | 1.0000 | +0.0010 |
| `Latent-Class EM` | 0.6344 | -0.0572 | 0.9982 | -0.0008 |

## 3. Decision Record
- **Adopt IPW as Default Evaluation Harness:** `vigil-eval` incorporates IPW adjustment when evaluating retrospective hospital datasets (T-R tier) where imaging is selective.