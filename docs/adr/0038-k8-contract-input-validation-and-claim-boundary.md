# ADR-0038: K8 utilities validate inputs and narrow claims to evidence

- **Status:** Proposed
- **Date:** 2026-10-19
- **Decision owners:** Q-7 executor, subject to overseer review

## Context

K8's model card reported exact FNR/FPR, OOD and adaptive-coverage figures without a committed result-producing artifact. It also stated that the default adaptive step size came from a regret-bound calculation, but no derivation or supporting source was present. The implementation accepted invalid alpha values, malformed score/label arrays, calibration sets with no positives, prediction before fitting, and malformed OOD data without a clear contract error. The user-facing boundary also overstated synthetic acceptance behavior as general statistical guarantees.

## Decision

The utility implementations reject invalid parameters/data and require fitting before prediction. A CRC calibration cohort with no positives raises an error rather than selecting an all-alert threshold. The K8 card now describes the tests as synthetic behavioral checks, makes exchangeability and unit-of-analysis assumptions explicit, and removes numeric claims and the unsubstantiated gamma derivation.

## Verification and limits

- `packages/vigil-ml/tests/test_k8_input_contract.py`: malformed inputs and unfitted states.
- `tests/acceptance_3b/test_k8_contract.py`: unchanged contract tests; local run passed.
- The acceptance test's independent synthetic rows do not establish patient-level exchangeability, clustered-landmark behavior, real-world OOD performance, or clinical utility.
- The fixed `AdaptiveConformal.gamma` remains a contract default without an evidence-backed selection study. This ADR does not change or validate it.
