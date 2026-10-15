---
status: accepted
date: 2026-10-14
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0001. Monorepo Layout for Vigil Precision Oncology Platform

## Context and Problem Statement
The initial prototype consisted of two separate flat directories (`sentinel-backend/` and `sentinel-frontend/`) with ad-hoc dependencies, circular imports, machine-specific hardcoded paths, and no separation between clinical domain models, simulation environments, evaluation harnesses, and web clients. As specified in `docs/MASTER_PLAN.md` §9.1, Vigil requires modular, strongly-typed boundaries to support reproducible science, offline clients, multiple simulation generators, and clinical decision support.

## Decision Drivers
- Strict decoupling of pure domain contracts and clinical chemistry logic from API frameworks.
- Independent packaging of simulation laboratories (`vigil-sim`) and evaluation harnesses (`vigil-eval`) to prevent leakage into runtime production code.
- Unified tooling across Python (via `uv` workspaces) and TypeScript (via `npm` workspaces).
- Preservation of git history during directory restructuring.

## Considered Options
- **Option 1: Polyrepo (separate repositories for core, API, ML, and Web)**
- **Option 2: Flat backend/frontend directories (status quo)**
- **Option 3: Modular monorepo with `apps/` and `packages/` per MASTER_PLAN §9.1**

## Decision Outcome
Chosen option: **Option 3: Modular monorepo**, because it provides clean architectural layering (Clean Architecture / Hexagonal Architecture), allows single-command verification (`make verify-phase`), prevents circular dependency risks, and standardizes cross-module interfaces.

### Layout:
- `apps/api`: FastAPI surveillance backend
- `apps/web`: Next.js clinician workstation & patient companion PWA
- `apps/worker`: Asynchronous background task worker (reminders, audits)
- `packages/vigil-core`: Shared domain models, analyte registry, UCUM units, LOINC codes, FHIR mappers (pure Python)
- `packages/vigil-ml`: ML inference runtime, conformal calibration, feature transformers
- `packages/vigil-sim`: Mechanistic cohort simulators (G1, G2, G3)
- `packages/vigil-eval`: Evaluation harness, leakage test suite, metric calculations
- `packages/vigil-opt`: Radiotherapy scheduling optimizer
- `packages/contracts`: OpenAPI specification and client contracts

### Confirmation
Structure is verified by automated repository audits (`docs/audits/REPO-AUDIT-P0.md`) and CI workspace synchronization.
