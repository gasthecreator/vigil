# Proposal: replace the legacy baseline AUC sanity gate

## Problem

`packages/vigil-ml/tests/test_baselines_sanity.py` treats fixed AUC floors for B1, B4 and the fast K3 approximation as implementation invariants. Its fixture derives horizon labels from `WindowedFeatureExtractor`, whose former behavior silently marked patients censored before the horizon as non-recurrence. The corrected extractor now returns unknown labels for those rows, and classifier fitting requires explicit censor-aware weights. The same fixed-score gate is therefore coupled to the invalid label contract and cannot serve as an invariant for correct censoring.

## Proposed change

Keep the outcome and leakage checks in the unit suite, but move comparative performance requirements to a committed, pre-registered study with patient-disjoint train/validation/test cohorts, IPCW metrics, patient-level bootstrap intervals, and independent test access. A model may lose to a baseline without making the software test suite incorrect; the study must report that result and must not tune against the test cohort.

## Evidence and boundary

The focused test command `./.venv/bin/pytest packages/vigil-ml/tests/test_features.py packages/vigil-ml/tests/test_baselines_sanity.py packages/vigil-eval/tests/test_model_canaries.py packages/vigil-eval/tests/test_metrics.py packages/vigil-sim/tests/test_generators.py` currently reports failures in `test_gbm_reaches_at_least_single_threshold_auc` and `test_k3_joint_model_distinct_from_single_threshold` after the label contract correction. The fixed-score assertions are left unchanged pending review. This proposal does not weaken acceptance tests and does not claim either model performs adequately.

## Decision needed

Overseer review should either accept a test redesign based on the censor-aware experiment protocol, or provide a corrected data-generating/estimand contract that supports a valid fixed-score invariant. Until then, do not represent those two assertions as passing.
