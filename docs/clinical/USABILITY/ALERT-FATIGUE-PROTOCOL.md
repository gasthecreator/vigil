# Alert-burden simulation protocol

This protocol describes a synthetic software simulation, not a human alert-fatigue study. Its fixed question, generator, seed, cohort size, input columns, and K2 configuration are preregistered at [`EXP-UF-001`](../../../experiments/EXP-UF-001/PREREG.md).

The original report and machine-readable values are preserved at [`reports/usability/alert-fatigue/REPORT.md`](../../../reports/usability/alert-fatigue/REPORT.md) and [`results.json`](../../../reports/usability/alert-fatigue/results.json). A later source audit found the fixed-seed output no longer matches current generator/K2 behavior; see [`RECONCILIATION.md`](../../../reports/usability/alert-fatigue/RECONCILIATION.md). Do not replay the consumed seed or treat its stored values as current-engine evidence. CI verifies the preserved files and their reconciliation record without regenerating the cohort.

A replacement simulation needs a new preregistration, fresh seed, and committed observed-input artifact/access record before evaluation. Regenerating an output requires a new versioned result path; it must not overwrite this history.

The result counts patient streams with a latched detector alarm. It does not measure the number of alerts seen in a clinic, clinician workload, false alarms against real outcomes, fatigue, usability, or clinical benefit. Do not adjust thresholds based on this simulation. Human-factors work requires the approved moderator script, consent form, ethics and facility approval, and an independently designed protocol.
