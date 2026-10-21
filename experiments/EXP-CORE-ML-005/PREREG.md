# EXP-CORE-ML-005 preregistration: synthetic observation-process calibration

## Status and scope

This preregistration is committed before its runner or any generated result. The study audits the mechanics of `balanced_synthetic_k3_v2`; it is not a model-performance, clinical, prevalence, or verification-bias-correction study. No model will be fitted, no threshold selected, and no frozen model test cohort accessed. All cohorts and results are synthetic.

## Questions

1. Do observed imaging frequencies track the configured per-visit imaging propensities across propensity strata and G1/G2/G3 generators?
2. Among performed imaging observations, do positive-result frequencies track the configured sensitivity for visible recurrence and false-positive rate for non-visible recurrence / no recurrence?
3. Do observed assay-missingness frequencies track their registered assumptions by generator and, for G1 high-cost assays, out-of-pocket delay factor?
4. Are shared facility-analyte offsets and scales identical within facility and distinct across facilities as specified?

The target is generator implementation behavior under the exact committed synthetic configuration. The imaging estimand is per performed examination conditional on visible recurrence, defined from the configured burden threshold, versus not-visible/no recurrence. The verification estimand is per observation, not patient-level eventual diagnosis. Missingness estimates are per analyte observation. These are not estimates of real clinical test characteristics.

## Design

- Profile: `packages/vigil-sim/vigil_sim/config/synthetic_population_k3_v2.json`, frozen by SHA-256 in the result manifest.
- Generators: G1 smooth, G2 burst, G3 heavy-tailed.
- Replicates: five independent seeds per generator; 2,000 patients per cell; 730 simulated days. Seed is `910000 + 10000 * generator_index + replicate_index`, with generator indices G1=0, G2=1, G3=2 and replicate indices 0–4.
- The runner must log the clean implementation commit, profile hash, seed, generated cohort counts, and source hash. It must refuse dirty trees and existing result/access artifacts. It may only run after this preregistration and runner are committed.
- For each generated observation, retain the declared imaging propensity, whether imaging occurred, its result when performed, latent burden/recurrence state for the diagnostic audit, assay observed masks, facility ID, and relevant patient missingness factor. No model-facing feature matrix or prediction is produced.

## Analysis

- Report denominators and observed rates alongside configuration-implied probabilities by equal-frequency per-generator/per-replicate propensity decile, generator, assay, and result stratum. For ties, use deterministic rank ordering by original observation order.
- Report binomial 95% Wilson intervals for imaging and performed-test result proportions. Report absolute deviations from each known generator parameter; do not collapse across generators to conceal a failure.
- For G1 high-cost assays, report missingness by equal-frequency per-replicate out-of-pocket-factor quintile and compare each bin with the registered probability function. For other generator/analyte cells, compare missingness with the registered generator-specific MCAR probability.
- Report within-facility equality and across-facility distribution of each analyte's generated effect. Do not fit a calibration correction.
- Preserve all cells, including sparse or undefined strata; label low-count intervals as imprecise. No post-hoc exclusion, threshold, or generator substitution.

## Interpretation and stopping

This study can reveal implementation/configuration mismatch in a synthetic mechanism. It cannot establish simulator realism, estimator validity, or clinical transport. If a specified mechanism fails to match its configured probability, stop and repair the simulator under a new source commit; register a new experiment before rerunning. If it matches, report only the tested configuration and Monte Carlo uncertainty. Do not use results to claim that the mechanism is clinically calibrated.

## Reproducibility artifacts

The runner, immutable `ACCESS_LOG.json`, machine-readable results, and generated report will be committed together after a successful one-time run. The result must contain input hashes and match the generated report. A separate replay command may be added only if it proves byte-identical inputs and does not repeat cohort generation or test access.
