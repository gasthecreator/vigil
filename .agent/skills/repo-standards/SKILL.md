---
name: repo-standards
description: Audit, scaffold, or upgrade any repository or codebase to big-tech professional standards (Google, Microsoft, Amazon, OpenSSF, DORA, SRE). Covers repo layout, README and docs, ADRs, governance files, code review and PR hygiene, commit conventions, testing strategy, CI/CD, supply-chain security, branch protection, release engineering, observability, and incident/runbook practice. Use this skill whenever the user says "make this repo professional", "audit my repo", "does this look vibe-coded", "clean up the repo structure", "set up CI/governance/ADRs/CODEOWNERS/SECURITY.md", "production-ready", "open-source ready", "repo hygiene", or starts a new project and wants a strong foundation, even if they never name this skill.
---

# repo-standards

Bring a repository up to the bar that large engineering orgs hold themselves to. The standard is distilled from Google's *Software Engineering at Google* and eng-practices, Microsoft's Engineering Fundamentals Playbook, Amazon's Builders' Library, OpenSSF (Scorecard, Best Practices Badge, SLSA), NIST SSDF, DORA, and Google SRE. Full catalog: `references/component-catalog.md`.

## Core idea (why this matters)

A repo reads as "vibe-coded" when it has no *explained intent*: unexplained structure, decisions nobody recorded, tests that only cover the happy path, process files that are really scratch notes, and nothing proving it works. Professional repos make three things legible to a stranger: **what it is and how to run it**, **why it is built this way**, and **what stops it from breaking** (automated gates). Optimize for those three. Every rule below serves one of them.

## Modes

Pick the mode from the request. If unclear, default to **Audit** (read-only) and offer the next step.

1. **Audit**: read-only. Inventory the repo, score it against the rubric, write a report. Change nothing.
2. **Upgrade**: apply approved findings from an audit, on a new branch, in small separate commits.
3. **Scaffold**: new project; create the foundation from `assets/templates/`.
4. **Review**: apply the review checklist (`references/component-catalog.md` section 5) to a diff or PR.

## Workflow

### 1. Inventory (always first; read before you write)
- Detect stack(s) from manifests (`go.mod`, `Cargo.toml`, `package.json`, `pyproject.toml`, `pom.xml`, `Dockerfile`, k8s manifests). Mixed repos: treat each.
- List root files and top-level dirs, `.github/`, CI workflows, `docs/`, test dirs. Check `git ls-files` (not just the working tree) because tracked and ignored files differ.
- Check for hazards first: tracked secrets or `.env`, DB dumps (`*.sql`, `*.sqlite`), certs/keys (`*.pem`, `*.key`), build artifacts (`target/`, `bin/`, `dist/`, `cover.out`, `node_modules/`), binaries, large files. Also check history if the user cares: `git log --all --diff-filter=A --name-only` for the same patterns. Anything ever committed stays in history; report it as exposed and recommend rotation, never silently "fix" by deletion.
- Read the README, CONTRIBUTING, CI config, and a sample of source and tests so the report reflects reality, not file names.

### 2. Score
Use `references/audit-rubric.md`. Each item is scored 0 (absent), 1 (present but weak/stale), 2 (solid), 3 (exemplary, enforced by automation). Group into tiers so the report shows where the gap is:
- **T0 Foundation**: hazards, layout, README, license, .gitignore, build/run reproducibility
- **T1 Collaboration**: governance files, CODEOWNERS, templates, commit/PR conventions, review rules
- **T2 Quality gates**: lint/format, tests (pyramid, failure paths), CI, coverage as signal
- **T3 Security and supply chain**: SECURITY.md, secret scanning, SAST, dependency updates, pinned actions, least-privilege tokens, SBOM, signed releases
- **T4 Operations**: observability, config, runbooks, SLOs, release/rollback, incident process
- **T5 Maturity**: ADR trail, design docs, deprecation policy, benchmarks, Scorecard/Badge, DORA metrics

