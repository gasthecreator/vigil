You are the executor for **Vigil**. Run `git pull origin main`, then re-read in full and in this order: `AGENTS.md` → `docs/MASTER_PLAN.md` (v1.2) → `docs/ML_PROGRAM.md` → **`docs/REALITY_RULES.md`** → `docs/STUBS.md` → `docs/PROGRESS.md` → **`docs/progress/VERDICT-P3.md`** → both skills in `.agent/skills/`.

Your last submission was rejected: the K1 model, the K8 ensemble and studies S4, S6, S10 were stubs or hard-coded numbers reported as `MET`, and K1's SBC and parameter-recovery "validation" never touched the model. The overseer's brief made `MET` the only attractive outcome; that is changed. **From now on, `NOT MET`, `BLOCKED`, `PARTIAL` and "this model lost to the baseline" are explicitly safe and welcome. A fabricated `MET` is the only outcome that invalidates your work.** If something is too hard to finish, build the honest part, register the rest in `docs/STUBS.md`, and report it as `NOT MET`.

**Assignment (one session; feature branches and PRs only; never push to `main`; never force-push):**

**Part A — Close R1–R7** in `VERDICT-P3.md` (retract the fabricated studies; wire `scripts/reality_audit.py` into CI with zero findings; keep `docs/STUBS.md` truthful; replace K3's hand-set coefficients with a fitted model; fix baselines; lead time at a fixed alert rate). Show a green CI run.

**Part B — Phase 3A only: make K1 real** (`docs/ML_PROGRAM.md` §3.1, `MASTER_PLAN` Phase 3A):
1. A mechanistic state-space model whose latent compartments, marker shedding/clearance and organ-damage dynamics are integrated numerically (state the equations in the model card; unit-test the integrator against closed-form cases and step-size convergence).
2. **`fit` must train.** Use the simulator's exported ground-truth latents (`vigil-sim`) to train an amortised recognition network (ELBO or neural posterior estimation), with train/validation/test splits by patient; log losses; seeds fixed.
3. **`predict_risk` must be derived from the model's posterior over recurrence onset/burden** (no hand-written logistic on raw markers). Horizon risks come from the posterior with credible intervals.
4. **Inference routes, each real, each tested, each comparable:** amortised VI; an online filter (UKF and/or particle filter) run over simulated visit sequences with a filter-consistency check (NEES/NIS within chi-square bounds); a reference **NUTS** fit (PyMC or NumPyro) on small cohorts as the gold standard; simulation-based inference (NPE) using the `sbi` ecosystem or a documented equivalent. If a route cannot be completed, do not name it anywhere; register it in `docs/STUBS.md`.
5. **SBC and parameter recovery run through the real inference code** on simulator output with known ground truth: rank-uniformity tests per parameter, bias/RMSE/90%-interval coverage for doubling time, shedding and clearance, with a documented list of non-identifiable parameters under typical visit schedules (profile-likelihood or equivalent).
6. Study S1's K1 arm under the existing PREREG (committed before running): K1 vs K3 vs B3/B4 at V ∈ {3,4,6,10,20}, patient-level bootstrap CIs, **lead time at a fixed alert rate**, results produced by code only. If K1 does not beat the best non-mechanistic model in the low-data regime, follow ML_PROGRAM §3.1 fallback and §13: three serious logged attempts, then ship the winner and say so.
7. Model card for K1 that lists exactly what is implemented and validated, and what is not.

**Do not start K2, K4, K5, K6, K8 or M12 (sub-phases 3B–3D).** Stop after 3A.

**Deliver:** `docs/progress/PHASE-3A-REPORT.md` (§16 structure; each gate `MET`/`NOT MET`/`BLOCKED` with evidence you can point to by file and test name), an updated `docs/PROGRESS.md` and `docs/STUBS.md`, green CI links, and the regenerated benchmark.
**Reply only with:** PR links + green CI run links; R1–R7 table; a 3A exit-gate table; the output of `python scripts/reality_audit.py`; which K1 inference routes truly exist; K1's measured result vs baselines in one sentence; everything you could not make real.
