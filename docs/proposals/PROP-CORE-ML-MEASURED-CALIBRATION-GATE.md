---
id: PROP-CORE-ML-MEASURED-CALIBRATION-GATE
title: Replace synthetic calibration assertions with mask-aware reproducible checks
author: Codex
date: 2026-10-19
status: DRAFT
plan_version_impact: NONE
---

# PROP-CORE-ML-MEASURED-CALIBRATION-GATE: Replace synthetic calibration assertions with mask-aware reproducible checks

## 1. Problem Statement

`vigil_sim.calibration.evaluate_cohort_calibration` previously evaluated every stored CA 15-3 value, including values whose `observed_mask` was false. Since the simulator retains generated values behind missing measurements, the evaluator could count unavailable tests as detections and specificity observations. Its output was described as reproducing published calibration figures. A mask-aware correction is now in the working branch. The existing one-seed G1 test then fails its fixed conditional lead-time SD ceiling; the remaining assertions pass for that seed. Acceptance assertions are unchanged pending review.

## 2. Evidence Base

- The evaluator and regression are in `packages/vigil-sim/vigil_sim/calibration.py` and `packages/vigil-sim/tests/test_calibration.py`.
- Before the correction, the implementation iterated `obs.analytes` without consulting `obs.observed_mask`.
- After the correction, `./.venv/bin/pytest -q packages/vigil-sim/tests/test_calibration.py packages/vigil-sim/tests/test_generators.py` reports 17 passed and one failure: G1 conditional lead-time SD `113.61508552541177` days versus the unchanged upper limit of 110 days.
- For G1, seed 42, 350 patients, 730 days, the mask-aware evaluator reports conditional lead mean `99.64246109751565` days, unconditional lead mean `49.11287182057644`, sensitivity `0.5260663507109005`, observation and patient specificity both `1.0`, 1,334 measured CA 15-3 observations, and 81/211 recurrent patients without a measured CA 15-3 in the detection window. These are one-seed synthetic evaluator outputs, not clinical estimates.

## 3. Proposed Change

Keep the evaluator mask-aware and keep the current acceptance test unchanged until the overseer decides its contract. Replace the single-seed fixed-range calibration gate only through an overseer-approved, pre-registered synthetic calibration study that defines the observable estimand, recurrence/censoring eligibility, missing-measurement handling, seed count, uncertainty intervals, and stopping rule. Report measurement coverage beside sensitivity and lead time. Do not tune the generator to satisfy the currently failing SD limit.

## 4. Considered Alternatives

- **Keep the assertion red until the approved protocol is available.**
  - *Pros:* preserves the current acceptance contract and makes the discrepancy visible.
  - *Cons:* does not provide a valid multi-seed calibration assessment.
- **Increase the SD ceiling or tune the simulator to the test seed.**
  - *Pros:* could make the fixed-seed test pass.
  - *Cons:* changes the target after observing the result and risks optimizing synthetic output to a brittle gate; rejected.
- **Restore evaluation of hidden values.**
  - *Pros:* reproduces the prior evaluator behavior.
  - *Cons:* violates the observed-measurement contract and inflates evidence; rejected.

## 5. Evaluation & Verification Criteria

An approved replacement must fail if hidden values are counted, use only measured assays, specify how patients with no measured test are represented, account for competing events/censoring in its target, use multiple predeclared seeds with uncertainty, and label outputs synthetic. The historical assertions remain unchanged until a recorded overseer disposition.

## 6. Kill / Rollback Criterion

If the mask-aware, pre-registered study does not meet its stated targets, retain the negative result and remove the calibration claim for that target. Do not change the observation mask or widen the target after seeing study outputs.

## 7. Impact on Master Plan

No Master Plan change is requested. This proposal concerns the implementation and verification evidence for the existing M13 calibration-target requirement.
