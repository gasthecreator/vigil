# Canonical layouts by stack

Follow the language's official guidance over folklore. Always keep entry points thin and logic private by default.

## Go (go.dev/doc/modules/layout)
```
repo/
  go.mod  go.sum
  cmd/<binary>/main.go        # thin: parse flags, wire deps, run
  internal/<domain>/...       # all logic; cannot be imported by other modules
  api/                        # OpenAPI/proto definitions (if any)
  migrations/  deploy/  docs/  scripts/  test/ (e2e, fixtures)
  Makefile  .golangci.yml  Dockerfile
```
- Server/operator: no exported packages; everything in `internal/`. Export a package only if meant for others, and then consider a separate module.
- `golang-standards/project-layout` is community opinion, not official. Skip `pkg/` unless you export a stable API.
- K8s operator (kubebuilder): `api/` (CRD types), `internal/controller/`, `config/` (kustomize), `cmd/`, `test/e2e`, `hack/`. Document CRD versioning and upgrade policy.
- Tests beside code (`x_test.go`); table-driven; `testdata/`; fuzz targets `FuzzX`.

## Rust (Cargo book)
```
repo/
  Cargo.toml (workspace)  Cargo.lock (commit for binaries)  rust-toolchain.toml
  crates/<name>/{Cargo.toml, src/lib.rs|main.rs, tests/, benches/, examples/}
  deny.toml  clippy.toml  rustfmt.toml
```
- One crate per bounded concern; shared deps via `[workspace.dependencies]`; `cargo deny` + `cargo audit` + `clippy -D warnings` in CI.
- Smart contracts / on-chain code: `contracts/`, audited, with invariant/fuzz tests and a documented upgrade/pause model.

## Python (PyPA)
```
repo/
  pyproject.toml            # single source of config (ruff, mypy, pytest)
  src/<package>/            # src layout prevents accidental imports of the working tree
  tests/  docs/  scripts/
```
- Prefer `src/` layout; lock with `uv`/`pip-tools`; `ruff` (lint+format), `mypy`/`pyright`; type-hint public APIs.

## Node / TypeScript
```
repo/
  package.json (workspaces)  tsconfig.base.json  eslint.config.js
  apps/<app>/  packages/<lib>/     # apps deploy; packages are shared
  e2e/  docs/  .nvmrc
```
- `tsc --strict`; commit lockfile; no secrets in client bundles; separate `api/` and `web/` concerns; `.env.example`.
- Keep tooling config out of the root where the tool supports it (or group under `config/`).

## Polyglot monorepo
```
repo/
  apps/ services/ libs/ tools/ infra/ docs/
  .github/CODEOWNERS            # per-directory owners (Google OWNERS idea)
```
- Affected-only CI (Nx, Turborepo, Bazel, or path filters); one version per dependency; merge queue; per-directory README.

## Common top-level directories
`docs/` (adr/, architecture.md, runbooks/, security/, notes/ if kept), `deploy/` or `infra/`, `scripts/` (documented, idempotent), `migrations/`, `observability/` (dashboards, alerts as code), `test/` or `e2e/`, `.github/` (workflows, templates, CODEOWNERS, dependabot.yml), `.devcontainer/`.

## Root-clutter triage
| Found at root | Do |
|---|---|
| DB dumps, backups, `.env`, certs/keys | Hazard: untrack, gitignore, check history, rotate |
| Build artifacts (`target/`, `bin/`, `cover.out`, `dist/`) | gitignore, untrack |
| PLAN/WORKLOG/HANDOFF/FINDINGS/PROPOSALS notes | Distill decisions into ADRs; archive the rest to `docs/notes/` or remove |
| AI-tool dirs (`.cursor`, `.codex`, `.gemini`, `.agent*`) | Keep only what you intentionally share (e.g., `AGENTS.md`/`CLAUDE.md`); gitignore others |
| Duplicate repos/dirs | Pick canonical, archive other |
