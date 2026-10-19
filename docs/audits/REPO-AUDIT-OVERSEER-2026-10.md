# Repo audit: Vigil (2026-10-19, commit `64e8cb0`)

Stack: Python 3.12 (uv workspace: 5 packages + FastAPI app), TypeScript (Next.js 15 web, UI package), SQLite (Postgres untested), GitHub Actions. Type: **security-sensitive / medical service + libraries + frontend** → all tiers required (rubric), plus fuzzing and signed releases.
Scope examined: file inventory (`git ls-files`, 1,008 files), root listing, `.github/` (workflows, templates, dependabot, CODEOWNERS), CI configuration and recent run results, GitHub repository settings via API (branch protection, rulesets, secret scanning), docs tree, a measured coverage run on `vigil-core` + `vigil-eval`, test inventory (598 test functions; 836 pass on `main`), grep for observability/typing/fuzzing/typing gates. *Skimmed, not verified:* ADR content quality, hazard-log entries beyond the verifier, regulatory drafts.
This audit is independent of the executor's `scripts/audit_repo_standards.py` / `REPO-AUDIT-P15.md`; I scored from evidence against the skill rubric.

## Scorecard (0–3 per item, mean per tier; target per plan §12: ≥ 3 T0–T4, ≥ 2 T5)
| Tier | Score | Target | Verdict |
|---|---|---|---|
| T0 Foundation | **2.6** | 3 | close |
| T1 Collaboration | **1.8** | 3 | **below** |
| T2 Quality gates | **2.0** | 3 | **below** |
| T3 Security & supply chain | **2.3** | 3 | below |
| T4 Operations | **1.3** | 3 | **well below** |
| T5 Maturity | **1.7** | 2 | **below** |

Itemised: T0 hazards 3 · root clean 2 · README+quickstart verified (clean-clone job) 3 · LICENSE 3 · .gitignore/.editorconfig 3 · reproducible setup 2 (uv/nvm pins, Makefile; no containers, no single `make reproduce`) · layout 2 (deviations §4 of the gap analysis).
T1 governance files 3 · CODEOWNERS 1 (single owner) · templates 2 · Conventional Commits enforced 3 (CI gate) · history 2 · **branch protection 0** (API: "Branch not protected", no rulesets).
T2 lint/format CI 3 · unit tests 3 (598 functions, behaviour + failure paths) · integration/e2e 2 (real-server Playwright, HTTP security suite; **no Postgres**) · flakes tracked 1 (one timing-flaky test, no register) · coverage 1 (measured 89 % on core, **not reported or gated in CI**) · fuzz/property 2 (5 property-test files; HL7/CSV fuzz tests; no parser fuzzing) · types 0 (no mypy/pyright/import-linter) · CI honest 3.
T3 secret scanning 2 (GitHub secret scanning + push protection enabled; no gitleaks in CI/pre-commit) · SAST 3 (CodeQL) · dependency scanning 3 (pip-audit, npm audit gate) · Dependabot 2 (configured; both open PRs were closed, none merged since the Next 15 move) · actions pinned to SHAs 3 · least-privilege permissions 3 · threat model 3 · SBOM 3 / signed releases 1 (tooling only; nothing published) · Scorecard 2 (workflow runs; score not recorded).
T4 structured logs 2 (JSON, request IDs) · metrics/tracing 0 · health 1 (`/health` only) · config via env + `.env.example` 3 · runbooks 1 (backup/restore only) · **SLOs 0** · release/rollback 2 (documented, DR drill) · **Dockerfile 0** · incident template 2 (pilot kit).
T5 ADRs 3 (29) · design docs 2 · docs by reader need 1 (not Diataxis, no build) · CHANGELOG 3 / **SemVer tags 0 (no tags)** / release notes 1 · deprecation/compat policy 2 · benchmarks & load results committed 3 · chaos/fault 2 · Best Practices badge 0 / DORA 0.

## Critical (act first)
- **`main` is unprotected** | evidence: `gh api .../branches/main/protection` → 404; `.../rulesets` → `[]` | fix (owner, needs admin): ruleset requiring PR + the 10 CI checks + code-owner review + no force-push; commands in `docs/ops/GITHUB-SETTINGS.md`. Until then every "required check" in this repo is advisory.
- No tracked secrets, dumps, keys or pickles (checked) — no critical hazard finding.

## Top gaps, ranked by trust impact / effort
1. Branch protection + second CODEOWNER (S, owner).
2. Containers + Postgres + scale test (G-01–G-03) — the production database has never been exercised (M).
3. Type/coverage/mutation/security-scanner gates (G-05–G-07) (M).
4. Observability, SLOs, alert runbooks (G-09) (M).
5. Diataxis docs site (G-08) and release workflow with provenance + first tag (G-10) (M).
6. Pre-commit (G-04), `make reproduce` (G-11) (S).

## Strengths to keep
Evidence-and-claims discipline enforced by CI; overseer-owned acceptance tests that cannot be edited by the executor; PREREG-before-results with reproducibility jobs; 29 ADRs; pinned Actions, CodeQL, pip/npm audit, SBOM; hash-chained audit with external anchor and compatibility fixtures; real-server e2e + Lighthouse + axe; honest STATUS/HANDOVER.

## Deliberately skipped (right-sizing)
SLSA L3, multi-region DR, Terraform/Helm (on-prem first; compose is enough), full DORA instrumentation (single-team).

## Upgrade plan
Executed by `docs/prompts/PROMPT-P16.md` (G-01…G-28), then re-audit. Settings changes (rulesets, Dependabot security updates, secrets) are **commands for the owner**, not applied by us.
