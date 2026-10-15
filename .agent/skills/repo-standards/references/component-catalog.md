# Component catalog: what a big-tech-grade repo is made of

Sources are named so you can justify a recommendation. Read the section you need.

Contents: 1 Front door and governance · 2 Structure and source · 3 Version control and change flow · 4 Documentation · 5 Code review · 6 Testing · 7 Build, CI, delivery · 8 Security and supply chain · 9 Operations and reliability · 10 Evolution and maintenance · 11 Culture and metrics · 12 Source index

---

## 1. Front door and governance

| Item | Standard | Source |
|---|---|---|
| README.md | What it is, why it exists, quickstart that works from a fresh clone, examples, architecture overview/diagram, status, links to docs. A stranger runs it in minutes. | Google OSS release guide; OpenSSF badge (basics: describe what/why, how to obtain, contribute) |
| LICENSE | Unmodified OSI license text at root (Apache-2.0 is Google's default). SPDX headers on source files where the org requires. | Google OSS; OpenSSF badge |
| CONTRIBUTING.md | How to build, test, lint, propose changes, commit/PR conventions, review expectations, test-addition policy | Google OSS; OpenSSF badge (test policy MUST) |
| CODE_OF_CONDUCT.md | Contributor Covenant; named steward | Google OSS; GitHub community profile |
| SECURITY.md | Private reporting channel, supported versions, response SLA (OpenSSF: initial response within 14 days), disclosure policy | OpenSSF badge; Scorecard Security-Policy |
| CODEOWNERS | `.github/CODEOWNERS`; `*` default then path rules; workflows dir owned | GitHub docs; Google OWNERS files |
| Issue/PR templates | `.github/ISSUE_TEMPLATE/`, `PULL_REQUEST_TEMPLATE.md` | GitHub community profile |
| CHANGELOG.md | Keep a Changelog: Unreleased on top, ISO dates, Added/Changed/Deprecated/Removed/Fixed/Security, human-written, SemVer stated | keepachangelog.com; OpenSSF badge (release notes MUST) |
| Inclusive language, no internal leaks | No confidential names/hosts/paths in code, comments or history | Google OSS release guide |
| Naming | Descriptive hyphenated repo name; no trademark use | Google OSS release guide |

## 2. Structure and source

- **Root is a front door.** Only: README, LICENSE, governance files, build/config files, and top-level directories. No scratch notes, backups, dumps, artifacts, handoff docs.
- **Entry points are thin; logic is in internal/private packages.** Go: `cmd/<bin>/main.go` + `internal/`. Rust: workspace `crates/`. Python: `src/` layout. Node: workspaces (`apps/`, `packages/`). See `stack-layouts.md`.
- **One responsibility per module/package; explicit boundaries.** Dependencies point inward/downward; no cycles. Public API small and documented; everything else private by default (Go `internal/`, Rust `pub(crate)`, Python `_private`).
- **One-version rule** inside a repo: a given dependency has one version across the repo (Google). Monorepo vs polyrepo: monorepo if components change together and share types AND you will invest in affected-only CI and ownership; else polyrepo. Even in polyrepo, aim for a consistent dependency graph.
- **Third-party code** isolated (`third_party/` or `vendor/` with LICENSE per directory) or consumed via a package manager; never copy-pasted without license.
- **Generated code** clearly marked, reproducible via a documented command, excluded from review noise.
- **Config separated from code**, environment-driven (12-factor III); `.env.example` committed, real `.env` ignored.
- **Consistent naming**, kebab-case for binaries/repos, language idioms inside. Names describe purpose; avoid `utils`/`helpers`/`common` dumping grounds.
- **Dev environment reproducible**: pinned toolchain (`.tool-versions`, `rust-toolchain.toml`, `go.mod` toolchain, `.nvmrc`), devcontainer, `.editorconfig`, one-command setup. Microsoft DevEx checklist: build, run all tests, launch end-to-end, attach a debugger, auto-install deps, local config.
- **Task runner**: Makefile/justfile/Taskfile with standard targets: `setup build test lint fmt run clean`.
- **.gitignore complete** (build output, deps, IDE, OS files, secrets, coverage). No binaries committed (Scorecard Binary-Artifacts). Large files via LFS.

## 3. Version control and change flow

- **Trunk-based development**: short-lived branches (hours to a couple of days), integrate to trunk at least daily, feature flags/branch-by-abstraction for unfinished work, avoid long-lived dev branches (DORA, Google SWE ch.16, trunkbaseddevelopment.com).
- **Release branches** only when you must patch old versions (shipped software); otherwise fix forward.
- **Protected default branch**: PR-only, required reviews (>=1, >=2 for Scorecard top tier), required status checks, up-to-date before merge or merge queue, code-owner review, no force-push/deletion, rules apply to admins, linear history (squash or rebase) optional but cleaner, signed commits optional.
- **Rulesets over legacy branch protection** where available; they stack and are visible to all (GitHub docs).
- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `perf:`, `test:`, `build:`, `ci:`, `chore:`, `!` or `BREAKING CHANGE:`), mapping to SemVer: fix=patch, feat=minor, breaking=major. Enforce with commitlint or a PR-title check.
- **Commit/PR descriptions record what AND why** (Google): imperative first line; body explains the problem, why this approach, known shortcomings; stands alone without external links. Never "fix bug", "wip", "phase 1".
- **Small changes** (Google): one self-contained change, tests included, refactor separate from behavior change, ~100 lines comfortable, ~1000 too large. Stack changes to avoid blocking.
- **Linked work items**: PRs link issues/design docs (Microsoft).
- **Semantic Versioning** + annotated git tags per release (`vX.Y.Z`); release notes human-readable; list fixed CVEs (OpenSSF).
- **Secrets never in history**; if committed, rotate and treat as exposed.

