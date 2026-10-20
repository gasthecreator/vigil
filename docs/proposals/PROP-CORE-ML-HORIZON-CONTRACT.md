---
id: PROP-CORE-ML-HORIZON-CONTRACT
title: Make model horizons explicit and reconcile evaluation with the required 3/6/12-month targets
author: Codex
date: 2026-10-20
status: DRAFT
plan_version_impact: MASTER_PLAN §6.2, §14 WP2.2
---

# PROP-CORE-ML-HORIZON-CONTRACT: Explicit model target horizons

## 1. Problem Statement

`WindowedFeatureExtractor.transform_cohort` silently defaulted to 180 days, while `build_landmark_features` defaulted to 365 days. The repository's historical baseline studies explicitly use 365 days, while `MASTER_PLAN.md` defines event-risk horizons as 3, 6, and 12 months. A caller could therefore select an estimand by choosing an entry point, and the current one-horizon studies do not cover the full required horizon set.

## 2. Evidence Base

- Source definitions: `packages/vigil-ml/vigil_ml/features.py`.
- In-repository study, benchmark, partner, and test callers were inventoried with AST search. Production/study runners already pass a horizon explicitly; several contract tests relied on the 180-day default.
- `docs/MASTER_PLAN.md` §6.1 specifies `H ∈ {3, 6, 12}` months. Current `EXP-CORE-ML-001..008` source uses explicit 365-day labels and must remain historical evidence for that target only.
- No performance result was generated or changed for this proposal.

## 3. Proposed Change

Require callers to supply `horizon_days` to both feature-building entry points. For future model comparisons, preserve separate horizon-specific estimands for 3, 6, and 12 months, report metrics per horizon, and preregister all selection and evaluation choices before any frozen test access. Preserve existing 365-day studies as historical 12-month approximations; do not silently reinterpret their results as evidence for the 3- or 6-month horizons.

## 4. Considered Alternatives

- **Keep a shared 365-day default.** Reduces call-site verbosity but still hides the target and does not enforce the 3/6/12-month model contract.
- **Keep separate 180- and 365-day defaults.** Preserves convenience at the cost of entry-point-dependent labels; reject.
- **Require explicit horizons and evaluate the full prescribed set.** Makes the estimand visible and auditable, with additional preregistered result work; preferred.

## 5. Evaluation & Verification Criteria

- All feature and training entry points must identify the horizon in their call or versioned study configuration.
- Unit tests must show omission fails, and explicit 90-, 180-, and 365-day horizons produce correspondingly named, boundary-correct labels.
- The registered baseline comparison must report censor-aware, patient-disjoint metrics and uncertainty separately at 3, 6, and 12 months, with no test-driven model selection.
- Existing frozen 365-day artifacts and access logs remain byte-identical.

## 6. Kill / Rollback Criterion

Do not change the required horizon set without an overseer-approved Master Plan change. If the multi-horizon data contract cannot identify labels or censoring status at each horizon without leakage or unsupported assumptions, fail that horizon closed and document the evidence; do not substitute a convenient default.

## 7. Impact on Master Plan

This proposal does not edit the Master Plan. It requests implementation/evidence alignment with its current 3/6/12-month target definition.
