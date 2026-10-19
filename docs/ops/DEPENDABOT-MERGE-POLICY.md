# Dependabot merge policy (G-14)

## Grouping
Configured in `.github/dependabot.yml`:
- **github-actions:** one weekly PR (`actions` group).
- **npm** (`apps/web`) and **pip** (root): weekly PRs grouped as `minor-and-patch`; semver-major for selected packages ignored (React/Next/eslint/tailwind/typescript/recharts, etc.).

## Who merges
1. **Owner or a CODEOWNER** merges Dependabot PRs after CI is green.
2. The executor may rebase/retarget with `@dependabot rebase` comments but does not merge Dependabot without owner confirmation when the bump touches clinical/runtime paths (`apps/api`, `packages/vigil-ml`, auth/crypto).

## Required before merge
- All required CI checks green (including `postgres-api-suite` / security scanners when present).
- Diff scoped to the dependency bump (no unrelated file edits from Dependabot).
- For **major** version bumps that are not ignored: a short note in the PR (or linked ADR) that API/behaviour was smoke-tested.
- `npm audit` / `pip-audit` gates must still pass after the bump.

## Cadence
- Review open Dependabot PRs at least weekly.
- Close with `@dependabot ignore this major version` only when a breaking upgrade is deliberately deferred (record why in the close comment).

## Security updates
Enabling Dependabot **security** updates is an owner GitHub-settings action (HANDOVER / gap analysis §6). Until enabled, high/critical findings still block via `dependency-audit` CI.