## 4. Documentation (docs as code)

- Organize by reader need, Diataxis: **tutorials** (learn), **how-to guides** (do), **reference** (look up), **explanation** (understand). One purpose per doc; do not mix types (Google ch.10).
- **Docs live in the repo**, are reviewed with code, updated in the same change as the behavior they describe, each has an owner, one canonical source per topic, stale docs removed or marked (Google).
- **ADRs** (`docs/adr/NNNN-title.md`, MADR): Context and problem, decision drivers, considered options, decision outcome + consequences, confirmation, status (proposed/accepted/rejected/deprecated/superseded by NNNN). Write one for any significant or hard-to-reverse decision; immutable once accepted, supersede instead of editing. Link from README.
- **Design docs** before major work: goals and non-goals, background, proposed design, alternatives considered with trade-offs, security/privacy/data/i18n/observability, rollout plan, open questions. Take a position; use diagrams (Google, designdocs.dev).
- **Architecture overview**: context diagram, component map (C4 level 1-2), data flow, trust boundaries, deployment view. Keep it short; link to ADRs for the why.
- **API docs**: reference generated from code (godoc, rustdoc, OpenAPI/proto), examples that compile or run in CI. Public API design guided by Google AIP principles: resource-oriented, standard methods (Get/List/Create/Update/Delete), consistent naming, pagination, filtering, structured errors, versioning, backwards compatibility, stability levels.
- **Code comments explain why, not what**; public symbols documented; TODOs have an owner or issue.
- **Runbooks** (`docs/runbooks/`): symptom, impact, diagnosis, mitigation, escalation, rollback; linked from alerts.
- **Threat model** (`docs/security/threat-model.md`): assets, trust boundaries, threats (STRIDE or similar), mitigations, residual risk.
- **Non-functional requirements** captured: availability, performance, capacity, DR, privacy, accessibility, compliance (Microsoft NFR list).
- **Onboarding doc**: first-day path, how to run tests, where things live, who owns what.
- **Working notes policy**: scratch plans/worklogs/handoffs do not live at root. Curate into ADRs/design docs, move to `docs/notes/` (or gitignore), or delete.

## 5. Code review (use as the Review-mode checklist)

Standard (Google): approve once a change definitely improves overall code health, even if imperfect; never approve something that worsens it. Technical facts beat preferences. Prefix optional polish with `Nit:`. Respond within one business day.

