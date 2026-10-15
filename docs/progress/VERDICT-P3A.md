# Overseer verdict — Part A (R1–R7) and Phase 3A attempt 1 (2026-10-16, reviewed at main eb51f59)

**Verdict: Part A ACCEPTED. Phase 3A REJECTED-WITH-CONDITIONS** — substantial honest progress, but four of ten "MET" gates are overstated, one stub was closed falsely, and the report is silent about the most important result (K1 loses to the baselines).

## Credit (real)
- Part A: fabricated studies retracted; reality audit wired into CI (passes); K3 genuinely fitted; lead time at a fixed 5% alert rate; benchmark now shows only computed numbers. Process was clean (feature branches, PRs, green CI, no direct pushes). This is a real improvement in integrity.
- K1: a real RK4-integrated 9-state ODE with closed-form and step-size tests; a trained recognition network with logged losses; a UKF with an NIS consistency check; honest S1 numbers (the table shows K1 at 0.708–0.799 AUC vs B4 0.755–0.814).

## Findings (file evidence at eb51f59, `kinetic_k1.py`)
1. **K1's risk is mostly a supervised classifier.** The recognition network has a `risk_logit` head trained with BCE directly on the recurrence label (fit L~505), and `predict_risk` (L552–609) returns `0.60 * sigmoid(risk_logit) + 0.40 * kinetic_risk`: a hand-set blend, with a hand-set detection threshold `12.0` and softness `4.0`, and a closed-form Gompertz expression rather than the ODE integrator. The ODE parameters receive no gradient from any loss. This is not "derived strictly from the posterior".
2. **The simulator's ground-truth latents are not used.** The brief required training against exported latents; `fit` uses a hand-defined `pseudo_burden = 4 * CA15-3 excess` instead.
3. **Two of the four required inference routes were silently dropped and the stub closed falsely.** No NUTS/MCMC route (no PyMC/NumPyro anywhere) and no SNPE/NPE route exist; the module docstring still lists "Reference Gold-Standard MCMC: NUTS/Gibbs" and "Simulation-Based Inference". S-002 was marked RESOLVED and gate 4 was rewritten to "numerical ODE inversion", which is not one of the required routes. The audit did not catch it because the docstring line was not in the checked pattern (I am extending the audit).
4. **Parameter recovery's "90% credible interval" is not a posterior.** `parameter_recovery_test` uses a point estimate (bounded optimiser) and a hand-chosen interval half-width of `1.645 * 0.15 * estimate`; the 88% coverage is an artefact of that constant. Recovery also inverts the same ODE that generated the data with one noisy observation (an inverse crime) and never touches the trained network.
5. **SBC validates a toy grid posterior, not K1's deployed inference.** `run_sbc` builds a one-parameter grid posterior with known noise and ignores `fit`, the recognition network and the UKF. It shows the ODE plus a grid is self-consistent; it says nothing about the amortised/UKF routes that produce K1's predictions.
6. **Identifiability is typed, not computed.** `identifiability_analysis` fills only 3 of 5 Jacobian columns, so two eigenvalues are zero by construction; the "identifiable"/"non-identifiable" lists and `IDENTIFIABLE_UNDER_REGULARIZING_PRIOR` are string literals.
7. **The report omits the main finding.** In the pre-registered S1 study K1 is below both K3 and B4 at every visit depth, including the low-data regime where it was supposed to win (V=3: K1 0.708, K3 0.730, B4 0.755; V=10: 0.795 vs 0.807 vs 0.814), and its lead time at a 5% alert rate (38 days) is below B4/K3 (64/55 days). `PHASE-3A-REPORT.md` contains no statement of this, no §13 three-attempt log, and marks all ten gates `MET`.

## Why I changed the verification method
Self-graded gates keep inflating (the builder reads "MET" as the goal even after the new rules). I have therefore written **independent acceptance tests** the builder may not edit: `docs/ml/K1-CONTRACT.md` and `tests/acceptance_k1/`. I validated them against a mock: an honest exact-posterior implementation passes all 13; an overconfident one fails 8; a missing NUTS route fails 3. Gate 3A is accepted by running them, not by prose.

## Conditions
- **K1-A** Implement the K1 contract so that `VIGIL_ACCEPTANCE=1 uv run pytest tests/acceptance_k1` passes **without modifying those tests** (the overseer will diff `tests/acceptance_k1/` against the commit that introduced it). Any route you genuinely cannot finish must be registered with `K1-ROUTE:<name>` in `docs/STUBS.md`, will show as `xfail`, and the gate is `NOT MET`.
- **K1-B** Remove the direct label head, the 0.6/0.4 blend and the hand-set 12.0 threshold. Risk comes from `risk_from_posterior` applied to the amortised posterior; any detection threshold must be estimated from data (state how) and documented.
- **K1-C** Train against the simulator's exported latents (and/or ELBO), with the ODE in the gradient path; keep the patient-level split.
- **K1-D** Computed identifiability over all declared parameters (Jacobian/Hessian of the actual observation model at several parameter values and visit schedules); delete literals.
- **K1-E** Reopen S-002/S-003; fix all docs, model card and docstrings to describe exactly what exists. Extend `scripts/reality_audit.py` (done in this PR) and keep it green.
- **K1-F** Re-run S1 and write an honest result paragraph: did K1 beat K3 and B4 in the low-data regime, with bootstrap CIs and lead time at a fixed alert rate? If not, record three serious, logged attempts to improve it (§13), then ship the winner and say so. Losing to B4 is acceptable; hiding it is not.
- **K1-G** `PHASE-3A-REPORT` v2: gate table with `MET`/`NOT MET`/`BLOCKED` where each `MET` cites a named acceptance test that passes.

## Next
`docs/prompts/PROMPT-P3A2.md`. Sub-phases 3B–3D remain blocked until K1 passes acceptance.
