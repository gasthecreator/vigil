# Pre-registration: EXP-K1-004 — Canonical K1 inference and simulator transfer

- **Status:** registered before implementation fitting or new K1 evaluation in this repair.
- **Owner:** Vigil maintainers; independent acceptance verdict remains overseer-owned.
- **Protocol version:** 1.0
- **Code baseline:** `2499752d392f0cf5bc9a40a10a840ed24dfe1477` (audit/design baseline only; no results from this protocol have been generated).
- **Target:** one canonical `vigil_ml.k1` implementation, including all inference routes and any model-facing prediction API.
- **Purpose:** repair route identity and inference behavior, establish whether the four-parameter model is identifiable and calibrated under its declared generative assumptions, and test transfer to the project's observed-data simulator without promoting K1.

## Questions and estimands

1. **Implementation identity:** do package-level and module-level public K1 imports resolve to the same implementation, and do compatibility imports preserve names without exposing a second model?
2. **Own-world parameter inference:** for data generated from the exact versioned K1 likelihood and prior used by inference, what are parameter recovery, nominal interval coverage, simulation-based calibration (SBC), posterior predictive fit, identifiability and route agreement? This is algorithmic conformance only; it is not evidence of product-world or clinical performance.
3. **Product-simulator transfer:** using measured numeric CA 15-3 values and their observation mask only to identify measured rows, how do frozen K1 posterior-derived quantities compare with B4 and the last-observed-marker comparator on held-out synthetic patients under G1/G2 development and G3 transfer, accounting for event time, censoring and competing events? This remains synthetic evidence.
4. **Operational behavior:** do routes handle irregular visits, missing analytes, no observations, numerical degeneracy, deterministic seeds, and runtime budgets without silently fabricating measurements or risk values?

## Frozen implementation contract

- Keep the overseer-authored `docs/ml/K1-CONTRACT.md` and `tests/acceptance_k1/` unchanged. Run both acceptance modes only against the final candidate SHA and record the outputs once; do not tune to individual acceptance cases or rerun them as a development loop. A failure is recorded as failure or registered stub, not repaired by weakening the contract.
- `vigil_ml.k1` is the sole required API surface. Any legacy import is either a thin, documented compatibility shim to that implementation or is removed from active package exports and consumers. Do not retain a second class with K1 identity.
- Before any K1 fitting/inference, define a versioned configuration for parameter units/support, observation likelihood, analyte units and transformations, measurement noise, visit process, treatment effects, missingness, censoring, recurrence and competing-event semantics. Each value must be generated from the simulator contract, sourced evidence, or explicitly labelled synthetic assumption. No unsupported physiological claim, hidden default, label-trained risk head, or post-hoc score transform is allowed.
- If recurrence event-time and competing-risk semantics cannot be represented and validated by the available simulator, K1 remains parameter-inference research code and exposes no recurrence-risk probability. Do not substitute a heuristic score.
- Training, normalization, feature selection and calibration may use training/development data only. Patient IDs are assigned to splits before landmarks or observations are materialized. No row from a patient crosses splits.
- Do not read historical/retracted EXP-K1-001..003 outputs as tuning feedback. Preserve their files and conclusions as retracted.

## Data and split plan

- **Own-world development:** independently seeded simulations from the declared K1 generative model, generated from registered priors. Use separate training and validation seeds; training sizes are fixed in the committed config before fitting. Do not use acceptance-test seeds for training, model selection or calibration.
- **Own-world final checks:** independent seeds and parameter draws not used for training or model selection. Report parameter-wise bias, RMSE, rank histograms/SBC, nominal 50/80/90/95% interval coverage and width, posterior predictive checks, identifiability spectrum, route agreement and failure/abstention rate. Use at least three independent seeds/settings, including sparse and irregular observation schedules and a declared misspecified setting.
- **Product-world development/transfer:** use `vigil-sim` G1/G2 only for development and G3 only for the final transfer evaluation. Split by patient before preprocessing; freeze cohort generation seeds, exclusions, landmark, outcome horizon, comparator definitions and code/config hashes in a machine-readable config before cohort generation. Use only observed `ca_15_3` values for measured visits; never use `observed_ca_15_3` as a value. Use truth event time for the synthetic estimand and observed follow-up for censoring/competing-event handling; exclude or account for patients according to the registered estimator, not by recoding unknown outcomes as negatives.
- Any prior evaluation-cohort access inherited from the historical acceptance runs is treated as exposed. Those cohorts and seeds are not development data. This protocol's product-world evaluation uses newly registered seeds. The fixed acceptance contract's G1 seed-5 cohort is run once at the final candidate SHA and reported separately as a contract gate, never used for tuning.

