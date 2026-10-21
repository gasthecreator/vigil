# ADR-0061: Preserve undefined evaluation metrics as undefined

## Status

Accepted.

## Context

Several evaluator outputs substituted chance-level values, fixed confidence intervals, or zeroes when the requested metric was missing or could not be estimated. Those values looked like observed results and could influence model comparisons or review decisions.

## Decision

- Missing/non-finite candidate or baseline metrics make the regression gate fail with an explicit undefined-comparison reason.
- Benchmark tables render unavailable numeric fields as `N/A` rather than zero.
- Subgroup bootstrap results with missing/non-finite estimates remain NaN and are excluded from empirical-Bayes fitting; no synthetic point estimate or interval is inserted.
- Subgroup interval shifting is not clipped to a generic `[0, 1]` range because the API accepts metrics with other domains.
- Verification-weighted AUC remains undefined when its weighted pair denominator is zero.
- Lead-time summaries without qualifying recurrence/alert observations remain NaN, and single-case conditional standard deviation is undefined. Surveillance patient-time uses observed follow-up span instead of an artificial 30-day minimum.

## Consequences

Incomplete evaluations can no longer appear numerically complete. Consumers must handle NaN/N/A and supply complete metrics before a regression comparison can pass. This does not resolve the validity of the estimands or empirical-Bayes interval approximation.
