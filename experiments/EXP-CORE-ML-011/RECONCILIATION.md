# EXP-CORE-ML-011 result-scope reconciliation

**Status: preserved partial mechanism evidence; do not expand its claims.** The original preregistration, result, report, and access log remain unchanged. This audit is based on their committed contents and source review; it did not replay the registered seeds.

The access log binds the run to profile SHA-256 `dd38047b067943ee201cfe426e7438df3678442cf9dd46e9defe1ead5df8e143`; the current file at the same `synthetic_population_core_v4.json` path hashes to `d4e29b2b4bb5b51a04487b73c38dd3b48b4ac2d161bfaa2dc28757693210aa57`. The current profile adds explicit facility mode, baseline-analyte sampling, verification provenance/result semantics, symptom mechanics, and cohort scheduling. The run remains bound to its logged profile bytes; it is not evidence for the current full profile. No attempt was made to infer that the profile-only changes preserve all registered cohort outputs.

## What the stored result establishes

- The standalone `propagate_first_order_secretion` transition agrees with the runner's independent RK4 calculation for 1,000 registered constant-burden cases.
- Existing v4 generator tests check G1/G2 visit-density invariance and recurrence-free behavior.
- The G2 cohort run recorded event counts and a conditional uniform-event-time diagnostic; the stored report records the resulting statistics.

## What it does not establish

- The RK4 comparison in `run.py::validate_g1_transitions` calls `propagate_first_order_secretion`. Production G1 instead calls `evaluate_first_order_on_fixed_grid` from `simulate_longitudinal_trajectory`. The registered maximum-error statistic therefore does not directly measure the production fixed-grid integration against an independent solver.
- The runner does not calculate a G1 recurrence count or eligible person-time. G1 rows in the report's replicate table display zero in the G2-only `events` and `eligible_person_days` fields because those accumulators are updated only for G2. Those zeros are not G1 recurrence counts or evidence that no G1 recurrences occurred.
- The stored run does not summarize the registered G2 amplitude distribution or validate the production marker trajectory's configured clearance against an independent reference. The unit test for `shot_noise_at_times` checks a hand-constructed analytical example, not the full G2 generator path.
- The study is mechanism evidence only. It does not calibrate v4 parameters to people, validate population realism, evaluate a predictive model, or make EXP-CORE-ML-008 results applicable to v4.

EXP-CORE-ML-012 was invalidated after test-seed overlap, as recorded in its DEVIATION.md. EXP-CORE-ML-013 ran on fresh seeds and covers the identified production call-path and distribution-diagnostic gaps at the limited synthetic-mechanism level. EXP-CORE-ML-011 remains an immutable partial result, not a failed rerun and not complete evidence for all its registered questions.
