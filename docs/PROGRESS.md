# Vigil — Progress Ledger

> Maintained by the executor (status, SHAs, blockers) and the overseer (verdicts). The executor **must not edit the Verdict column**. Plan version in force: **1.1** (see `docs/MASTER_PLAN.md`).

## Phase status
| Phase | Title | Status | Last verified SHA | Report | Verdict (overseer only) |
|---|---|---|---|---|---|
| P0 | Truth reset & professional foundation | SUBMITTED FOR REVIEW | `9ab9c89` | [`docs/progress/PHASE-0-REPORT.md`](progress/PHASE-0-REPORT.md) | — |
| P1 | Simulation Laboratory & data foundation | SUBMITTED FOR REVIEW | `PENDING_COMMIT` | [`docs/progress/PHASE-1-REPORT.md`](progress/PHASE-1-REPORT.md) | — |
| P2 | Evaluation backbone & classical science core | NOT STARTED | — | — | — |
| P3 | Advanced modelling, calibration, uncertainty, abstention | NOT STARTED | — | — | — |
| P4 | Plausibility, explanation, test ladder | NOT STARTED | — | — | — |
| P5 | Platform backend v2 | NOT STARTED | — | — | — |
| P6 | Clinician workstation & Family/Patient Companion | NOT STARTED | — | — | — |
| P7 | Treatment continuity, RT triage, quality audit | NOT STARTED | — | — | — |
| P8 | Safety, security, governance, clinical-readiness package | NOT STARTED | — | — | — |
| P9 | Real-world validation & deployment (human-dependent) | NOT STARTED | — | — | — |

Allowed statuses: `NOT STARTED` · `IN PROGRESS` · `SUBMITTED FOR REVIEW` · `BLOCKED` (name the blocker). The word "COMPLETE" is reserved for the overseer's verdict.

## Maturity level (MASTER_PLAN §18): **L0 — honest prototype (Phase 0 and Phase 1 verified)**
The prototype defects A2, A4–A12, A14, A16–A17 were resolved in Phase 0. Phase 1 resolves A1 (circular label) and A13 (analytes, units, missingness, symptoms) via the Simulation Laboratory and Data Foundation. Real clinical performance validation remains to be conducted on real cohorts in subsequent phases.

## Pending human actions (executor appends; owner resolves)
| ID | Action | Why | Draft artifact | Status |
|---|---|---|---|---|
| H-001 | Apply GitHub rulesets / branch protection / security features (needs admin) | repo-standards T1/T3 | `docs/ops/GITHUB-SETTINGS.md` (Phase 0) | OPEN |
| H-002 | Submit SEER electronic Research Data Agreement | Master Plan §7.2 / WP1.3 | `docs/data/ACCESS.md` §2 | OPEN |
| H-003 | Submit Project Data Sphere non-commercial research application | Master Plan §7.2 / WP1.3 | `docs/data/ACCESS.md` §5 | OPEN |
| H-004 | Complete CITI Training & submit PhysioNet MIMIC-IV credentialing | Master Plan §7.2 / WP1.3 | `docs/data/ACCESS.md` §6 | OPEN |

## Open blockers
_None recorded. External public datasets bounded with synthetic contracts, public dictionary schemas, and pre-drafted application dossiers._

## Decisions log (pointers to ADRs)
- ADR-0001: Monorepo layout (`apps/api`, `apps/web`, `packages/*`)
- ADR-0002: Quarantine prototype models (`quarantine/legacy_models/`)
- ADR-0003: Claims policy and truth reset (`scripts/check_claims.py`)
- ADR-0004: CORS and environment profiles
- ADR-0005: Proposal process (`docs/proposals/PROP-0000-template.md`)

## Verdict history (overseer)
_None yet._
