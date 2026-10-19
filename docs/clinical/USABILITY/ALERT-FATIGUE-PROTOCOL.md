# Alert-burden simulation protocol

This protocol describes a synthetic software simulation, not a human alert-fatigue study. Its fixed question, generator, seed, cohort size, input columns, and K2 configuration are preregistered at [`EXP-UF-001`](../../../experiments/EXP-UF-001/PREREG.md).

Run `uv run python scripts/run_alert_fatigue_simulation.py` to regenerate the script-written report at [`reports/usability/alert-fatigue/REPORT.md`](../../../reports/usability/alert-fatigue/REPORT.md) and machine-readable values at [`results.json`](../../../reports/usability/alert-fatigue/results.json). CI calls the script in verification mode and checks the measured fields against the committed result.

The result counts patient streams with a latched detector alarm. It does not measure the number of alerts seen in a clinic, clinician workload, false alarms against real outcomes, fatigue, usability, or clinical benefit. Do not adjust thresholds based on this simulation. Human-factors work requires the approved moderator script, consent form, ethics and facility approval, and an independently designed protocol.
