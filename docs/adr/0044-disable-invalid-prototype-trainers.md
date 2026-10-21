# ADR-0044: Disable invalid prototype trainers

## Status

Accepted for Q-7 source-path quarantine. This does not rehabilitate historical
prototype artifacts or replace them with another model.

## Context

ADR-0002 quarantined the original prototype models and their serialized files,
but the repository again contained directly executable trainer scripts. The
organ-susceptibility trainer fit synthetic oracle targets and wrote a pickle
model. The longitudinal trainer used circular `is_anomaly` labels, a
bidirectional model, and a pickle scaler. A deprecation header did not prevent
either path from training or writing artifacts.

## Decision

- Retain the old module paths only to give callers a clear migration error.
- Make both public trainer functions raise before importing training or
  serialization dependencies or writing files.
- Keep all historical outputs and claims governed by ADR-0002 and their
  existing quarantine provenance; do not regenerate or overwrite them.
- Add function-level and module-execution tests proving both entry points fail
  closed without creating artifacts.

## Consequences

The invalid prototype trainers cannot be used accidentally through their
Python APIs or `python -m` entry points. No approved replacement trainer is
introduced by this change. Package B still requires a complete call-path audit
of every historical trainer, evaluator, and serving route.
