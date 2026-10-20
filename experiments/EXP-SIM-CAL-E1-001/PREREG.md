# EXP-SIM-CAL-E1-001: Source-aligned synthetic CA 15-3 comparison

## Status and registration boundary

This protocol is committed before implementation of its evaluator/runner and before any cohort is generated or inspected for this study. The implementation, tests, configuration, and runner will be committed and frozen before the first run. The run is single-use: any integrity or execution failure is retained, and a correction requires a new experiment ID, protocol commit, and fresh seeds. The only input data are generated synthetic cohorts. This is not patient-level or clinical calibration.

The study operationalizes the owner-approved disposition in ADR-0063. It does not tune simulator parameters, select a model, alter earlier cohorts, or change the historical evaluator. `ACCESS_LOG.json` will record the preregistration commit/hash, implementation commit and source hashes, Python/dependency versions, exact seeds and cohort names, and first-access timestamp before cohort generation.

## Question and target quantities

Under the explicit `balanced_synthetic_core_v4` assumptions, what are the seed-level and across-seed estimates for the source-comparable, observed-diagnosis CA 15-3 quantities below? All estimates are conditional on the simulator's event, visit, measurement, verification, and competing-event mechanisms.

1. **Pre-diagnosis detection fraction among monitored diagnosed cases:** numerator is an observed CA 15-3 value strictly above the source cutoff on a visit strictly before observed diagnosis; denominator is a diagnosed recurrent patient with at least one finite, observed CA 15-3 measurement strictly before diagnosis. Also report coverage and the same numerator over all observed diagnosed recurrent patients.
2. **Conditional lead time:** for detected monitored cases, observed diagnosis day minus the earliest strictly pre-diagnosis measured value above cutoff. Report days and months, where one month is `365.2425/12` days. Report arithmetic mean and sample standard deviation. E1's abstract reports `4.2 ± 2.3` months but does not define the dispersion statistic there, so compare the means descriptively and present the simulator SD separately; do not treat the two dispersion terms as equivalent.
3. **Observed-NED patient specificity:** among patients with no observed diagnosis, no competing event, and no loss to follow-up before administrative follow-up ends, and with at least one finite observed CA 15-3 value, a patient is negative only if every such measured value is at or below cutoff. Report the fraction and all numerator/denominator counts. This is an observed-status estimand and can include undiagnosed latent recurrence.
4. **Oracle recurrence-free specificity sensitivity analysis:** repeat quantity 3 after additionally restricting to patients with no latent recurrence. This is synthetic-oracle-only and is not source-comparable.
5. **E1 distant-recurrence sensitivity:** report `not_estimable` for the present G1/G2/G3 site mechanism because it contains no locoregional recurrence class and cannot reconstruct the source's excluded-locoregional denominator. Do not label all generated recurrence sites as evidence that this source statistic was reproduced.

The source values are 37/91 (41%) elevated before diagnosis among monitored CA 15-3 recurrence cases, a reported lead-time summary of 4.2 ± 2.3 months, 54% CA 15-3 sensitivity after excluding locoregional recurrences, and 99% specificity among 444 NED patients. The abstract does not define the dispersion convention for ± 2.3, so this study will not treat it as a published SD. These are context values from E1, not simulator acceptance thresholds. The study reports synthetic estimates beside source values without inference that their populations or measurement processes are exchangeable.

## Data-generating assumptions and fixed design

- Population profile: `packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json`, profile ID `balanced_synthetic_core_v4`, SHA-256 `d4e29b2b4bb5b51a04487b73c38dd3b48b4ac2d161bfaa2dc28757693210aa57`. Load the checked-in JSON explicitly and pass it to each generator; do not use implicit legacy defaults.
- Generators: G1 smooth kinetics, G2 burst shedding, and G3 heavy-tailed assay noise. They are three synthetic stress mechanisms, not estimates of real clinical populations.
- Replicates: 30 independent cohorts per generator, 1,023 patients per cohort, 2,263 administrative follow-up days (365.0 × 6.2), with schedule and observation/missingness settings read from the frozen profile. The cohort size mirrors E1's reported total enrollment and the duration approximates its reported 6.2-year mean; this does not recreate the source's varying follow-up or its 533-patient CA-tested subset.
- Seeds: `base_seed = 514000 + generator_offset + replicate`, with offsets G1=100, G2=200, G3=300 and replicate indices 0–29. No seed overlaps EXP-CORE-ML-001..013, EXP-K1-001..004, or the E1 legacy calibration fixtures. Before implementation, verify this namespace against every committed seed/access inventory; if any collision exists, amend this protocol before generating data.
- No pre-test tuning, exclusion changes, threshold selection, or generator-parameter adjustment is permitted. No cohort may be inspected before the implementation commit and access log are frozen.

