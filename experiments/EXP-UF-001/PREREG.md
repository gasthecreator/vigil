# EXP-UF-001 — synthetic alert-burden simulation (pre-registration)

**Status:** pre-registered before result generation. This is a software workload simulation, not a clinical study or human-factors result.

## Question and limits

How often does the existing K2 detector latch at least one alert per generated patient stream in one fixed synthetic world? This measures alert burden only. It cannot estimate clinician fatigue, acceptability, clinical utility, sensitivity, or outcomes.

## Frozen procedure

- Generator: `vigil-sim` `G1_SMOOTH`; seed `1624`.
- Cohort: 250 generated patients; 730 days; nominal 90-day sampling interval.
- Input: observed CA 15-3 values only, using the simulator's observation mask. No latent columns or outcome labels are read.
- Detector: `vigil_ml.k2.SequentialDetector` defaults (`alpha_pt=0.05`, `sigma_log=0.12`, `burn_in=3`).
- Primary descriptive quantity: number and fraction of evaluable patient streams with a latched alert; also report observations processed.
- Reproduction command: `uv run python scripts/run_alert_fatigue_simulation.py`.
- No tuning, subgroup search, or threshold selection is planned. A different generator, seed, model configuration, or workload is a separate preregistration.

## Decision rule

There is no success threshold. Report the computed values with the explicit limit that this one synthetic workload is not a measure of clinician fatigue or patient benefit. Do not change product alert thresholds from this result.
