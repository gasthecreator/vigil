# ADR-0048: Preserve competing death in partner landmark outcomes

- **Status:** Proposed for Q-7 overseer review
- **Date:** 2026-10-19
- **Decision owners:** Q-7 executor; clinical/statistical lead and owner ratify the protocol before real-data use

## Context

The clinical preregistration specifies cumulative-incidence handling for death without recurrence. The partner landmark builder discarded the extractor's event codes and rebuilt `E` as recurrence versus censoring, so death was treated as censoring. This diverged from both the planned estimand and `vigil_eval`'s supported event code 2.

## Decision

Partner landmarks encode recurrence as event 1, death without prior recurrence as competing event 2, and only administrative/loss-to-follow-up as censoring 0. The fixed 365-day target is recurrence before competing death: recurrence by the horizon is a case, competing death by the horizon is a known control, follow-up reaching the horizon is a known control, and censoring before the horizon is unknown. The end of surveillance and alert exposure is the first of recurrence, competing death, and follow-up.

This implements a fixed-horizon competing-risk outcome for IPCW evaluation. It does not add an all-time cumulative-incidence estimator or establish model validity. Same-day recurrence and death remain invalid because their order is unknown.

## Consequences

The previous synthetic partner report is stale under this corrected outcome contract and must be regenerated before reuse. The preregistration remains draft and unfrozen; no real-data evaluation or frozen test set is accessed by this change. The clinical/statistical lead must review this operationalization at protocol ratification.

## Evidence

- Regression tests cover competing death as a known control and recurrence preceding later competing death.
- Existing IPCW implementation treats event code 2 as a known outcome and only code 0 as censoring.
- Focused partner analysis, evaluator, freeze-gate, and synthetic dry-run checks are required for closure of this source finding.
