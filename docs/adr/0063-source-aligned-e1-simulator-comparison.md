# ADR-0063: Use source-aligned observed-diagnosis semantics for the E1 simulator comparison

**Status:** Accepted by owner, 2026-10-20  
**Decision owner:** Gideon Sanni  
**Context:** Q-7 package B; `PROP-CORE-ML-CALIBRATION-ESTIMAND.md`

## Context

The legacy calibration evaluator used latent recurrence onset, accepted measurements on or after the event, and compared an unsourced 30 U/mL default with E1's reported CA 15-3 cutoff of 60 U/mL. It also compared one-seed pass ranges with literature point estimates. That contract cannot support the stated E1 comparison. The simulator has an observed diagnosis event produced by its verification process, but its recurrence-site generator currently selects only bone, lung, liver, or brain and has no locoregional recurrence class.

## Decision

Use the simulator's observed diagnosis day as the event time for a new, source-aligned, synthetic comparison. Count only finite CA 15-3 values marked observed on days strictly before diagnosis. Use the source-reported cutoff of greater than 60 U/mL, converted through the repository's unit converter from `U/mL` to the analyte's canonical unit. Keep the registry reference limit as a distinct value. Register a fresh multi-seed protocol before generating cohorts; preserve the legacy evaluator and its outputs as historical diagnostics.

Report monitored-case coverage and case detection separately. The 37/91 comparison uses diagnosed recurrent patients with at least one measured CA 15-3 value before diagnosis; also report detection over all diagnosed recurrent patients. Lead time is the first pre-diagnosis measured elevation to observed diagnosis. Compare its mean descriptively with the reported 4.2 ± 2.3 months, whose dispersion convention is unspecified in the abstract, and report simulator SD separately. Define and report measured observed-NED specificity separately from an oracle recurrence-free sensitivity analysis, because occult latent cases are not identifiable from observed diagnosis alone.

Do not claim the source's 54% distant-recurrence sensitivity is reproduced by the current site generator: it lacks locoregional cases, so the source denominator cannot be reconstructed. If the required E1 statistics are unavailable or undefined, report them as not estimable with denominators and do not substitute a synthetic number. No result from this study is clinical validation, a diagnostic threshold recommendation, or evidence for clinical use of routine tumor-marker surveillance.

## Consequences

- Existing single-seed target gates remain software diagnostics, not evidence of E1 agreement.
- The new evaluator and study artifacts are separate from the legacy function and results.
- Simulator parameter changes are not authorized by this decision and require separate, preregistered studies.
- The endpoint that requires locoregional-versus-distant stratification remains unsupported until the simulator can represent those categories under a reviewed protocol.