### 3. Report
Write the findings with `references/audit-rubric.md` format: score per tier, top gaps ranked by (impact on a stranger's trust) / (effort), and a concrete fix per gap. Be honest about what you only skimmed. Findings are leads until verified; say what you checked.

### 4. Upgrade (only after the user approves the list)
- New branch from the default branch, never commit to `main`. Match the repo's existing commit style; otherwise Conventional Commits.
- One concern per commit (structure move, docs, CI, security files separate) so each is reviewable and revertable.
- Prefer moving over deleting. Never delete user files, rewrite git history, force-push, or change branch protection/repo settings without explicit confirmation. Offer the commands for settings changes instead of silently applying them when they need admin rights.
- Use templates from `assets/templates/` but fill them with the repo's real facts (actual commands, real owners). A template with placeholders left in is worse than none.
- Verify after: build, tests, and lint still pass; links in docs resolve; CI config is valid YAML.

## Principles to apply when making judgment calls

- **Automate the rule, don't document the rule.** If a standard can be a linter, formatter, CI gate, or ruleset, make it one. Humans review what machines cannot (design, naming, intent). (Google: formatters and static analysis; Tricorder-style "<10% false positive" gating.)
- **Small, single-purpose changes.** One self-contained change per PR/commit, tests included, refactors separate from behavior changes. Around 100 lines is comfortable; ~1000 is too large.
- **Every non-trivial decision gets a short written record.** ADRs for the why, design docs before big builds, postmortems after incidents. Keep them next to the code, in review, with owners.
- **The default branch is always releasable.** Trunk-based, short-lived branches, feature flags for unfinished work, protected branch, required checks.
- **Prove it.** Badges, CI status, coverage trend, benchmark results, a threat model, a reproducible build. Claims without evidence are what "vibe-coded" looks like.
- **Right-size it.** A solo portfolio project does not need a security audit or SLSA L3. Match tier targets to project type (library, service, operator, CLI, frontend, portfolio) and say which tiers you deliberately skipped and why. Process theater is also unprofessional.
- **Docs are code.** Versioned, reviewed, owned, updated in the same change as the behavior; one canonical source per fact; remove or mark stale docs. Organize by reader need (tutorial / how-to / reference / explanation, per Diataxis).
- **Working notes are not product.** Scratch plans, agent handoffs, worklogs and AI-tool config belong in `docs/` (curated), a gitignored folder, or nowhere; the repo root is a front door.

## Gotchas
- `golang-standards/project-layout` is not official; follow go.dev/doc/modules/layout (`cmd/`, `internal/`).
- Coverage targets turn into ceilings; use coverage to find untested code, not as a score.
- Dependabot "enabled" is what Scorecard checks; merging its PRs is what actually matters.
- CODEOWNERS only enforces anything when branch protection/rulesets require code-owner review, and it must exist on the base branch.
- Pin GitHub Actions to full commit SHAs and set top-level `permissions: read-all` (or `contents: read`); grant write per job only.
- Meta-specific practices (Buck2, internal diff tooling) were not verifiable from public sources; do not cite them as fact. Stacked small changes are the transferable idea.

## References (load as needed)
- `references/component-catalog.md`: every component of a professional repo, with the why and source. Read for Audit, Review, and anything unfamiliar.
- `references/audit-rubric.md`: scoring items, tier targets by project type, report template.
- `references/stack-layouts.md`: canonical directory layouts for Go, Rust, Python, Node/TS, Kubernetes operators, polyglot monorepos.
- `references/github-config.md`: rulesets, Actions hardening, Dependabot, CodeQL, Scorecard, release automation.
- `assets/templates/`: ADR (MADR), PR template, SECURITY.md, CODEOWNERS, CONTRIBUTING, design doc, postmortem, runbook, Dependabot, CI skeleton, Scorecard workflow.