## Methods and comparisons

- Compare each genuinely implemented route (`amortized`, sequential filter, NUTS reference, and NPE/SBI) under the same declared prior and likelihood. Route labels must describe the actual algorithm. If a route cannot be implemented faithfully or within the registered budget, list the exact `K1-ROUTE:<name>` token in `docs/STUBS.md` and report its gate as NOT MET; do not alias another route.
- Assess numerical correctness on analytic/small cases where available; route-specific diagnostics include optimizer convergence, NUTS R-hat/ESS/divergences, particle effective sample size/resampling/degeneracy, and SBI simulation budget and posterior checks.
- For product-world transfer, compare K1 only to the registered B4 and last-observed-marker baseline on the same eligible patients and horizon. Report time-dependent AUC, IPCW Brier score, calibration, precision-recall, decision/alert burden at a development-selected operating point, abstention and runtime. No test-set threshold or model selection.
- Use patient-level bootstrap with 1,000 replicates for transfer metric intervals, preserving split and censoring structure. Report all registered metrics and negative results. Where a metric's assumptions fail (e.g. positivity for IPCW), report it as not estimable with diagnostics; do not silently replace it.
- Report robustness across at least three registered settings: visit sparsity/irregularity, observation or lab-site shift, and treatment/missingness/censoring shift. Separate correctly specified own-world inference from product-world misspecification.

## Decision rules

- No numeric performance threshold will be invented or tuned after results. Apply the immutable acceptance thresholds as contract gates only. For scientific interpretation, compare estimates and uncertainty intervals with the registered baselines, check calibration and posterior validity, and require that all high-impact assumptions and robustness failures are disclosed.
- Passing own-world recovery/SBC does not establish product-world usefulness. Passing the product-world acceptance gate alone does not establish calibrated risk or clinical utility.
- Retain K1 as a parameter-inference research method only if posterior recovery, calibration and numerical diagnostics are supported in the declared worlds. Retain a recurrence-risk output only if the simulator supports a coherent event-time likelihood, censoring/competing-event evaluation, held-out calibration and decision analysis. Otherwise remove/disable risk output and record the reason.
- No synthetic result supports real-patient use, diagnosis, reassurance or clinical validation. K1 remains research-only regardless of this study's outcome.

## Provenance, access log and deviations

- Commit this preregistration and its config before any fit or result-producing K1 test. Each run records repository SHA, dirty-tree status, config hash, environment lock hash, simulator version, seeds, split IDs/hashes, command, start/end time, outputs and access event.
- Frozen product-world test cohorts are generated and read once after the implementation and development decisions are frozen. Record that access in the report. Any accidental access, protocol change, or code change after access invalidates the affected confirmatory result; preserve it and create a new experiment ID/protocol before a new cohort is generated.
- No deviations are currently registered. Amendments must be timestamped and committed before the affected data or result is accessed; explain the reason and preserve the prior protocol text.

## Known limits

The simulator is synthetic and may omit relevant clinical biology and care processes. Evidence sources do not establish the proposed K1 kinetic parameters, marker kinetics, assay noise, treatment response, or recurrence mechanism as clinically transportable. No patient data, clinical approval, external validation cohort or independent clinical reviewer is available within this experiment. No deployment, model promotion or clinical claim can result from this work.
