# AGENTS.md — Operating instructions for AI coding agents (Gemini / Antigravity, Claude, others)

This repository is **Vigil** (formerly *Sentinel*), a breast-cancer follow-up decision-support platform built in memory of the product owner's mother. It is a safety-relevant health project. Read this file first, every session.

## Mandatory reading order
1. This file.
2. [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) — the canonical product, plan, standards and definition of success. **Read all of it.**
3. [`docs/PROGRESS.md`](docs/PROGRESS.md) — current phase, verdicts, pending human actions.
4. [`docs/EVIDENCE.md`](docs/EVIDENCE.md) — what is known vs. only claimed.
5. The phase brief you were given (it will reference `MASTER_PLAN.md` §14).

## Always-on skills (read them, follow them)
- [`.agent/skills/complete-solution/SKILL.md`](.agent/skills/complete-solution/SKILL.md): take the complete path; no stubs, no deferrals, no fake verification; reduce scope only for a concrete blocker, stated plainly.
- [`.agent/skills/repo-standards/SKILL.md`](.agent/skills/repo-standards/SKILL.md): big-tech repository standards; use its `references/` and `assets/templates/`.

**Project overrides to the skills:** (a) the owner pre-approves repo-standards *Upgrade* work on files in this repository, so you do not wait for approval before applying audit findings — but you still never force-push, rewrite published history, delete data, or change GitHub settings/branch protection yourself (write the commands in `docs/ops/GITHUB-SETTINGS.md` instead); (b) "ask the user" decisions are recorded as ADRs unless they fall under `MASTER_PLAN.md` §17.3 (human-only actions); (c) there is **no time pressure**; nothing is shrunk for being long or hard — only a pre-registered, evidenced failed experiment (§13) or a named external blocker justifies reducing scope.

## Non-negotiables (full text in MASTER_PLAN §3 and §11)
1. **Truth over impressiveness.** No claim without a committed artifact that proves it. Synthetic-data results are always labelled *synthetic*. Never write "complete", "done", "production-ready", "enterprise-grade", "state-of-the-art", "clinically validated" without evidence. A result like ROC-AUC = 1.000 is a defect to investigate, never a success.
2. **Safety first.** Never output or imply a diagnosis; never show "low risk = safe"; support abstention; follow the claims policy and hazard log.
3. **No leakage.** Labels must be real clinical events with a horizon; features must never contain outcome-derived information (the prototype's `is_anomaly` label is the cautionary example).
4. **No pickle** for model exchange; no secrets, personal paths, or wildcard CORS; no unauthenticated data-mutating endpoints outside the `local` profile.
5. **Reproducible.** Fixed seeds, pinned dependencies, one-command regeneration of every reported number.
6. **Do not edit `docs/MASTER_PLAN.md`.** File a proposal in `docs/proposals/` if the plan is wrong or incomplete.
7. **Stop at phase boundaries** (commit the phase report, update the ledger, wait for the verdict) — but never stop *inside* a phase to ask permission to continue.

## How to work
- Plan briefly, then execute the whole phase end-to-end; keep a task list; verify for real (run the tests/builds/benchmarks); fix root causes.
- Small, reviewable PRs/commits with Conventional Commit messages; tests and docs in the same change.
- Record decisions as ADRs (`docs/adr/`), experiments as `experiments/EXP-####/`, and surprises in the phase report.
- When blocked by something only a human can do, do everything else, draft the artifact (application, agreement, command list), and list it under "Pending human actions" in `docs/PROGRESS.md`.
- When in doubt about safety or honesty, choose the more conservative behaviour and record why.
