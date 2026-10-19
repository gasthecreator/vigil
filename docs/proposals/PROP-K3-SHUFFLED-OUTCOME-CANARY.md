# Proposal: make the K3 shuffled-outcome canary patient-valid

## Observed failure

On the corrected generator source `37de102`, the unchanged `test_k3_joint_model_canaries` failed with shuffled IPCW AUC `0.6140` against its `0.60` ceiling. This is a test result, not a model-performance estimate.

## Test-contract issue

`packages/vigil-eval/tests/test_model_canaries.py` fits `FastLandmarkJointModel` and scores the same landmark rows used for fitting. It then permutes only the event-code vector `d`, leaving follow-up times, horizon labels, repeated landmarks, IPCW weights, and fitted scores in place. This does not define a null distribution for a patient-level survival outcome and can retain structured association through the unshuffled arrays. A single fixed permutation and raw `0.60` cutoff do not express Monte Carlo uncertainty or account for multiple rows per patient.

## Proposed disposition

- Keep the test unchanged until overseer review; do not widen the cutoff or tune against its seed.
- Replace the check with a patient-grouped negative control whose permutation unit and outcome arrays match the registered survival estimand, and evaluate against a predeclared null interval over multiple fixed seeds or a patient-level bootstrap.
- Preserve latent-column and input canaries independently of this shuffled-outcome diagnostic.
- If the check continues to evaluate K3, first resolve K3's invalid model identity; do not treat a passing randomization check as evidence for a Bayesian joint model.

## Evidence and boundary

The local test-suite output reported `test_k3_joint_model_canaries` at `packages/vigil-eval/tests/test_model_canaries.py:150`; source inspection identifies the ungrouped event-only permutation. No CI status was checked successfully, and no acceptance assertion was changed. This proposal does not claim the source change caused the failure or authorize modifying the test.

## Decision needed

Overseer review is needed to approve a patient-level null design and its finite-sample criterion. Until then, the gate remains unchanged and NOT MET on this branch.
