# Proposal: replace the legacy baseline AUC sanity gate

## Problem

`packages/vigil-ml/tests/test_baselines_sanity.py` treats fixed AUC floors for B1, B4 and the fast K3 approximation as implementation invariants. Its fixture derives horizon labels from `WindowedFeatureExtractor`, whose former behavior silently marked patients censored before the horizon as non-recurrence. The corrected extractor now returns unknown labels for those rows, and classifier fitting requires explicit censor-aware weights. The same fixed-score gate is therefore coupled to the invalid label contract and cannot serve as an invariant for correct censoring.

## Proposed change

Keep the outcome and leakage checks in the unit suite, but move comparative performance requirements to a committed, pre-registered study with patient-disjoint train/validation/test cohorts, IPCW metrics, patient-level bootstrap intervals, and independent test access. A model may lose to a baseline without making the software test suite incorrect; the study must report that result and must not tune against the test cohort.

## Evidence and boundary

The focused command `./.venv/bin/pytest packages/vigil-ml/tests/test_features.py packages/vigil-ml/tests/test_baselines_sanity.py packages/vigil-ml/tests/test_m12.py -q` reported failures in `test_gbm_reaches_at_least_single_threshold_auc` and `test_k3_joint_model_distinct_from_single_threshold` after the label and feature-contract corrections; in the current focused run the former is blocked by its fixed B1 floor and the latter by its fixed fast-logistic floor. The feature, metric, leakage, and simulator contract suites pass. These fixed-score assertions remain unchanged pending review. Q-7's corrected feature contract now aligns the 90-day window with its name, normalizes acceleration for irregular intervals, preserves zero follow-up, rejects absent or contradictory outcome metadata, and validates observation/event boundaries; these changes make the older fixed-score result non-comparable and require a new preregistered study. The broader feature/metrics/leakage/simulator contract suites pass (57 tests), but the comparative fixed-score gate remains unresolved. This proposal does not weaken overseer-owned acceptance tests and does not claim either model performs adequately.

The latest PR #79 CI run (`39417463523`, backend-tests (ml) job `118609860489`, merged test commit `9bce4ff14d7da866635543010bb1411b32bb5082`) reproduces both unchanged fixed-floor failures: B1 AUC `0.5488445517` versus `> 0.65`, and fast landmark logistic AUC `0.7108199278` versus `> 0.72`. No comparison outcome was tuned and no assertion was changed.

## Decision needed

Overseer review should either accept a test redesign based on the censor-aware experiment protocol, or provide a corrected data-generating/estimand contract that supports a valid fixed-score invariant. Until then, do not represent those two assertions as passing.