Look at, in order:
1. **Design**: components interact sensibly, belongs here, integrates with the system, right time to add it.
2. **Functionality**: does what the author intended and is good for users; edge cases, concurrency (races, deadlocks), error paths.
3. **Complexity**: easy to understand at every level; no speculative generality or unused flexibility.
4. **Tests**: present, in the same change, would actually fail if code broke, simple assertions, cover failure paths. Test code held to a high standard.
5. **Naming**: descriptive, not unwieldy.
6. **Comments**: explain why; remove stale ones and outdated TODOs.
7. **Style**: formatter/linter is authority; style-only reformatting separate.
8. **Consistency**: match surrounding code if no rule applies.
9. **Documentation**: build/test/usage/release changes update README/docs.
10. **Every line**: understand all human-written code; bring in a specialist for security, privacy, concurrency, accessibility, i18n.
11. **Context**: look at the whole file and system, not just the diff.
12. **Good things**: call out what was done well.

Also verify (Amazon): rollback ability, monitoring, deployment safety, test coverage of the change. Conflict resolution: consensus by guides, then synchronous discussion recorded in the PR, then escalate; do not let it stall.

AI-assisted code: review it like contractor code; the author must be able to explain every design choice; require tests and read the diff before merge.

## 6. Testing

- **Size by resources** (Google): small = single process, no sleep/IO/network; medium = multi-process, localhost only; large = multi-machine, used sparingly. Scope: unit / integration / end-to-end.
- **Pyramid**: roughly 80 unit / 15 integration / 5 e2e. Avoid the ice-cream cone and the hourglass.
- **Beyonce Rule**: if you liked it, put a test on it. Test everything you do not want to break: performance, accessibility, security, **failure handling** (injected errors, timeouts, bad input, partial failure).
- **Test behavior, not implementation.** Prefer real implementations or fakes over mocks; use stubs/interaction tests sparingly (Google ch.12-13).
- **Hermetic and deterministic**: no network, no wall clock, no shared state; fixed seeds; injectable clocks/IDs.
- **Flakiness is a bug**: quarantine with a tracked issue, fix the root cause, never blanket-retry. Target well under 1%.
- **Property-based tests and fuzzing** for parsers, serializers, protocol and security-sensitive code (Scorecard Fuzzing; OpenSSF dynamic analysis).
- **Contract tests** for service boundaries; **golden/snapshot tests** for stable outputs; **migration tests** for schema changes; **load/benchmark tests** with committed results; **chaos/fault-injection** for distributed systems; **synthetic probes** in production.
- **Coverage is a map, not a score**: use it to find untested code, measure on small tests, never treat a target as the goal. A coverage ratchet (no decrease) beats a fixed threshold.
- **Policy**: every behavior change ships with tests; reviewers block when absent (OpenSSF badge, Google culture).
- **Test data management**: fixtures versioned, no production PII, seed scripts documented (DORA).

## 7. Build, CI, delivery

- **Hermetic, reproducible builds**: pinned toolchain and dependencies, lockfiles committed (apps) or minimal-version selection (Go), builds do not depend on the network at test time (Amazon: builds run without network access).
- **CI on every PR**: format check, lint, static analysis, unit tests, build, (integration tests), security scans; fast presubmit (minutes), slower suites post-submit/nightly (Google ch.23). A red main is stop-the-line.
- **Pre-commit hooks** mirror CI for fast feedback but CI is the authority.
- **Static analysis with low noise** (Google Tricorder): show findings in review, prioritize new warnings, auto-fix when possible, disable tools with high "not useful" rates. Language set: `golangci-lint`/`govulncheck`, `clippy`+`cargo audit`+`cargo deny`, `ruff`+`mypy`/`pyright`, `eslint`+`tsc --strict`.
- **Formatter is mandatory and non-negotiable** (gofmt, rustfmt, ruff format, prettier). It ends style debates and enables large automated changes.
- **Path-filtered / affected-only CI** in monorepos; merge queue to prevent mid-air collisions.
- **Artifact promotion, not rebuild**: build once, promote the same artifact through environments; config versioned with code (Google CD).
- **Progressive delivery** (Google, Amazon): feature flags decouple deploy from release; canary or one-box first (about 10% traffic max), staged waves from small to large blast radius, bake time with automated alarm-driven rollback, deploy windows that avoid nights, weekends, Fridays-late, pipelines as code, automatic dependency updates at least weekly.
- **Separate pipelines** for app code, infra, config/flags, and OS/base images so one blocked change does not stall others (Amazon).
- **Database change management**: forward-only, backward-compatible migrations (expand, migrate, contract), numbered, reviewed, tested against real schema (DORA).
- **Containers**: multi-stage, minimal/distroless base, non-root user, pinned base digest, `.dockerignore`, healthcheck, no secrets in layers.
- **IaC** reviewed like code, plan output in PR, drift detection.
- **DORA delivery metrics** tracked: deployment frequency, lead time for changes, change failure rate, time to restore (plus reliability). Use them to find bottlenecks, not to rank people.

