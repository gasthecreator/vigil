# ADR-0037: ONNX runtime requires an explicit artifact

- **Status:** Proposed
- **Date:** 2026-10-19
- **Decision owners:** Q-7 executor, subject to overseer review

## Context

`VigilProductionRuntime` constructed and exported a newly randomized `SurrogateInferenceNet` whenever its path was absent, wrote it to a shared `/tmp/vigil_model.onnx`, and supplied a literal epistemic standard deviation of `0.04`. The controller had no calibration cohort, so current predictions abstained, but the runtime still created an untrained model and presented fabricated uncertainty as an input. The class name also overstated its validation status.

## Decision

The runtime requires a caller-supplied, existing ONNX file and caller-supplied epistemic uncertainty. It checks the fixed input dimension and rejects malformed or non-finite feature vectors. It never creates or writes a model artifact. The historical class name remains for compatibility, but its docstring identifies it as a research wrapper. The default K8 controller remains uncalibrated and abstains.

## Consequences and limits

- The runtime can no longer silently invent weights or uncertainty.
- This does not establish artifact provenance, signature verification, calibration, uncertainty validity, parity to a supported model, or clinical utility.
- The latency test uses an explicitly exported untrained network only to measure ONNX execution mechanics over at least 1,000 calls. It excludes preprocessing, uncertainty, calibration, API overhead and model performance.
- `VigilProductionRuntime` remains unavailable for supported clinical risk output; S-019 remains open for those claims.

## Verification

- `packages/vigil-ml/tests/test_phase3_models.py::test_runtime_requires_an_explicit_existing_model`
- `packages/vigil-ml/tests/test_phase3_models.py::test_runtime_rejects_invalid_feature_vector`
- `packages/vigil-ml/tests/test_phase3_models.py::test_explicit_onnx_export_parity_and_runtime_latency`
- `packages/vigil-ml/tests/test_phase3_models.py::test_runtime_latency_benchmark_rejects_reduced_sample_size`
