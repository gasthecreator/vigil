---
status: accepted
date: 2026-10-14
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0005. Proposal Process for Master Plan Evolution

## Context and Problem Statement
Per `docs/MASTER_PLAN.md` §0.3 and §17.2, `MASTER_PLAN.md` is the canonical single source of truth for Vigil. The plan author and reviewer is Claude (Overseer); the executor is Gemini / Antigravity. To prevent plan drift, accidental scope contraction, or silent deviations, the executor must never directly edit `docs/MASTER_PLAN.md`.

## Decision Drivers
- Integrity of canonical documentation.
- Transparent record of why and how architectural or scientific plans change.
- Clear separation of roles between plan oversight and execution.

## Considered Options
- **Option 1: Allow any agent or developer to edit `MASTER_PLAN.md` directly**
- **Option 2: Formal proposal mechanism (`docs/proposals/PROP-####-*.md`) with Overseer approval**

## Decision Outcome
Chosen option: **Option 2: Formal proposal mechanism**.
- Any proposed change or discovered discrepancy is documented in a proposal using `docs/proposals/PROP-0000-template.md`.
- Proposals include empirical evidence, alternatives, evaluation criteria, kill criteria, and plan section impact.
- The Overseer reviews the proposal, issues a verdict, and updates `MASTER_PLAN.md` and `docs/PLAN-CHANGELOG.md` upon acceptance.
- Work on unaffected components continues while proposals are under review.

### Confirmation
`scripts/verify_phase.py` and git history verify that `docs/MASTER_PLAN.md` is not modified by executor commits.
