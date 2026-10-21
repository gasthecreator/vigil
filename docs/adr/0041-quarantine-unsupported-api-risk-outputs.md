# ADR-0041: Quarantine unsupported API risk outputs

## Status

Accepted for the Q-7 API repair. This is a safety and serving decision, not
evidence that another model is valid.

## Context

The legacy `VigilEngine` emitted recurrence-risk scores from fixed lab
thresholds, substituted constants for absent measurements, and generated
clinical follow-up prose despite being marked quarantined. Patient APIs stored
and served those values, the demo seeder created additional risk rows, and the
triage queue mixed those outputs with task state using fixed weights. The M1
organ prior also depended on E12 numerical claims that were retracted.

## Decision

- Make the two legacy inference methods fail closed until an approved model
  satisfies its registered runtime contract.
- Continue recording supplied laboratory values and running the separate
  observation adjudication pipeline, but create no legacy `RiskInference`
  rows.
- Return explicit unavailable or abstained states, with null score, interval,
  and triage fields. Never substitute zero for an unavailable estimate.
- Keep historical rows for auditability, hide them from active risk displays,
  and continue treating historical high/triage rows as a conservative
  bad-news disclosure hold.
- Order the patient queue from stored active follow-up task escalation and due
  dates. Do not synthesize a composite risk or urgency score.
- Store baseline pathology without the unsupported M1 organ prior. Make its
  database column nullable without deleting existing historical values, and do
  not expose old vector values through these API responses.
- Make cohort risk aggregates unavailable and prevent synthetic demo seeding
  from generating legacy risk rows.

## Consequences

The API can record and route observations while recurrence-risk predictions
abstain. Clients must accept nullable risk fields and distinguish unavailable
from zero. This does not validate M3/K2, close other K1/K3/M1 findings, or make
synthetic data clinical evidence. The repair requires full route, migration,
acceptance, and repository CI verification before Q-7 can close.
