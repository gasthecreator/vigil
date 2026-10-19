# P16 PR2 report — quality gates (G-04, G-05, G-06, G-07, G-11, G-13, G-14)

> Status: SUBMITTED FOR REVIEW. Maturity stays L0. Overseer audit files and acceptance tests untouched.

## Outcome
Pre-commit, scoped `mypy --strict`, import-linter, coverage ratchet, security scanners, `make reproduce`, deterministic worker kill test, flake register, and Dependabot merge policy are wired so each gate can fail on a seeded violation and pass on the real tree.

## Evidence
| Gap | Artefact |
|---|---|
| G-04 | `.pre-commit-config.yaml` (ruff, prettier, gitleaks, conventional commit-msg) |
| G-05 | `pyproject.toml` `[tool.mypy]` + `[tool.importlinter]`, `docs/adr/0030-typing-and-import-linter-scope.md`, `.github/workflows/quality-gates.yml` job `typing-and-imports`, `make typecheck` |
| G-06 | `reports/quality/COVERAGE_RATCHET.json` (floor **88.7%**, target **90%**), `scripts/check_coverage_ratchet.py`, measured `reports/quality/coverage-core-eval.json` (**88.72%** = 967/1090), nightly `scripts/run_mutation_m5.py` → `reports/quality/MUTATION_SCORE.json` |
| G-07 | quality-gates `security-scanners` (gitleaks, Bandit, Semgrep, Trivy fs, licence), `dependency-review` job, `pytest-randomly` in lockfile, ZAP nightly `.github/workflows/zap-baseline.yml` + `docs/security/ZAP-BASELINE.md`, Trivy image nightly |
| G-11 | `make reproduce` → `scripts/reproduce.py` (study regen, STATUS check, SBOM, release manifest generate+verify); CI job `reproduce-smoke` |
| G-13 | `tests/resilience/test_worker_resilience.py` polls before SIGTERM; `docs/ops/FLAKE-REGISTER.md` F-001 |
| G-14 | `.github/dependabot.yml` groups + `docs/ops/DEPENDABOT-MERGE-POLICY.md` |

## Gate fail-then-pass (commands)
| Gate | Fail (seed) | Pass |
|---|---|---|
| Coverage | `uv run python scripts/check_coverage_ratchet.py --seed-fail` → exit 1 | measure + `check_coverage_ratchet.py --coverage-json …` |
| mypy | CI step: `mypy --strict` on `/tmp/vigil_mypy_seed.py` | `uv run mypy --config-file pyproject.toml` → 0 errors / 15 files |
| import-linter | CI step: plant `vigil_api` import under `vigil_core` | `bash scripts/run_lint_imports.sh` → 2 kept |
| Licence | `uv run python scripts/check_licences.py --seed-fail` | `check_licences.py` → ok, 0 forbidden |
| reproduce | `uv run python scripts/reproduce.py --seed-fail` | `make reproduce` |

## Numbers (script-written)
- Coverage core+eval: **88.72%** (967/1090 lines); floor 88.7; plan target 90 (not reworded).
- Mutation: local run recorded `tool_not_installed`; nightly job installs `mutmut` and writes `MUTATION_SCORE.json`.
- Bandit `-ll` on api/core/eval after B104/B608 fixes: **0 medium/high**.
- Licence: **0** forbidden SPDX/classifier hits; 3 LGPL notes (not fail).

## Deviations
1. **mypy scope** limited to vigil-core, vigil-eval, `m5.py` (ADR-0030) — not whole monorepo.
2. **`make reproduce`** covers cheap study regeneration + STATUS/SBOM/manifest; full classical ML remains `make reproduce-ml` (nightly-capable).
3. **ZAP** `fail_action: false` on local e2e profile; triage in `docs/security/ZAP-BASELINE.md` (auth-off findings expected).
4. **NOTICE / full licence inventory** remains PR3 (G-08…); this PR only ships the allowlist gate.

## Overseer notes
None yet.
