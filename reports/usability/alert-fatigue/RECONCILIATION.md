# EXP-UF-001 historical output reconciliation

**Status: historical; not current evidence.** This fixed-seed synthetic report is preserved unchanged. A later read-only source audit found that the current generator and K2 implementation no longer reproduce its recorded values. The exact source change responsible for the drift has not been isolated, so the old result is not attributed to the current engine and must not guide model or alert-policy selection.

The source audit recorded current-source output for the same requested workload as 246 observed streams, 44 latched alerts, fraction `0.1788618`, and 979 observations, compared with the preserved `250`, `80`, `0.32`, and `1184`. These are synthetic software outputs, not clinical or human-factors evidence. The audit and full producer crosswalk are in [`CORE-ML-ENTRYPOINT-CROSSWALK-2026-10.md`](../../../docs/audits/CORE-ML-ENTRYPOINT-CROSSWALK-2026-10.md) and [`CORE-ML-REPAIR-PLAN-2026-10.md`](../../../docs/audits/CORE-ML-REPAIR-PLAN-2026-10.md).

The files below are preserved verbatim. CI checks their hashes and that the report agrees with the stored JSON; it does not replay seed `1624` or claim the old values reproduce from current source.

- `results.json` SHA-256: `ef512ef3e05fc379fde246d34ede658349d32b3998f3a75ffec577333f009842`
- `REPORT.md` SHA-256: `9298c817723a56caa68259cc264bcf90ac87771ba2a3fecf489af25f292e2473`

A replacement workload requires a new preregistration, a fresh seed, and a committed observed-input artifact/access record before evaluation. Do not overwrite this historical result.
