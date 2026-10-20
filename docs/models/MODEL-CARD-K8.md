# Model Card: K8 Calibration and OOD Utilities

**Identifier:** `MODEL-K8-CONFORMAL-SUITE`
**Review date:** 2026-10-19
**Implementation:** `packages/vigil-ml/vigil_ml/k8.py`
**Contract:** [`docs/ml/K2-K8-CONTRACT.md`](../ml/K2-K8-CONTRACT.md)
**Behavioral suite:** `tests/acceptance_3b/test_k8_contract.py` (unchanged overseer-owned tests)

## Intended use and limits

K8 contains a threshold calibrator, a Mahalanobis-distance outlier gate, and an adaptive miscoverage update. These are post-processing utilities; K8 is not a predictive model and does not produce recurrence probabilities. It is research code and is not connected to a predictor evaluated in prospective clinical data or a calibrated runtime artifact.

The passing behavioral contract is limited to the synthetic distributions and checks encoded in `tests/acceptance_3b/test_k8_contract.py`. It does not establish a patient-level guarantee, clinical utility, robustness to real assay/site shift, or validity under repeated landmarks or clustered observations. Do not present a K8 threshold as a patient-specific risk.

## Implemented behavior

### Conformal threshold

`ConformalRiskController.fit` uses positive calibration scores and the supplied `alpha` to choose a lower-tail order statistic. `decide` alerts when a score is at or above the fitted threshold. The implementation now rejects invalid alpha, malformed/non-finite scores, non-binary labels, a calibration cohort with no positive labels, and prediction before fitting.

Any finite-sample statement depends on exchangeability of the calibration and test **units** and on a valid score/label definition. The code does not group repeated observations by patient, establish exchangeability for clinical cohorts, or calibrate the score itself. The acceptance test uses independent synthetic rows and does not test clustered patient records.

### OOD gate

`OODGate.fit` estimates a mean and regularized covariance from the supplied inlier reference rows, then sets a distance cutoff from their empirical distance quantile. `is_ood` compares new rows with that fitted reference. The default target quantile and covariance regularizer are implementation parameters, not estimates of clinical safety. This empirical Mahalanobis rule has no general shift-detection guarantee; non-Gaussian, multimodal, sparse, or changing feature distributions can invalidate its behavior.

### Adaptive update

`AdaptiveConformal.update` adjusts its running alpha using the observed coverage indicator and the caller-supplied `gamma`. The implementation default is fixed by the contract; it was not derived from a retrieved regret-bound calculation or selected by a registered calibration study. The contract checks one synthetic scale-drift stream only. Broader coverage claims, feedback-delay behavior, patient-level adaptation, and safe deployment are unestablished.

## Evidence and verification

The immutable acceptance suite was run locally after input-contract hardening:

```text
....                                                                     [100%]
4 passed in 1.83s
```

Additional validation tests are in `packages/vigil-ml/tests/test_k8_input_contract.py`. No standalone results artifact currently supports numerical performance claims for K8. The numerical table previously in this card was removed because its figures had no committed result-producing script and could not be independently traced. The earlier assertion that the adaptive step size came from a regret bound was also removed because no supporting derivation was present.

## Configuration and provenance

- CRC `alpha` is provided to the controller and its threshold is fitted from calibration scores. The caller must identify the calibration unit, cohort, score producer, label horizon and split in a preregistered study.
- OOD reference rows and distance cutoff are fitted from the supplied inlier dataset. The default alpha is an algorithm setting, not a clinical false-alarm target.
- ACI `gamma` is a fixed algorithm setting; this repository contains no evidence that the default is optimal or clinically appropriate.
- No output from these utilities is eligible for a patient-facing decision until a model-specific score, patient-level calibration design, input provenance, monitoring policy and independent review are established.
