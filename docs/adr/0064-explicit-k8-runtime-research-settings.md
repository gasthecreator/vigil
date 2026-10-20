# ADR-0064: Make K8 runtime assumptions explicit and dimension-aware

- Status: Accepted
- Date: 2026-10-20
- Decision owner: repository owner (Q-7 quality and provenance instruction)

## Context

The `conformal_k8.py` runtime controller embedded OOD, covariance, uncertainty, interval, alert-tier, and adaptive-update values in source. Its OOD cutoff of 45 was described as a 15-dimensional chi-square cutoff even though the wrapper accepts arbitrary feature dimensions. It initialized an uncalibrated alert threshold to 0.28, and its high-uncertainty explanation advised an expedited retest without a validated decision rule. The model card already states that K8 has no patient-level or clinical validation.

## Decision

- Put every numerical research setting used by the runtime controller in `k8_research_config_v1.json`, marked `unvalidated_research_defaults` with an explicit statement that no clinical source or sensitivity study supports the values.
- Validate the configuration schema and numeric domains when loading it. Compute an effective canonical SHA-256, including explicit constructor overrides, and attach the configuration ID and hash to each prediction result.
- Leave the alert threshold unset until calibration. Derive the Mahalanobis chi-square cutoff from the configured tail probability and the fitted feature dimension, rather than assuming 15 dimensions.
- Require calibration before online adaptation and reject non-boolean feedback. Replace the high-uncertainty retest recommendation with research-only abstention language.
- Keep this wrapper separate from the `k8.py` behavioral contract; neither implementation validates the other. No K8 performance or clinical claim follows.

## Consequences

The settings are auditable and dimension-aware, but they remain unvalidated legacy research assumptions. The change does not select or tune them, validate the score model, establish patient-level exchangeability, or satisfy the K8 study requirements in package F. A registered sensitivity and calibration study and reconciliation of the two K8 implementations remain open.

## Evidence

- `packages/vigil-ml/tests/test_k8_input_contract.py`: configuration identity/hash, dynamic degrees-of-freedom cutoff, and adaptation preconditions.
- `packages/vigil-ml/tests/test_phase3_models.py`: runtime abstention, OOD and mechanics regression coverage.
- Local verification: 27 focused tests passed and 1 skipped; strict mypy passed for `conformal_k8.py` and `runtime.py`; Ruff and formatting checks passed. The `vigil-ml` wheel built locally and the archive contains `k8_research_config_v1.json` at the expected package path.
