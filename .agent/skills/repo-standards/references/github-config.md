# GitHub configuration for a hardened repo

Settings changes need admin rights and change shared state: show the user the command or setting and get a yes before applying. File additions can go on a branch.

## Branch rules (ruleset on default branch)
- Require PR before merge; required approvals >=1 (2 for team/high-risk); dismiss stale approvals on new commits; require approval of the most recent push
- Require code owner review
- Require status checks (CI, lint, tests, CodeQL) and branches up to date, or enable merge queue
- Block force pushes and deletions; apply to admins
- Require linear history (squash/rebase); optionally signed commits
- Require conversation resolution
- Restrict who can create tags matching `v*`

## Repository security features
- Dependabot alerts + security updates; secret scanning + push protection; code scanning (CodeQL default setup or advanced); private vulnerability reporting enabled; Actions default workflow permissions = read; require SHA pinning if available; 2FA required for the org.

## Workflow rules (see `assets/templates/ci.yml`)
- Top-level `permissions: contents: read`; elevate per job
- `concurrency` to cancel superseded runs; `timeout-minutes` on jobs
- Pin actions: `uses: actions/checkout@<40-char-sha> # v4.x.y`
- No `pull_request_target` checking out PR code; pass untrusted values via `env:`
- Cache dependencies; matrix for supported toolchain versions; path filters in monorepos
- Separate workflows: `ci` (PR), `codeql`, `scorecard`, `release` (tags), `nightly` (slow/e2e)
- Release: tag-triggered, builds once, attaches artifacts + SBOM + checksums, signs with cosign (keyless OIDC), generates provenance attestation, publishes release notes from CHANGELOG

## Dependabot
Weekly updates for each ecosystem and `github-actions`; group minor/patch; `cooldown` of a few days for fresh releases; label and assign. Template: `assets/templates/dependabot.yml`.

## Scorecard
Add `assets/templates/scorecard.yml`; publish results; track the badge. Key checks: Branch-Protection, Code-Review, CI-Tests, Dependency-Update-Tool, Pinned-Dependencies, SAST, Security-Policy, Token-Permissions, Dangerous-Workflow, Signed-Releases, Vulnerabilities, Maintained, License, SBOM, Fuzzing, Binary-Artifacts.

## Community profile (Insights > Community Standards)
README, CODE_OF_CONDUCT, CONTRIBUTING, LICENSE, issue templates (`.github/ISSUE_TEMPLATE/`), PR template, security policy.

## Repo metadata
Description, topics, homepage, social preview; pinned releases; archived repos marked; default branch `main`; disable unused features (wiki, projects) or use them deliberately.
