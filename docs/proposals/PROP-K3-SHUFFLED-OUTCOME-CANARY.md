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

The latest PR #79 CI run (`39417463523`, backend-tests (misc) job `118609860513`, merged test commit `9bce4ff14d7da866635543010bb1411b32bb5082`) reports shuffled IPCW AUC `0.6136` against the unchanged `0.60` ceiling. Source inspection confirms the ungrouped event-only permutation described above. This is a gate result, not a model-performance estimate; it does not establish that the source change caused the failure or authorize modifying the test.

The next PR #79 run on branch head `38339ace662c186db6c20b5081c938f0c3f28d89` (CI run `39432790607`, backend-tests (misc) job `118662193428`; quality-gates run `39432790754`, coverage-ratchet job `118661931375`) independently reproduces shuffled IPCW AUC `0.6136378551` against the unchanged `0.60` ceiling. The coverage-ratchet job stops during coverage measurement because this canary fails; it is a propagated failure, not a separate test defect. The separate K1 acceptance failure is reported by the Postgres suite and backend-acceptance job. No seed, threshold, or test was changed.

## Disposition (2026-10-20)

Accepted by the repository owner for the PR #79 repair. The invalid row-wise,
event-only permutation was removed. The independent latent-column canary is
retained. No replacement performance canary is claimed: the current fast
landmark logistic implementation is not the registered Bayesian joint model,
and a patient-grouped survival null belongs with the genuine K3 implementation
and its preregistration. See ADR-0062. This leaves K3 model validity and its
statistical evaluation open in the core ML repair plan.
