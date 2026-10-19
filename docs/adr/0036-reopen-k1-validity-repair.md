---
status: accepted
date: 2026-10-19
decision-makers: Gideon Sanni (Product Owner), Codex (Executor)
consulted: Claude (Overseer; prior K1 review)
informed: Contributors
---

# 0036. Reopen K1 for validity repair without promotion

## Context

ADR-0007 closed K1 as research-only after the earlier S1 comparison and three K1 optimization runs. The 2026-10 core audit found that those runs are invalid evidence: they supplied `observed_ca_15_3` measurement flags as values, their interventions did not match their preregistrations, and their reported risk/interval semantics were unsupported. The audit also found that the public `vigil_ml` export and the contract/benchmark path resolve to different classes, and that neither implementation establishes the registered K1 model.

The owner has explicitly requested a complete core-ML repair and retraining effort. This supersedes ADR-0007 only on whether further K1 validity work is permitted; it does not reverse the prior negative performance evidence (which remains unreliable), authorize forced performance tuning, or promote K1.

## Decision

1. Reopen K1 for source-of-truth consolidation, correct training/inference, and preregistered synthetic evaluation under `docs/audits/CORE-ML-REPAIR-PLAN-2026-10.md`.
2. Use the overseer-defined `vigil_ml.k1` contract as the required compatibility surface. Reconcile all other K1 module/package exports to one implementation identity; retire or explicitly adapt legacy paths without leaving a second active model behind.
3. Keep K1 research-only and unavailable for recurrence-risk use until its event-time semantics, posterior uncertainty, simulator alignment, calibration, robustness, runtime, and independent review meet the binding gates. If the evidence does not support risk prediction, retain only validated parameter inference and remove risk claims.
4. No acceptance test, historical result, or frozen test cohort may be edited or reused to make the repair pass. Any changed estimand or consumed test cohort requires a new experiment ID and preregistration.

## Consequences

- Existing K1 reports, cards, and studies remain retracted or historical until their source discrepancies are resolved; no number is copied forward as current evidence.
- Engineering behavior may be checked with unit/property tests after preregistration. Model selection and any frozen-test evaluation follow the new K1 study protocol and clean-commit access guard.
- This ADR does not claim that K1 will outperform B3/B4, that its parameters are identifiable in clinical data, or that synthetic validation establishes clinical validity.
- The runtime path must fail closed or clearly abstain while the model is unvalidated; no deployment/promotion action is part of this decision.