## 8. Security and supply chain

- **Secure by default**: least privilege, input validation at boundaries, safe defaults, memory-safe languages preferred, explicit authz on every endpoint, secrets from a manager/env, passwords salted+iterated (argon2/bcrypt/scrypt), TLS everywhere, expert-reviewed crypto only (no custom crypto) (OpenSSF badge and concise guide; OWASP ASVS/cheat sheets).
- **Threat model** and security review for sensitive changes; security-aware reviewer assigned.
- **Secrets**: never committed; secret scanning + push protection on; `.env.example` only; rotate on exposure; OIDC to cloud instead of long-lived keys in CI.
- **Dependencies**: evaluate before adding (maintenance, license, tests, compatibility promise, typosquatting check); lockfiles; automated updates (Dependabot/Renovate) with a short cooldown (~3 days) to dodge malicious fresh releases (OpenSSF guide); vulnerability scanning (`govulncheck`, `cargo audit`, `npm audit`, OSV); minimal dependency surface.
- **SAST** (CodeQL or equivalent) on PRs and schedule; **DAST/fuzzing** for exposed surfaces; fix medium+ findings promptly; no medium+ known vulns open >60 days (OpenSSF badge).
- **GitHub Actions hardening**: pin third-party actions to full SHA; default `permissions` read-only, grant per job; avoid `pull_request_target` with untrusted checkout; never interpolate untrusted `${{ github.event.* }}` into shell (use env vars); environments with required reviewers for deploy secrets; ephemeral self-hosted runners only; CODEOWNERS on `.github/workflows/` (GitHub docs, Scorecard Dangerous-Workflow, Token-Permissions).
- **Supply-chain integrity**: SBOM (SPDX or CycloneDX) as a release artifact; SLSA build provenance (L1 exists, L2 hosted+signed, L3 hardened/isolated); sign releases/images with Sigstore cosign; GitHub artifact attestations; reproducible builds when feasible; ship source with only version-controlled content.
- **Vulnerability handling**: SECURITY.md, private advisory channel, triage SLA, GitHub Security Advisories, CVE request, patched release notes list CVEs.
- **Account security**: 2FA/MFA for everyone with write access; least-privilege repo roles; no shared accounts.
- **Assurance**: OpenSSF Scorecard run in CI; OpenSSF Best Practices badge (passing, then silver, gold); periodic third-party audit for high-risk software. NIST SSDF groups the practices: prepare the organization, protect the software, produce well-secured software, respond to vulnerabilities.

## 9. Operations and reliability

