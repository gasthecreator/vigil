# Proposal: resolve the B2 velocity comparator's units and provenance

## Finding

`packages/vigil-ml/vigil_ml/baselines.py::VelocityBaseline` combines two slopes with different dimensions:

- CA 15-3 is measured in `[iU]/mL`; its slope is `[iU]/mL/day`.
- CEA is measured in `ug/L`; its slope is `ug/L/day`, then the implementation multiplies it by `2.0` and compares it with the CA 15-3 slope.
- Both are thresholded with the same default `velocity_cutoff=0.08`, which has no cited source, versioned configuration, or sensitivity analysis.

`experiments/EXP-CORE-ML-008/PREREG.md` names B2 as a comparator but does not freeze this cutoff, the CEA multiplier, the unit transformation, or an alternative-analyte policy. Its test result is reproducible from the implementation, but the B2 method is under-specified in the preregistration. Preserve the result as historical synthetic output; do not use its B2 contrasts to support a clinical comparator claim or tune the rule against its frozen cohorts.

The unit definitions are in [`packages/vigil-core/vigil_core/analytes.py`](../../packages/vigil-core/vigil_core/analytes.py). The rule's current implementation is explicitly described as an unvalidated research assumption, but that warning does not supply the missing numeric provenance or make the cross-analyte comparison dimensionally valid.

## External evidence and limits

One published surveillance study evaluated CA 15-3 velocity and reported a criterion of `>2.5 U/mL/year` as its best single-marker criterion. This converts arithmetically to about `0.00685 U/mL/day`, while the current B2 default is `0.08` `[iU]/mL/day` (29.2 per year), about 11.7 times larger. This difference is a provenance discrepancy, not evidence that the published criterion should replace B2: assay, cohort, estimand, method, and transportability require review. [Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC7375621/)

ASCO's 2026 post-treatment surveillance guideline states that routine CEA, CA 15-3, and CA 27.29 testing is not recommended for asymptomatic breast cancer survivors. The 2007 ASCO update likewise noted that early marker-detected metastatic findings had no demonstrated outcome benefit and did not recommend their use for routine follow-up. These sources rule out presenting B2 as a clinically validated surveillance threshold; they do not preclude a clearly labeled synthetic-method comparator. [ASCO 2026 guideline](https://ascopubs.org/doi/10.1200/JCO-26-01700), [ASCO 2007 update](https://pmc.ncbi.nlm.nih.gov/articles/PMC2793754/)

## Proposed disposition

1. Keep the existing source and EXP-008 artifacts unchanged as historical evidence until the overseer rules on the comparator.
2. Do not treat B2's EXP-008 contrasts as confirmatory model-selection evidence. The result remains synthetic, and the B2 method parameters were not fully registered.
3. Before another B2 comparison, either define a unit-consistent, analyte-specific rule with cited rationale and a versioned configuration, or retire B2 from the comparator set. Register the chosen definition and all sensitivity analyses before generating any evaluation cohorts; use new seeds because EXP-008 test access is complete.
4. Keep clinical surveillance use disabled. No fixed velocity threshold is supported by the evidence collected here.

## Decision requested

Overseer disposition is needed on whether B2 is retained as a nonclinical synthetic comparator after a new registered specification, or retired from model-selection comparisons. Until disposition and a new preregistration, do not silently modify the threshold or reuse EXP-008 cohorts.
