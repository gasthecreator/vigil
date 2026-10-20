# ADR-0065: Retire the EXP-M12-001 frozen run

- Status: Accepted
- Date: 2026-10-20

## Context

EXP-M12-001 preregisters a one-time frozen run. Its historical outputs are committed, but the canonical append-only frozen-test access log has no corresponding entry, the run lacks a clean-tree/source-SHA access guard, and its training/evaluation contract predates corrected early-censor semantics. The provenance audit explicitly forbids inferring and backfilling the missing access event. The previous runner guard could be bypassed by removing output files while the access log remained absent.

## Decision

Retire EXP-M12-001's frozen run. Preserve its historical files without treating its claims as current selection evidence. The runner requires the committed `FROZEN-RUN-DISPOSITION.json` and always refuses frozen execution when the study is retired; missing, malformed, or unrecognized disposition fails closed. Any replacement must have a new experiment ID, preregistration, seeds, pre-access canonical logging, and censoring-aware training and evaluation.

## Consequences

The old frozen seeds cannot be replayed through this runner, including after output deletion. This does not establish exactly when historical test access happened, repair the old result, or replace the required new study. The old access event remains unrecorded rather than fabricated.
