# Proposal: quarantine the current K3 implementation pending a real joint model

## Finding

The class `BayesianJointModelK3` in `packages/vigil-ml/vigil_ml/joint_model.py` is presented as a Bayesian joint longitudinal-survival model, but its sampler draws a shared linear trajectory over rows and a scalar marker association. It does not model patient random effects, competing risks, repeated patient clusters, or the registered shared-parameter structure. It uses fixed marker-centering and hazard constants. Its fast sibling is a regularized logistic classifier; its empirical-Bayes latent-state calculation is not used in prediction. The historical fast class is therefore a baseline, not a fast implementation of K3.

Earlier K3 parameter/PPC tests do not validate the registered model: the synthetic test generates the outcome from a marker threshold and does not independently exercise the intended joint survival likelihood. The fixed residual-normality p-value has been replaced with a calculated statistic, but this narrow fix does not address the model mismatch.

## Proposed disposition

1. Keep K3 marked research-only and remove the Bayesian/joint/production claims from user-facing model cards and model-selection records.
2. Do not use either implementation as clinical evidence or call the fast classifier a K3 retrain.
3. Implement the registered competing-risk mixed-effects model in Stan or PyMC, with patient-grouped longitudinal likelihood, explicit censoring/event definitions, posterior diagnostics, and dynamic prediction. Keep the fast baseline under a distinct name.
4. Before testing the replacement, commit a preregistration with synthetic data-generating assumptions, patient-level splits, calibration, metrics, and elimination rules. Use independent seeds and a reproducible run artifact.

## Evidence and boundary

This proposal is based on source inspection of `BayesianJointModelK3.fit`, `_sample_chain`, `check_posterior_predictive`, and `FastLandmarkJointModel.predict_risk`, compared with `docs/ML_PROGRAM.md` §3.3 and `docs/prompts/PROMPT-P2.md` / `PROMPT-P3.md`. It makes no performance claim and does not replace overseer-owned acceptance tests or verdicts. Current pre-registered core tuning in EXP-CORE-ML-003 includes the fast logistic baseline under an explicitly non-Bayesian name and does not include `BayesianJointModelK3`.


## Q-7 implementation update (2026-10-20)

ADR-0049 now quarantines `BayesianJointModelK3`: `fit`, posterior-predictive checks, and `predict_risk` fail closed; the old fake sampler and its posterior-shaped outputs were removed. Package tests now assert quarantine instead of parameter recovery or posterior coverage. The fast path is now canonically named `LandmarkLogisticResearchBaseline`; `FastLandmarkJointModel` remains as an import alias for frozen experiment source compatibility; it is a logistic research baseline; its unused empirical-Bayes utility and hardcoded trajectory parameters were removed, and package tests no longer encode an unverified latency budget. This is containment, not a replacement model; the registered K3 and package E remain open. Frozen experiment sources and outputs were not modified or rerun.
