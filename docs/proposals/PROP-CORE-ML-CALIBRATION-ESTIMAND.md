---
id: PROP-CORE-ML-CALIBRATION-ESTIMAND
title: Align the legacy CA 15-3 simulator comparison with its cited estimand
author: Codex
date: 2026-10-20
status: UNDER REVIEW
plan_version_impact: NONE
---

# PROP-CORE-ML-CALIBRATION-ESTIMAND: Align the CA 15-3 simulator comparison with E1

## 1. Problem Statement

`vigil_sim.calibration.evaluate_cohort_calibration` is described as comparing synthetic outputs with the Molina et al. E1 results, but its current outcome and eligibility rules do not match the cited summaries:

- Lead time is measured to `true_recurrence_day` (latent onset), while E1 reports marker elevation before diagnosis.
- The CA 15-3 lead-time list accepts any pre-latent-onset elevation, with no registered pre-diagnosis window.
- The sensitivity window extends 30 days after latent recurrence, so post-event samples can count as preclinical detections.
- All recurrent sites enter the sensitivity denominator, although E1 reports 54% after excluding locoregional recurrences.
- E1's CA 15-3 pre-diagnosis result is 37/91 (41%) in the monitored subset and uses a reported cutoff above 60 U/mL. The evaluator's default was 30.0; Q-7 now sources that value from the registry reference upper limit and labels it accurately, but this remains a different comparison point.
- The 88% patient-specificity gate and other single-seed pass ranges are implementation criteria, not the published E1 estimates.

These differences make `lead_time_target_met`, `sensitivity_target_met`, `specificity_target_met`, and `all_targets_met` unsuitable as evidence that the simulator reproduces E1, even when the evaluator correctly masks unmeasured values.

## 2. Evidence Base

- `packages/vigil-sim/vigil_sim/calibration.py::evaluate_cohort_calibration` reads `true_recurrence_event` and `true_recurrence_day` for recurrent cases; its sensitivity predicate includes days through `true_recurrence_day + 30`.
- `packages/vigil-sim/tests/test_calibration.py::test_g1_smooth_calibration_targets` evaluates one G1 cohort at seed 42 and 350 patients. Its comments compare the result with the Molina targets.
- The E1 dossier records 37/91 CA 15-3 monitored recurrences elevated before diagnosis, a 4.2 ± 2.3 month lead time, a 54% sensitivity after excluding locoregional recurrences, and 99% specificity among 444 NED patients. It records the source CA 15-3 cutoff as greater than 60 U/mL.
- The primary abstract is indexed at [PubMed PMID 7579505](https://pubmed.ncbi.nlm.nih.gov/7579505/). It reports the 1,023-patient cohort, 37/91 CA 15-3 pre-diagnosis elevations and 4.2 ± 2.3 month lead time.
- The current registry-derived default is the CA 15-3 population reference upper limit, not an assay-independent diagnostic threshold. The Q-7 source correction records this distinction in `packages/vigil-sim/vigil_sim/calibration.py` and the entrypoint crosswalk.

## 3. Proposed Change

Keep the existing evaluator outputs and historical results as legacy synthetic diagnostics until disposition. For any replacement E1 comparison:

1. Define the event time as observed clinical diagnosis, not latent recurrence, or rename the estimand and remove E1 comparison claims if the simulator cannot represent the source endpoint.
2. Use an explicit, source-traceable CA 15-3 comparison cutoff in the source assay's unit, with a validated conversion to the simulator's canonical unit. Keep the population reference limit as a separate quantity.
3. Count only finite, observed CA 15-3 measurements strictly before diagnosis. Report marker coverage and missing-test counts beside the measured-case detection fraction.
4. Separate locoregional from distant recurrence and use the denominator matching the particular E1 statistic. Do not pool 37/91 with the 54% distant-recurrence result.
5. Define the NED/control set and measured-assay denominator explicitly. Remove unsupported patient-specificity pass criteria or label them as independent engineering targets with their own rationale.
6. Register a multi-seed study, uncertainty method, tolerance/stopping rule, and fresh seed namespace before generating cohorts. Preserve per-seed results and label all conclusions synthetic.

Do not tune simulator parameters against the current seed or widen existing acceptance bounds. Keep the overseer-owned test unchanged until this proposal is dispositioned.

## 4. Considered Alternatives

- **Recommended: implement a source-aligned synthetic comparison after disposition.**
  - *Pros:* defines the intended observable event and preserves a useful, explicitly synthetic calibration target.
  - *Cons:* needs a verified site mapping, assay-unit decision, and a new registered study; it will not establish clinical calibration.
- **Retain a latent-onset evaluator but withdraw the E1 comparison.**
  - *Pros:* useful for internal simulator mechanism diagnostics without conflating biological onset and clinical diagnosis.
  - *Cons:* its existing pass flags and reports must be renamed/reframed; it cannot support E1 calibration claims.
- **Keep the current output as E1 calibration evidence.**
  - *Rejected:* event time, post-event inclusion, recurrence mix, cutoff, and denominators do not align with the source summary.

## 5. Evaluation & Verification Criteria

After disposition, tests must prove that a post-diagnosis measurement cannot count as preclinical detection; latent and observed diagnosis times are not interchanged; non-distant cases do not enter the distant-metastasis denominator; hidden measurements do not count; units and cutoff provenance are validated; and empty or unmeasured strata remain undefined with denominators reported. The registered study must use multiple fresh seeds and report uncertainty without tuning to those outcomes.

## 6. Kill / Rollback Criterion

If the simulator cannot faithfully define observed diagnosis, site eligibility, or assay unit conversion, retain only the latent-onset diagnostic and remove the E1 calibration claim. If a preregistered multi-seed comparison fails its registered criterion, preserve the negative result and do not tune on those test seeds.

## 7. Impact on Master Plan

No Master Plan change is requested. This proposal clarifies evidence required for the existing M13 calibration-target requirement.
