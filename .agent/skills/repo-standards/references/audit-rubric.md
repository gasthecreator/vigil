# Audit rubric and report format

Score each item 0 absent · 1 present but weak/stale/unenforced · 2 solid · 3 exemplary and enforced by automation. Mark N/A with a reason; do not score what does not apply.

## Items by tier

**T0 Foundation**
- No hazards tracked (secrets, dumps, certs, binaries, artifacts) *(any tracked secret/dump = automatic critical finding)*
- Root is clean (no scratch notes, backups, tool-config clutter)
- README: purpose, quickstart verified to work, architecture, status
- LICENSE present and correct
- .gitignore complete; .editorconfig
- Reproducible setup: pinned toolchain, one-command build/test/run, task runner
- Layout follows the stack's canonical convention (`stack-layouts.md`)

**T1 Collaboration**
- CONTRIBUTING, CODE_OF_CONDUCT, SECURITY present and accurate
- CODEOWNERS present, 2+ owners per critical area, workflows owned
- Issue and PR templates
- Conventional Commits or equivalent, enforced
- History readable: meaningful messages, no "wip/fix/stuff", small PRs
- Default branch protected: PR-only, required checks, required review, no force-push

**T2 Quality gates**
- Formatter and linter enforced in CI
- Unit tests: behavior-focused, failure paths covered
- Integration/e2e tests for critical flows; test pyramid sane
- Flakes tracked; CI under ~10 min for presubmit
- Coverage reported as a signal (ratchet, not worship)
- Fuzz/property tests where input parsing exists
- CI green on default branch; status badge honest

**T3 Security and supply chain**
- Secret scanning and push protection
- SAST (CodeQL or equivalent); vulnerability scanning of dependencies
- Dependabot/Renovate configured and PRs actually merged
- Actions pinned to SHAs; least-privilege `permissions`; no dangerous triggers
- Threat model for networked or data-handling software
- SBOM and signed releases/provenance (when you publish artifacts)
- Scorecard run in CI; target score tracked

**T4 Operations** *(services/operators only)*
- Structured logging, metrics, tracing, health endpoints
- Config via environment; `.env.example`
- Runbooks linked to alerts; SLOs defined
- Release process documented; rollback tested; migrations backward-compatible
- Dockerfile hardened (multi-stage, non-root, pinned)
- Incident/postmortem template exists

**T5 Maturity**
- ADRs for significant decisions; design docs for major features
- Docs organized by reader need; one canonical source; owned and fresh
- CHANGELOG + SemVer tags + release notes
- Deprecation and compatibility policy
- Benchmarks/load results committed; chaos/fault tests if distributed
- OpenSSF Best Practices badge progress; DORA metrics observed

## Targets by project type (right-sizing)

| Project type | Required tiers | Skip or lighten |
|---|---|---|
| Portfolio/static site | T0, T1 light, T2 (lint+build), secret scan | T4, SBOM/provenance, threat model |
| Library / CLI | T0-T3, T5 (CHANGELOG, SemVer, docs) | T4 |
| Backend service / API | T0-T5 | provenance L3 |
| Infra/operator/K8s controller | T0-T5 incl. runbooks, upgrade/compat policy | none |
| Security-sensitive / DeFi / medical | all tiers, plus audit, fuzzing, SLSA L2+, signed releases | none |
| Research/prototype | T0 + README + license | everything else; label status clearly |

## Report template

```
# Repo audit: <name>  (<date>, commit <sha>)
Stack: <...>   Type: <...>   Scope examined: <what you read; what you only skimmed>

## Scorecard
T0 Foundation   x/3 avg   T1 Collaboration x/3   T2 Quality x/3
T3 Security     x/3       T4 Operations x/3      T5 Maturity x/3

## Critical (act first)
- <hazard or blocker> | evidence: <command/file> | fix: <specific>

## Top gaps, ranked by trust impact / effort
1. <gap> | why a reviewer notices | fix | effort S/M/L
...

## Strengths to keep
- ...

## Deliberately skipped (right-sizing)
- <item>: <reason>

## Proposed upgrade plan (needs approval)
Commit 1: ... Commit 2: ...  (branch: chore/repo-standards)
```

Tone: specific and evidence-based; findings are leads until verified. Credit what is already good.
