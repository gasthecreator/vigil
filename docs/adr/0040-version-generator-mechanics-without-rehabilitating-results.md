# ADR-0040: Version generator mechanics without rehabilitating results

## Status

Accepted for the synthetic simulator implementation; no evaluation result is approved by this decision.

## Context

The G1/G2/G3 source used many kinetic, treatment, verification, and artifact constants directly in code. The `balanced_synthetic_core_v3` profile already versioned several population and observation assumptions, but a profile hash did not identify the full mechanism settings. Historical profiles and frozen result producers must remain reproducible as historical artifacts; their outputs must not be rewritten or silently reinterpreted.

G3 also let its linearly increasing recurrence signal exceed its declared full-signal burden after the recurrence day. This made the generated latent burden depend on time beyond the configured signal saturation.

## Decision

- Put the legacy G1/G2/G3 mechanism values used by `balanced_synthetic_core_v3` in that profile, including lead windows, growth ranges, burden/marker/organ coupling, treatment effects, burst timing, heavy-tail noise, and pre-analytical error rates/magnitudes.
- Apply the declared facility offset and scale effects in G2/G3 for this profile; their historical profile paths retain prior behavior.
- Record that these values were transcribed from legacy source and have no claimed clinical calibration or literature validation. New model-selection use requires a preregistered sensitivity study; this profile has not generated new evaluation results.
- Require the v3 profile to declare the complete mechanism setting set and reject malformed/non-finite inputs. Keep compatibility fallbacks for historical profiles so their prior semantics are not silently changed.
- In `balanced_synthetic_core_v3`, bound G3's signal to `[0, 1]`, so latent burden cannot exceed its declared full-signal mass. Keep the old post-recurrence extrapolation only for legacy profiles to preserve frozen-replay semantics; it is not endorsed as a valid model behavior.
- Preserve existing reports/results and their historical status. This decision does not make G1 an ODE/clearance model or G2 a Poisson shot-noise model.

## Consequences

The v3 profile hash now describes the major generator assumptions consumed by the implemented stress processes. The equations remain stress-process equations, not validated tumor biology. Calibration, verification-bias validity, sensitivity analysis, and regenerated registered evidence remain open under Q-7 packages B, C, and G.