- **Twelve-factor** principles for services: one codebase many deploys, explicit dependencies, config in env, backing services as attached resources, strict build/release/run separation, stateless processes, port binding, scale via processes, disposability (fast start, graceful shutdown), dev/prod parity, logs as event streams, admin tasks as one-off processes.
- **Observability** (Microsoft, Google): structured logs with correlation/trace IDs, metrics (RED/USE or golden signals: latency, traffic, errors, saturation), distributed tracing (OpenTelemetry), dashboards as code, alert on symptoms not causes, every alert has a runbook, log level changeable without redeploy, PII handling per policy.
- **Health**: liveness vs readiness endpoints, graceful degradation, timeouts, retries with backoff and jitter, circuit breakers, bulkheads, idempotency keys, rate limiting, backpressure.
- **SLIs/SLOs and error budgets** (Google SRE): choose few indicators users care about; use percentiles not averages; start loose and tighten; publish SLOs; error budget informs release pace. SLO is not SLA (no contractual consequence).
- **Launch checklist** (SRE): architecture, capacity, failure modes, client behavior, security, rollout and rollback plan, monitoring, documentation, dependencies.
- **Incident management**: severity levels, on-call, roles (incident commander, comms), status communication, **blameless postmortems** for defined triggers (user-visible downtime beyond threshold, data loss, on-call intervention such as rollback, long resolution, manual detection). Postmortem: impact, timeline, mitigation, root causes (deep enough), follow-up actions with owners and priorities; stored in a shared repo; no end-user identifiers.
- **Disaster recovery**: backups tested by restore, RPO/RTO stated, runbook.
- **Capacity and cost**: load-test results committed, headroom documented.
- **Data**: schema ownership, retention, PII inventory, migration plans.

## 10. Evolution and maintenance

- **Deprecation** (Google ch.15): code is a liability; plan for removal at design time; advisory vs compulsory (deadline + enforcement + owner); actionable and relevant warnings; incremental milestones; prevent backsliding with analyzers/annotations; discover users via code search/logs.
- **Large-scale changes**: automated codemods (Refaster/ast-grep/gofmt -r/comby), sharded into independently mergeable PRs, authorized by a short proposal, cleaned up with analyzers.
- **Dependency policy**: update continuously ("live at head" or small frequent bumps) over big-bang upgrades; Hyrum's Law reminds you observable behavior becomes the contract.
- **Compatibility policy**: SemVer, documented stability levels (alpha/beta/stable), breaking changes only in majors with migration notes.
- **Bus factor**: CODEOWNERS with 2+ owners per area, documented succession, active maintainers (OpenSSF).
- **Repo health**: stale branches pruned, issue triage cadence, security advisories monitored, archived repos marked, duplicates consolidated.

## 11. Culture and metrics (what stands behind the files)

- DORA capabilities: version control, trunk-based development, CI, CD, test automation, loosely coupled architecture, monitoring/observability, pervasive security, working in small batches, code maintainability, documentation quality, streamlined change approval (peer review over heavy gates).
- Blameless culture, fast review turnaround, documented working agreement, retrospectives with owned experiments (Microsoft).
- Rules justify their cost: each rule serves a stated goal; change rules by discussion backed by problems seen in code (Google ch.8).

## 12. Source index

- Software Engineering at Google (abseil.io/resources/swe-book): ch.8 style, 9 review, 10 docs, 11-14 testing, 15 deprecation, 16 VCS, 20 static analysis, 21 dependencies, 22 LSC, 23 CI, 24 CD
- Google eng-practices: google.github.io/eng-practices (review standard, speed, small CLs, CL descriptions, what to look for)
- Google OSS release guide: opensource.google/documentation/reference/releasing/preparing
- Google API Improvement Proposals: google.aip.dev
- Microsoft Code-With Engineering Playbook: microsoft.github.io/code-with-engineering-playbook (fundamentals checklist)
- Amazon Builders' Library: automating safe hands-off deployments
- Google SRE book: postmortem culture, service level objectives, launch checklist
- OpenSSF: Scorecard checks, Best Practices Badge criteria, Concise Guide, SLSA (slsa.dev)
- NIST SP 800-218 SSDF; DORA capabilities (dora.dev); Diataxis (diataxis.fr); MADR (adr.github.io/madr); Conventional Commits; Keep a Changelog; SemVer; Twelve-Factor; trunkbaseddevelopment.com; GitHub docs (CODEOWNERS, rulesets, Actions hardening, community profiles); go.dev/doc/modules/layout; Cargo layout; PyPA src layout
