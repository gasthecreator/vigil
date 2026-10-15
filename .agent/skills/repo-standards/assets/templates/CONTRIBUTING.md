# Contributing

Thanks for helping. This page is the shortest path from clone to merged change.

## Setup
```bash
git clone <repo> && cd <repo>
make setup      # installs pinned toolchain deps and git hooks
make test       # must pass on a fresh clone
```

## Workflow
1. Open or claim an issue; for non-trivial work write a short design doc or ADR first (`docs/adr/`).
2. Branch from `main`: `feat/<topic>`, `fix/<topic>`. Keep branches short-lived.
3. Keep changes small and single-purpose; refactors in separate PRs; include tests.
4. Run `make lint test` locally. CI runs the same checks.
5. Open a PR using the template. Describe what and why, not just what.
6. Address review comments; `Nit:` comments are optional. Reviewers respond within one business day.

## Commit messages (Conventional Commits)
`type(scope): imperative summary`, with `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`. Use `!` or a `BREAKING CHANGE:` footer for breaking changes. Body explains why.

## Standards
- Formatter and linter are authoritative (`make fmt lint`).
- New behavior needs tests, including failure paths. Bug fixes start with a failing test.
- Public API changes update docs and CHANGELOG.
- No secrets, no generated or build artifacts, no large binaries.

## Reporting bugs and security issues
Bugs: use the issue template. Vulnerabilities: see SECURITY.md (private report).
