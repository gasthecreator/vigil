---
status: accepted
date: 2026-10-20
decision-makers: Codex (Executor)
consulted: None
informed: Contributors
---

# 0049. Fail closed on the invalid historical K3 sampler

## Context

ADR-0006 and the old K3 tests described `BayesianJointModelK3` as a valid Bayesian joint survival model. Source review found that it pooled rows as independent observations, omitted patient random effects and competing risks, used fixed hazard and marker constants, and exposed posterior-style diagnostics from a different model. Its fast sibling is a fitted logistic landmark baseline, not a joint model or production approximation. The implementation does not meet `docs/ML_PROGRAM.md` §3.3.

## Decision

Quarantine the historical `BayesianJointModelK3` compatibility name. `fit` and `predict_risk` now fail closed with an actionable error, and the model identifier explicitly marks it invalid. Replace tests that treated the old sampler as validated with tests that assert quarantine. Rename the fast path canonically to `LandmarkLogisticResearchBaseline`, while preserving `FastLandmarkJointModel` as a source-compatibility alias for historical experiments. Describe and test it as a research logistic baseline; its unused empirical-Bayes helper and hardcoded trajectory parameters were removed; its package tests make no unsupported clinical latency claim. The legacy `horizon_days` constructor argument is retained for import compatibility but is ignored because labels define the target.

Do not reuse the old outputs, rewrite frozen studies, or treat this quarantine as a replacement model. A genuine K3 requires a separately preregistered, patient-grouped longitudinal competing-risk model and evidence under package E. ADR-0006 remains historical and is superseded on this disposition only.

## Consequences

Historical experiments that import the fast class retain their source compatibility, but their model identity is a logistic baseline. Any caller that attempts the invalid Bayesian class now receives an explicit error instead of a fabricated inference result. K3 remains unavailable for valid joint-model inference until the registered replacement and its preregistered evaluation are completed.
