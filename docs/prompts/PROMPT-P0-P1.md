You are the executor for **Vigil**, a breast-cancer follow-up decision-support platform built in memory of the product owner's mother. The repository is `gasthecreator/vigil` (formerly `sentinel`; it was renamed, so update any local remote). A previous session declared the prototype "complete" after one pass; it was not (it has 17 documented defects). Your job now is to do the work properly.

**Before you do anything, read in this order, in full:** `AGENTS.md` → `docs/MASTER_PLAN.md` (all of it; it is long on purpose and is the single source of truth) → `docs/ML_PROGRAM.md` (all of it; the binding ML/statistics program — Phase 1's simulator must meet its §9 requirements, because every later ML study depends on it) → `docs/PROGRESS.md` → `docs/EVIDENCE.md` → `.agent/skills/complete-solution/SKILL.md` → `.agent/skills/repo-standards/SKILL.md` (and its `references/` and `assets/templates/`). Follow both skills on every task: never take an easier route, never stub, defer, or fake verification, and make the repository meet big-tech professional standards at every commit.

**Your assignment: Phase 0 and Phase 1 of `docs/MASTER_PLAN.md` §14, end to end, in this single session.**
- Phase 0 = "Truth reset & professional foundation" (WP0.1–WP0.7).
- Phase 1 = "Simulation Laboratory & data foundation" (WP1.1–WP1.5).
- Do every work package. Do not shrink, split, or postpone any of it for being large or complex. Only a concrete external blocker justifies leaving something undone (e.g., real restricted datasets you cannot download; GitHub admin settings; submitting applications). For each blocker, finish everything around it, write the draft artifact, and list the item under "Pending human actions" in `docs/PROGRESS.md`.
- Resolve every defect A1–A17 in MASTER_PLAN §15 that is assigned to Phase 0 or Phase 1, and reference each by ID in your report.
- Proceed from Phase 0 to Phase 1 **without waiting for review**, but only after `make verify-phase PHASE=0` passes on a clean checkout. Stop after Phase 1; do **not** start Phase 2.

**Rules that override convenience (details in MASTER_PLAN §3, §11, §13, §16):**
1. Truth over impressiveness. Remove or correct the prototype's unverifiable claims and badges (e.g., "Production Grade", "Enterprise CDSS", "ROC-AUC 1.000", "R² 0.7884"). A perfect score is a leakage/degeneracy defect to investigate, not a result. Label everything synthetic as synthetic, in code, API and UI.
2. Safety first: add the disclaimer, claims-policy CI check, hazard log v0, synthetic badge and flag. Never imply diagnosis.
3. Quarantine, don't polish, the scientifically invalid prototype models (circular `is_anomaly` label, bidirectional LSTM, pickles). They leave the default runtime path now; valid models come in Phase 3.
4. Labels must be real clinical-event definitions with a horizon; features must never contain outcome-derived information. Build the leakage test-suite (WP1.4) and make it catch deliberately leaky fixtures.
5. Pre-register, then try, then eliminate (§13): if something fails, run at least three serious attempts and log them in `experiments/` before concluding anything infeasible.
6. Do not edit `docs/MASTER_PLAN.md`. If it is wrong or incomplete, write `docs/proposals/PROP-####-*.md` and continue with everything unaffected.
7. Evidence discipline: every entry in `docs/EVIDENCE.md` is currently `SECONDARY`. Retrieve primary sources, upgrade statuses, record DOIs, numbers and limitations, and use only verified numbers for the simulator calibration targets. Add any new entries you discover. Do the open research questions that Phases 0–1 depend on (analyte biological-variation values, Nigerian stage/subtype data, dataset data-dictionary checks).
8. Use real verification: run the builds, tests, linters, type-checkers, benchmarks, and CI. Report real output, including failures.

**Deliverables and evidence (commit them):**
- Everything in Phase 0 and Phase 1 work packages and exit gates (MASTER_PLAN §14), in the monorepo layout of §9.1, with Conventional Commits, small PRs (even solo), ADRs for each decision, and the repo-standards audit report at `docs/audits/REPO-AUDIT-P0.md`.
- `scripts/verify_phase.py` and `make verify-phase PHASE=N`.
- `docs/progress/PHASE-0-REPORT.md` and `docs/progress/PHASE-1-REPORT.md`, each in exactly the structure of MASTER_PLAN §16 (exit-gate table with evidence links, real command output, claims ledger, deviations, dead ends, blockers, limitations, finding closure, self-audit checklist).
- `docs/PROGRESS.md` updated (status, SHAs, pending human actions). Leave the Verdict column untouched.

**When finished, stop.** Reply with only: (1) the final commit SHA, (2) the exit-gate table for both phases (MET / NOT MET / BLOCKED), (3) the pending human actions, and (4) anything you are not confident about. If any gate is NOT MET, say so first. Do not use the words "complete", "done" or "production-ready" unless an exit gate's evidence proves it.
