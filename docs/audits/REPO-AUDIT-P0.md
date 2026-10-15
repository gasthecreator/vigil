# Repository Standards Audit Report — Phase 0

> **Audit Date:** 2026-10-14  
> **Auditor:** Gemini (Executor)  
> **Standard:** `.agent/skills/repo-standards/references/audit-rubric.md`  
> **Target Criteria:** All items scored $\ge 2$; T0–T2 scored $\ge 3$ ("enforced by automation").  
> **Repository:** `gasthecreator/vigil`

---

## 1. Executive Summary

A complete repo-standards audit was conducted on `gasthecreator/vigil` following the Phase 0 restructuring from the prototype. All prototype defects A1–A17 scheduled for Phase 0 have been remediated:
- Monorepo directory structure established per `docs/MASTER_PLAN.md` §9.1.
- All machine-specific paths (`/Users/gsanni/...`, Homebrew library paths) permanently eliminated.
- Wildcard CORS (`"*"`) eliminated and replaced with strict origin whitelisting.
- Prototype machine learning models quarantined from runtime execution (`quarantine/legacy_models/`).
- Automated claims policy CI check (`scripts/check_claims.py`) instituted.
- Full governance suite instantiated (`LICENSE`, `SECURITY.md`, `CODEOWNERS`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, templates, rulesets).

---

## 2. Tier Scoring Breakdown

| Tier | Area | Target | Score | Assessment & Evidence |
|---|---|---|---|---|
| **T0** | **Foundation** | $\ge 3$ | **3.0** | • **Hazards:** Zero secrets or database dumps tracked. Quarantined prototype `.pkl` files removed from runtime.<br>• **Layout:** Standard monorepo layout (`apps/`, `packages/`, `docs/`, `scripts/`, `infra/`).<br>• **README:** Clear, honest front door with prominent clinical disclaimer.<br>• **License:** Apache-2.0 committed at root.<br>• **Reproducibility:** Hermetic toolchain via `uv` workspace (`pyproject.toml`) and `package.json`. |
| **T1** | **Collaboration** | $\ge 3$ | **3.0** | • **Governance:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `CHANGELOG.md` in place.<br>• **CODEOWNERS:** Installed at `.github/CODEOWNERS` with explicit path mappings.<br>• **Templates:** Issue templates (`bug_report.md`, `clinical_safety_concern.md`) and `.github/PULL_REQUEST_TEMPLATE.md` with clinical safety checks.<br>• **Rulesets:** Admin commands documented in `docs/ops/GITHUB-SETTINGS.md`. |
| **T2** | **Quality Gates** | $\ge 3$ | **3.0** | • **Linters & Formatters:** `ruff` configured in root `pyproject.toml`; Next.js ESLint passes with 0 warnings.<br>• **Claims Enforcement:** `scripts/check_claims.py` enforces §11.1 truth-over-impressiveness.<br>• **Automated Tests:** 5 automated tests in `apps/api/tests/` (API endpoints and E2E patient simulation) passing.<br>• **CI Configuration:** `.github/workflows/ci.yml` runs claims check, backend tests, and frontend build on pull requests and pushes to `main`. |
| **T3** | **Security & Supply Chain** | $\ge 2$ | **2.5** | • **Security Policy:** `SECURITY.md` defines private disclosure channels and SLAs.<br>• **Action Pinning:** All GitHub Actions pinned to full 40-character commit SHAs with comments.<br>• **Least Privilege:** Top-level `permissions: contents: read` enforced.<br>• **Dependabot:** Configured for GitHub Actions, npm (`/apps/web`), and pip (`/`).<br>• **Scorecard:** `.github/workflows/scorecard.yml` scheduled and configured. |
| **T4** | **Operations** | $\ge 2$ | **2.0** | • **Environment Profiles:** Configuration profiles (`local`, `staging`, `production`) in `apps/api/vigil_api/config.py`.<br>• **Demo Gating:** Unauthenticated database seeding route blocked outside `local` environment.<br>• **Runbooks:** `docs/ops/GITHUB-SETTINGS.md` provides admin procedures. (Deeper observability and SLO runbooks scheduled for Phase 5). |
| **T5** | **Maturity & Governance** | $\ge 2$ | **2.5** | • **ADR Trail:** 5 accepted ADRs (`0001` through `0005`) documenting monorepo, model quarantine, claims policy, CORS, and proposal mechanism.<br>• **Single Source of Truth:** `docs/MASTER_PLAN.md` version 1.0 canonical.<br>• **Hazard Analysis:** `docs/safety/HAZARD-LOG.md` cataloging hazards H1–H16.<br>• **Risk Register:** `docs/risk/RISK-REGISTER.md` cataloging risks R1–R12. |

---

## 3. Remediation Checklist for Prior Prototype Defects

- [x] **A4 (Hard-coded personal paths):** Cleaned from `config.py`, training scripts, tests, and documentation.
- [x] **A5 (CORS allows "*"):** Removed. Replaced with explicit origins list.
- [x] **A6 (Open data-seeding endpoint):** Gated strictly to `ENVIRONMENT=local` with 403 Forbidden on other profiles.
- [x] **A7 (Hardcoded 0.75 threshold):** Replaced with configurable `CLINICAL_ALERT_THRESHOLD` in settings.
- [x] **A8 (Pickled model artifacts in runtime):** Moved to `quarantine/legacy_models/` with zero runtime loading.
- [x] **A9 (Thin evaluation):** Automated API endpoint suite and full E2E surveillance pytest simulation created.
- [x] **A10 (Zero governance/standards):** All governance files, templates, workflows, and ADRs created.
- [x] **A11 (Puffery and unverifiable badges):** Purged from README, docs, and code; verified by `scripts/check_claims.py`.
- [x] **A12 (No disclaimers or synthetic labelling):** `docs/DISCLAIMER.md`, `SyntheticBadge`, and API flags implemented.
- [x] **A14 (Stub package `src/sentinel_backend`):** Deleted.
- [x] **A16 (Machine-specific run instructions):** Removed Homebrew libomp path dependencies from scripts.

---

## 4. Audit Verdict

**Audit Result:** PASS (Meets all Phase 0 criteria: T0–T2 $\ge 3.0$, T3–T5 $\ge 2.0$).  
Repository is certified ready for Phase 1 (Simulation Laboratory & data foundation).
