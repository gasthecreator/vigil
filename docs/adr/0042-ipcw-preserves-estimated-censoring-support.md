# ADR-0042: Preserve the estimated censoring survival in IPCW

## Status

Accepted for the Q-7 data and estimand repair. This is an evaluation contract
correction, not evidence that any model or historical result is valid.

## Context

`KaplanMeierEstimate.predict_survival` floored every censoring-survival estimate
at `1e-4`. `compute_ipcw_weights` then inverted that altered value, silently
capping IPCW weights at 10,000. The floor was absent from the ML Program and
the registered experiment protocols. It changes the estimator for sufficiently
large cohorts and hides when the observed censoring distribution has no support
at a requested time.

## Decision

- Return the Kaplan–Meier estimate without a positive probability floor.
- Compute IPCW weights from that estimate. Fail closed if a required inverse is
  zero-support or non-finite; do not cap weights implicitly.
- Preserve existing experiment artifacts. A result produced with the old code
  remains evidence for its recorded source only. Before using corrected metrics
  to make a model-selection claim, preregister or amend the applicable study
  under the ML Program and record the exact source and access log.
- Keep this implementation fix separate from any choice to truncate weights;
  truncation would require a justified, versioned protocol and sensitivity
  analysis.

## Consequences

Weights may exceed 10,000 when the empirical censoring survival is below
`1e-4`, and an unsupported metric calculation will fail instead of returning a
finite score. Existing results produced where the floor was inactive have
unchanged IPCW weights. No historical result is rewritten or silently
reclassified by this source change.

The focused metric tests cover zero Kaplan–Meier survival and a supported
weight above the former cap. This does not close the broader Q-7 data-path,
estimator, or historical-result audit.
