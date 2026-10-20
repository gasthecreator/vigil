# ADR-0046: Require a ratified threshold grid for partner DCA

- **Status:** Proposed for Q-7 overseer review
- **Date:** 2026-10-19
- **Decision owners:** Q-7 executor; clinical lead and owner must ratify the grid before real-data use

## Context

The partner analysis called `survival_decision_curve_analysis` without thresholds, which activated the evaluator's compatibility grid of 50 values from 0.01 to 0.50. Neither the clinical preregistration nor analysis specification selected or ratified that grid. Decision-curve results therefore encoded an unreviewed clinical trade-off range.

## Decision

The partner analysis emits no decision-curve numbers unless the frozen preregistration supplies PR-10 as a JSON array of finite, strictly increasing probabilities in `(0, 1)`. The freeze gate validates the grid. Synthetic dry runs without a frozen protocol report DCA as `not_run`; they never use the evaluator default. The compatibility default remains available to isolated callers, but no partner evaluation path may invoke it implicitly.

## Consequences and limits

Real partner analysis remains blocked until the clinical lead and owner ratify PR-10 and the preregistration is frozen. This does not make DCA clinically valid, establish net-benefit utility, or resolve the separate competing-risk specification gap. The decision is reversible by a new preregistered protocol amendment before test access.

## Evidence

- Freeze-gate tests reject missing, empty, unordered, duplicate, nonnumeric, and out-of-range PR-10 grids.
- Partner-analysis tests verify no-grid abstention and exact use of explicit thresholds.
- The synthetic partner dry-run is regenerated with DCA marked `not_run` because there is no ratified grid.
