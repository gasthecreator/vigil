# Changelog

All notable changes to **Vigil** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Monorepo architecture per `docs/MASTER_PLAN.md` §9.1 (`apps/api`, `apps/web`, `packages/vigil-core`, `packages/vigil-sim`, `packages/vigil-eval`).
- Mandatory clinical disclaimer (`docs/DISCLAIMER.md`).
- Safety hazard log v0 (`docs/safety/HAZARD-LOG.md`) cataloging hazards H1–H16.
- Risk register (`docs/risk/RISK-REGISTER.md`) with mitigations for R1–R12.
- Automated claims-policy CI validator (`scripts/check_claims.py`).
- GitHub ruleset & branch protection runbook (`docs/ops/GITHUB-SETTINGS.md`).
- Proposal workflow template (`docs/proposals/PROP-0000-template.md`).
- Architectural Decision Records:
  - ADR-0001: Monorepo layout
  - ADR-0002: Quarantining of prototype models (Defects A1, A2, A3, A8)
  - ADR-0003: Claims policy and truth reset (Defects A2, A11, A12)
  - ADR-0004: Strict CORS profiles and environment deployment controls (Defects A5, A6)
  - ADR-0005: Proposal process for Master Plan evolution

### Changed
- Renamed project from Sentinel to Vigil across all codebase modules, tests, configuration, and documentation (WP0.1).
- Purged unevidenced badges, puffery, and unverifiable metrics ("ROC-AUC 1.000", "enterprise-grade", "production-ready") from README and documentation.
- Replaced wildcard CORS (`*`) with strict environment-specific origins (`localhost:3000` for local profile).
- Removed hardcoded personal machine paths (`/Users/gsanni/...`) from default database URLs and training scripts (Defect A4).
- Gated the demo cohort seeding endpoint (`/api/v1/analytics/seed-demo-cohort`) behind `ENVIRONMENT=local` checks (Defect A6).

### Removed
- Removed empty stub package `src/sentinel_backend` (Defect A14).
- Removed pickled model artifacts (`baseline_model.pkl`, `feature_scalers.pkl`) from default runtime execution paths (Defect A8).
