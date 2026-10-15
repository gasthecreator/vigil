# Contributing to Vigil

Thank you for contributing to **Vigil**, an open, evidence-disciplined clinical decision-support platform for breast-cancer follow-up.

Before contributing, please read:
1. `AGENTS.md` and `docs/MASTER_PLAN.md` (the canonical architectural and scientific standard).
2. `docs/DISCLAIMER.md` (our clinical and research posture).
3. Non-negotiables: **Truth over impressiveness**; **Safety first**; **No data leakage**; **Reproducibility**.

## Quickstart Setup
```bash
git clone git@github.com:gasthecreator/vigil.git
cd vigil
make setup      # Sets up uv workspace and npm dependencies
make lint       # Runs ruff, mypy, and check_claims
make test       # Runs unit and property tests
```

## Contribution Workflow
1. **Issue or Proposal First:** For non-trivial changes, open an issue or draft a proposal using `docs/proposals/PROP-0000-template.md`.
2. **Short-Lived Branches:** Create branches off `main` named `feat/<topic>`, `fix/<topic>`, `refactor/<topic>`, `docs/<topic>`.
3. **Small PRs:** Keep PRs under ~400 lines where feasible, focused on a single concern.
4. **Conventional Commits:** Write commit messages following Conventional Commits format:
   `type(scope): brief summary` (e.g., `feat(vigil-core): add LOINC mappings for hepatic panel`).
5. **Mandatory Automated Checks:**
   - Code must pass `make lint`, `make test`, and `python3 scripts/check_claims.py`.
   - Never commit secrets, personal machine paths, or ungrounded claims.
   - Any synthetic entity or output must be explicitly marked `synthetic=True`.

## Code of Conduct
All contributors and maintainers are expected to adhere to `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
