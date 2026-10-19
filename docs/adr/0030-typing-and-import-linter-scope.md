# ADR-0030: Typing and import-linter scope (P16 PR2 / G-05)

## Status
Accepted

## Context
MASTER_PLAN §12 and PROMPT-P16 PR2 require `mypy --strict` (or pyright strict) on core packages and `import-linter` contracts for the planned layering. Applying `--strict` to the entire monorepo (especially `vigil_ml` torch/jax modules and `apps/api`) in one PR would be a multi-thousand-line typing migration unrelated to safety gates.

## Decision
1. **`mypy --strict` is enforced in CI** on exactly:
   - `packages/vigil-core/vigil_core`
   - `packages/vigil-eval/vigil_eval`
   - `packages/vigil-ml/vigil_ml/m5.py` (explanation verifier)
2. Third-party modules without stubs (`sklearn`) are ignored via `[[tool.mypy.overrides]]` (`ignore_missing_imports = true`). `pandas-stubs` is a committed dependency.
3. **`import-linter` contracts** (in `pyproject.toml`):
   - Domain packages must not import `vigil_api`
   - `vigil_core` must not import `vigil_ml` / `vigil_eval` / `vigil_sim`
4. Expanding strict typing to `vigil_ml` (except `m5.py`), `vigil_sim`, and `apps/api` is a follow-up; until then those packages are **not** claimed typed.

## Consequences
- CI fails if the scoped mypy or import-linter contracts fail (gates that can fail — seeded violations documented in `docs/progress/P16-PR2-REPORT.md`).
- Broader typing debt remains visible and owned; this ADR records the deliberate scope cut.
