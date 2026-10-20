# EXP-K4-001 frozen seed disposition

The committed `results.json`, `REPORT.md`, and `CONCLUSION.md` record one frozen run over replications 0–9, base seed 20261201, with source hash `8af5136e5e3339ea`. Preserve these artifacts; do not rerun, regenerate, or overwrite them. Any new K4 evaluation needs a new preregistration and fresh seeds in a new experiment directory.

The canonical `data/audit/frozen_test_access.jsonl` has no EXP-K4-001 entry. The saved report and conclusion establish that the run occurred, but the missing access-log row means its historical access record is incomplete; this file does not invent a Git SHA or backfill an unverified access event.

The historical runner's `--smoke` mode also used the frozen base-seed namespace. Whether that mode was invoked before the guard was added is not established by the committed evidence. The current runner assigns smoke replications after the configured development seed range and uses a separate derived bootstrap seed. No smoke or frozen cohort was run while applying this correction.

Current K4 input-contract validation, target-contract propagation, and runner safeguards differ from the frozen source hash: the stored hash is `8af5136e5e3339ea`, while the current concatenated `k4.py` + runner SHA-256 is `f6ad16d694a26fc2` (first 16 hex characters). The historical result remains attached to its recorded hash and is not represented as regenerated from the current source.
