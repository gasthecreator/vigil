# EXP-CORE-ML-012: v4 simulator call-path mechanism verification

## Status and boundary

This preregistration is committed before implementation changes, new mechanism test code, or result access. The study uses synthetic inputs only and does not select model parameters, calibrate to patient data, evaluate predictive performance, or establish clinical validity. It addresses limits found in the preserved partial EXP-CORE-ML-011 evidence; that study's seeds, outputs, report, and access log will not be reused or changed.

## Questions

1. Does the production `balanced_synthetic_core_v4` G1 path use its configured secretion and clearance coefficients and produce the registered fixed-grid integration values within a prespecified numerical error against an independently coded solver?
2. Does the production G2 path use configured Poisson event rate, positive lognormal amplitudes parameterized by the configured arithmetic mean and coefficient of variation, and the configured exponential clearance kernel?
3. Do the production G1/G2 paths preserve common-time values when measurement visits are added, emit no recurrence-linked signal/events for recurrence-free controls, and keep event traces/latent truth out of model-visible observations and labels?

These are software-mechanism estimands under one synthetic profile. They are not biological parameter estimates or evidence that the profile matches any population.

## Frozen configuration and implementation boundary

- Profile: `packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json`, profile id `balanced_synthetic_core_v4`, SHA-256 `d4e29b2b4bb5b51a04487b73c38dd3b48b4ac2d161bfaa2dc28757693210aa57`.
- Pre-implementation source commit: `d8a362821529e329919430696831cc59382f1c92`. Frozen input hashes at this commit: `packages/vigil-sim/vigil_sim/generators.py` `2775a881468cb3744ca103764ca2b6667342ae4974ef505fdfd7a7132121a544`; `packages/vigil-sim/vigil_sim/mechanisms.py` `d7d519e146fb720a31051122443d938889529c6c25159d966b1ec700b031ac21`; `packages/vigil-sim/pyproject.toml` `741fae49b9445d1c2d36075ee0fb06196be7f309e91ea4e42939d642b6a10dbd`; repository `uv.lock` `2337234d520c965c2b3c867a3978c4fbac75751de1a4231f42403c6f35f59e6e`.
- Initial environment: Python `3.12.15`, NumPy `2.5.4`, SciPy `1.18.1`; the locked dependency file is the authoritative complete environment specification. The implementation commit's source hashes and exact runtime versions must also be written to `ACCESS_LOG.json` before the first result-producing command. If the profile changes after this protocol is committed but before output access, amend this protocol and commit the amendment first.
- All rate, clearance, burden, amplitude, step-size, and integration settings are read from the profile. No duplicate numeric parameter is added to the runner or test fixtures except analytically defined mathematical constants.
- The implementation may factor profile-driven G1 and G2 operations into callable internal mechanisms to make the actual generator path testable. The generator and study runner must call the same mechanism implementation. Any event-time or amplitude trace used for diagnostics remains internal and must not enter patient observations, features, labels, API payloads, or model artifacts.

## Design and randomization

- Use five independent synthetic replicates, 1,000 generated patients per G1/G2/G3 per replicate, and the registered 730-day follow-up. Retain each replicate separately and report all exclusions and eligible person-time. G3 is included only as a comparison/contract control; no G3 mechanism or performance claim is estimated.
- Base seed: `20261201`; generator stream offsets: G1 `310000`, G2 `420000`, G3 `530000`; each cohort seed is base plus its generator offset plus `20000 * replicate_index` (zero-based replicate index). Patient-level G2 streams are derived from that cohort seed, stable patient ID, and the two registered stream names. The runner must reject dirty worktrees and any pre-existing access/result/report artifacts.
- G1 analytic tests use deterministic piecewise-constant and smooth burden functions drawn from fixed equations in the test code. They do not read or tune against any cohort result. For production integration path tests, the exact G1 helper called by `simulate_longitudinal_trajectory` is wrapped to capture its burden function and profile arguments. An independent RK4 solver samples that same burden at the configured grid's left edges, uses the configured zero-order-hold interval, and subdivides each interval into 16 equal solver steps; it starts at zero state and integrates each analyte with its own configured secretion/clearance pair. Production and RK4 values are compared at the exact observation days. The solver subdivision is a numerical method setting, not a simulator parameter.
- G2 distributional diagnostics are generated from the v4 production event and amplitude mechanisms on the new patient-scoped streams. The report records event-count mean/variance by replicate, exact two-sided Poisson probability-ordering p-value against configured rate times eligible recurrence person-time, conditional normalized event-time uniform KS statistic/p-value, and amplitude mean/CV plus a KS diagnostic after standardization by the preregistered lognormal parameters. For each replicate, Holm correction is applied across its three registered distribution checks at family-wise alpha `0.01`. The same pure trace-draw helper is used by production and the runner; the runner regenerates each trace deterministically from cohort seed, patient ID, and the registered stream names after cohort generation, then verifies trace counts against the production latent event-count field. Traces remain absent from cohort and model-visible exports.
- A direct analytical clearance fixture verifies that the production G2 marker-state function equals the sum of prior event amplitudes times their configured exponential-clearance kernels. A path-wiring regression proves that `simulate_longitudinal_trajectory` uses the tested mechanism and profile values; it does not expose diagnostic traces in public outputs.
- Tests assert shared observation times agree to absolute tolerance `1e-10` when additional visits are inserted. Numerical solver comparison tolerance is maximum absolute error `1e-6` marker units. Distribution diagnostics use alpha `0.01`, with Holm correction across the three registered distribution checks (Poisson count, conditional event-time uniformity, standardized amplitudes). No threshold is altered after access.
- Recurrence-free controls must have zero recurrence-linked G1 burden/marker signal and zero G2 events/marker signal. Every reported value must be finite and nonnegative where required. Feature/label contract checks must establish that mechanism traces and future latent truth are not model-visible.

## Analysis, failure, and reporting

- Report G1 recurrence counts and G2 event counts as distinct fields. Do not use a default zero for a metric that was not computed; report `null`/`not_applicable` with a reason instead.
- Preserve per-replicate results and all diagnostics, including failures. Do not tune coefficients, integration step, event rate, thresholds, or tests against these draws. A failed result is preserved; any correction requiring new result access receives a new experiment ID and fresh seeds.
- Generate `results.json` and render `REPORT.md` from the saved JSON. Verify byte-for-byte report parity and record source, preregistration, profile, simulator, runner, lockfile, Python, NumPy, and SciPy digests/versions in the access log.
- The run can support only a conclusion about implementation fidelity of the tested synthetic mechanisms. It cannot close simulator calibration, verification-bias validity, population realism, or model-performance questions. Any downstream model study on v4 requires its own preregistration and fresh cohorts.

## Execution order

1. Commit this preregistration before mechanism or runner changes.
2. Implement the registered testable internal mechanism boundary, tests, and result runner; commit them before accessing study outputs.
3. Run once from a clean implementation commit, preserving any failure output and log. Verify report parity and hashes, then commit the result artifacts.
