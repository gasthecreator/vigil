# Proposal: define censor-aware partner lead-time and over-detection

## Finding

`scripts/partner_analysis.py::secondary` previously passed partner outcomes to `vigil_eval.lead_time.evaluate_lead_time_and_overdetection` after dropping right-censoring and competing-death information. `to_vigil_frames` sets `observed_recurrence_event` false when no confirmed event is recorded by the available follow-up, and the adapter supplied `is_indolent=False` for every patient. The legacy evaluator interprets every such patient as definitively disease-free, counts their alerts as overdetection, and measures person-time only between observed laboratory draws. Its signature has no censoring horizon, follow-up time, competing event, or verification state.

The partner target contract in `docs/clinical/ANALYSIS-SPEC.md` distinguishes recurrence, competing death, and administrative/loss censoring; it labels follow-up before 365 days unknown. The lead-time adapter discarded those distinctions, so the secondary number did not share the primary analysis' observable-outcome contract. This is a source-to-estimand defect, not evidence that the result is clinically biased by a known amount.

## Conservative disposition

The partner analysis now emits `lead_time.not_computed` with the missing estimand stated explicitly. It does not pass censored outcomes through the legacy evaluator or assume an indolence label. The analysis specification describes this behavior. The generic legacy evaluator remains available for its existing fully observed synthetic fixtures and now rejects missing/invalid recurrence and indolence labels, inconsistent recurrence dates, malformed alerts/times, and observations for unknown patients. Those contract tests do not make the evaluator censor-aware or validate partner-data lead time.

## Required protocol before re-enabling

Register the target population, index time, alert episode definition, event and competing-death treatment, censoring/verification assumptions, disease-free follow-up requirement or IPCW method, estimand horizon, alert-burden denominator, patient-level uncertainty method, and minimum evaluable counts. The implementation must receive and validate those inputs, report exclusions/undefined components, and have tests that show early censoring and competing death cannot be counted as confirmed disease-free. Do not regenerate prior partner reports as performance evidence or claim lead time until the clinical/statistical review and preregistration are complete.

## Scope and evidence

This finding is in Q-7 packages B and G. It changes only the partner secondary-output behavior; it does not change the primary fixed-horizon outcome, model fitting, frozen test sets, or the generic synthetic lead-time evaluator. No partner result was reopened for this audit. A synthetic dry-run is used only to verify that the output reports the explicit unavailable status and is not performance evidence.
