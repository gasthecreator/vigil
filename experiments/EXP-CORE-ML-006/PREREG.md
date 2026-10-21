# EXP-CORE-ML-006 preregistration: post-diagnosis follow-up boundary

## Status and scope

This is a new, one-time synthetic simulator audit. It is registered after EXP-CORE-ML-005 and uses independent seeds because its source assumptions are changing. EXP-CORE-ML-005 remains preserved as evidence for its exact source commit and will not be overwritten or replayed. No model is fitted, no threshold is selected, and no clinical claim is tested.

## Questions and estimands

1. Does the generated cohort stop routine surveillance visits after a synthetic confirmed recurrence diagnosis, allowing visits through at most 90 days after diagnosis to represent transition to acute oncology?
2. Are visits strictly before terminal competing events and loss to follow-up?
3. On the resulting observation set, do imaging propensity, result sensitivity/specificity, assay missingness, and shared facility-effect checks match the same versioned K3-v2 assumptions audited in EXP-CORE-ML-005?

These are implementation checks for the synthetic generator only. They do not establish clinical follow-up patterns, test accuracy, verification-bias correction, or prediction performance.

## Design

- Use `packages/vigil-sim/vigil_sim/config/synthetic_population_k3_v2.json`; record its SHA-256.
- Use G1, G2, and G3; five independent replicates of 2,000 patients per generator; 730 simulated days.
- Seeds: `960000 + 10000 * generator_index + replicate_index`, with G1=0, G2=1, G3=2 and replicate indices 0–4. These differ from all EXP-CORE-ML-005 seeds.
- The committed one-time runner must record the clean source commit, runner/profile/environment hashes, exact access log, result hash, and report hash. It must refuse dirty work trees and pre-existing access/results/reports.
- Assert that for every patient with a confirmed observed recurrence, no emitted observation is later than `observed_recurrence_day + 90`; for patients with a competing event, no emitted observation is at or later than its event day. Count and report all denominators and violations. Also report cases with no visits and any fallback behavior.
- Repeat the per-visit propensity, imaging-result, assay-missingness, and facility-effect summaries defined in EXP-CORE-ML-005 on only the emitted observation rows. Retain all generator/replicate cells and uncertainty intervals.

## Interpretation and stopping

Any post-boundary observation is a generator defect; do not suppress it in analysis. Any other mismatch is reported and repaired under a new preregistration before further result generation. Passing checks show only that this synthetic implementation follows its declared rules. They do not validate the rules against clinical evidence.

## Outputs

After the runner is committed and executed once, commit `ACCESS_LOG.json`, `results.json`, and generated `REPORT.md`. Do not overwrite or replay these artifacts. Any future code or assumptions change requires another new experiment ID and independent seeds.