## Endpoint definitions and unit handling

- Source cutoff: greater than 60 `U/mL`, taken from the E1 excerpt in `docs/evidence/E1.md`. Convert the cutoff with `vigil_core.units.convert_units` using analyte code `ca_15_3` to the registry's canonical unit. Do not duplicate a conversion factor in implementation code.
- A measured value is usable only when `observed_mask["ca_15_3"]` is true and the value is finite. A latent numeric value behind a false mask is never used.
- Case event time and site use `observed_recurrence_day` and `observed_recurrence_site`, not latent recurrence time/site. Diagnosis-day measurements are excluded (`observation.day < observed_recurrence_day`).
- A patient's first measured pre-diagnosis elevation determines lead time; repeated elevated values do not create additional cases.
- A control must remain under observed NED status through administrative follow-up and have no competing event or loss-to-follow-up event before the end. The exact simulator censoring fields and boundary behavior must be validated in tests before running.
- Count diagnosed cases with zero measured pre-diagnosis observations as not monitored, not as marker-negative. A case with pre-diagnosis observations but no value above cutoff is monitored and undetected.
- The E1 sensitivity statistic excluding locoregional recurrence is not computed for current profiles; its output is explicitly `not_estimable` with a reason.

## Uncertainty and reporting

- Preserve all 30 replicate rows per generator, including zero-denominator, undefined, and failed metrics; never replace undefined values with zero.
- Primary aggregation is the unweighted arithmetic mean of defined replicate estimates. For detection, lead time, and specificity, give a 95% percentile interval from 10,000 bootstrap resamples of the 30 independent replicate indices, resampling whole replicates with replacement. Use one fixed bootstrap seed `514999`, recorded in the access log. Replicates, not patients, are the independent resampling units for across-seed variation.
- Report the numerator, denominator, coverage, mean, SD, and all per-seed values. If fewer than 24 of 30 replicates define a metric, aggregate interval is `not_estimable`; do not discard failed replicates or replace them.
- Compare the simulated mean/SD descriptively with E1's published point summaries only for the supported endpoints. No null hypothesis, equivalence margin, acceptance range, or simulator retuning is registered.
- The report must state that E1 discouraged routine marker surveillance per the guideline evidence in E1 and that marker elevation is not diagnosis or clinical benefit.

## Integrity, tests, and stopping rules

Before generation, tests must establish: unit conversion returns the expected canonical representation using the library conversion; false-mask values do not affect any endpoint; same-day and post-diagnosis values do not count; missing observation rows reduce coverage without creating a negative case; observed diagnosis is not replaced by latent onset; competing events and loss to follow-up do not enter the NED denominator; zero denominators remain undefined; recurrence sites cannot silently satisfy the absent locoregional exclusion; and identical input cohorts reproduce identical JSON.

The study runner must reject duplicate patient IDs, invalid/contradictory observed diagnosis fields, non-finite or negative observation days, observations beyond the cohort horizon, and mismatched profile/hash/seed metadata. It must refuse existing results or access records for this experiment ID. The renderer must derive all displayed quantities from saved JSON, and a parity test must reproduce the report bytes. Run the complete evaluator/runner contract test suite and existing simulator regression suite before any cohort generation.

If a preregistered integrity check fails, abort before generating or inspecting a study cohort, record the deviation, and do not edit the protocol in place. If a runtime/result failure occurs after generation, preserve the partial data/access records, do not rerun seeds, and register a new experiment with fresh seeds.

## Limits

All inputs and results are synthetic and inherit the uncalibrated v4 assumptions. The design's fixed cohort size and follow-up differ from E1's monitored subset and varying follow-up. Observed-NED specificity may contain latent undiagnosed cases. The current site generator cannot reproduce E1's locoregional exclusion. No result establishes real-world calibration, diagnostic performance, clinical utility, benefit, or an appropriate clinical cutoff.
