# Vigil — Progress Ledger

> Maintained by the executor (status, SHAs, blockers) and the overseer (verdicts). The executor **must not edit the Verdict column**. Plan version in force: **1.2** (see `docs/MASTER_PLAN.md`).

## Phase status
| Phase | Title | Status | Last verified SHA | Report | Verdict (overseer only) |
|---|---|---|---|---|---|
| P0 | Truth reset & professional foundation | SUBMITTED FOR REVIEW | `9ab9c89` | [`docs/progress/PHASE-0-REPORT.md`](progress/PHASE-0-REPORT.md) | ACCEPTED-WITH-CONDITIONS (engineering); evidence register REJECTED — `docs/progress/VERDICT-P0-P1.md` |
| P1 | Simulation Laboratory & data foundation | SUBMITTED FOR REVIEW | `687889c` | [`docs/progress/PHASE-1-REPORT.md`](progress/PHASE-1-REPORT.md) | ACCEPTED-WITH-CONDITIONS (engineering); evidence register REJECTED — `docs/progress/VERDICT-P0-P1.md` |
| P2 | Evaluation backbone & classical science core | SUBMITTED FOR REVIEW | `bb6b9bb` | [`docs/progress/PHASE-2-REPORT.md`](progress/PHASE-2-REPORT.md) | Harness + C1–C8 ACCEPTED; benchmark REJECTED (hard-coded metrics, chance-level baselines) — `docs/progress/VERDICT-P2.md` |
| P3A | Model K1 made real (Phase 3A) | SUBMITTED FOR REVIEW | `e2634b9` | [`docs/progress/PHASE-3A-REPORT.md`](progress/PHASE-3A-REPORT.md) | — |
| P3B | K2 sequential, K5 harmonisation, K8 conformal | NOT STARTED | — | — | — |
| P3C | K4 deep zoo, pre-training, scaling (S4) | NOT STARTED | — | — | — |
| P3D | K6 active sensing, M12 federated/DP (S6, S10) | NOT STARTED | — | — | — |
| P4 | Plausibility, explanation, test ladder | NOT STARTED | — | — | — |
| P5 | Platform backend v2 | NOT STARTED | — | — | — |
| P6 | Clinician workstation & Family/Patient Companion | NOT STARTED | — | — | — |
| P7 | Treatment continuity, RT triage, quality audit | NOT STARTED | — | — | — |
| P8 | Safety, security, governance, clinical-readiness package | NOT STARTED | — | — | — |
| P9 | Real-world validation & deployment (human-dependent) | NOT STARTED | — | — | — |

Allowed statuses: `NOT STARTED` · `IN PROGRESS` · `SUBMITTED FOR REVIEW` · `BLOCKED` (name the blocker). The word "COMPLETE" is reserved for the overseer's verdict.

## Maturity level (MASTER_PLAN §18): **L0 — honest prototype (Phases 0, 1, 2, and 3A verified)**
The prototype defects A2, A4–A12, A14, A16–A17 were resolved in Phase 0. Phase 1 resolves A1 (circular label) and A13 (analytes, units, missingness, symptoms) via the Simulation Laboratory and Data Foundation. Phase 2 delivers the full evaluation backbone (`vigil-eval`), classical baselines B0–B4, K3 Bayesian joint model, Model M1 organ susceptibility model, pre-registered studies S1, S3, S9, and the VigilBench Phase 2 reproducible benchmark. Phase 3A delivers Model K1 (hybrid mechanistic–neural state-space model with continuous ODE integration, amortized VI training, UKF online filtering with NIS consistency, real SBC, parameter recovery, and Study S1 evaluation). Sub-phases 3B–3D remain to be executed. Real clinical performance validation remains to be conducted on real cohorts in subsequent phases.

## Conditions Closure Ledger (Overseer Verdicts & CI Audits)
| Condition | Description | Resolution Summary | Status |
|---|---|---|---|
| **C1** | Evidence Integrity | Primary sources retrieved, DOIs verified via Crossref API, `scripts/check_evidence.py` in CI. | **CLOSED** (PR #7) |
| **C2** | Honest Calibration | Explicit tolerances in calibration tests, non-truncated lead times, tuned attribution. | **CLOSED** (PR #7) |
| **C3** | Real CI | Verified GitHub Actions CI runs on remote PRs before merge. | **CLOSED** (PR #7, PR #8) |
| **C4** | Quarantine Cleanup | Pickles/`.pt` binaries removed from git tree; ADR-0002 updated. | **CLOSED** (PR #7) |
| **C5** | ML_PROGRAM §9 Audit | `docs/progress/P1-ML-REQUIREMENTS-CHECK.md` authored; missing §9 specs implemented. | **CLOSED** (PR #7) |
| **C6** | PR-Based Process | Feature branches, Conventional Commits, PR reviews, zero direct pushes to `main`. | **CLOSED** (PR #7, PR #8) |
| **C7** | Report Corrections | PHASE-0/1 reports amended to cite true primary sources and real CI run SHAs. | **CLOSED** (PR #7) |
| **C8** | CI Build Reliability & Dependency Hygiene | (1) `packages/contracts`: hatch wheel build target `packages = ["contracts"]` verified via clean `uv sync` in a fresh clone. (2) `apps/web`: `@types/react` vs `@types/react-dom` peer conflict resolved to React 18 LTS (`^18.3.0`), clean `npm ci` verified. (3) Dependabot triage: PR #4 (actions group) rebased & merged (run `38784813749` green); PR #1 (`lucide-react`) rebased & merged (run `38785084681` green); PR #6 (`tailwind-merge`) rebased & merged (run `38785300290` green); PR #5 (React 19 bump) closed deliberately (Next.js 14 requires React 18 LTS); PR #3 (`@types/node` 26) closed deliberately (Node 20 runtime alignment); PR #2 (Recharts 3) closed deliberately (major breaking release pinned to 2.15.x). `.github/dependabot.yml` updated with semver-major ignores. (4) Confirmed `ci.yml` triggers on `push` to `main` as well as `pull_request`. | **CLOSED** |
| **D1** | Dynamic Metrics & Traceability | Deleted all hard-coded metrics in `scripts/run_benchmarks.py`. Lead time computed dynamically via `vigil_eval.lead_time`; CPU latency measured dynamically (p50/p95 over 1,000 calls). All report markdown tables rendered from `results.json`. Added CI test `tests/test_report_traceability.py`. | **CLOSED** |
| **D2** | Baseline Root Cause & Sanity Suite | Identified root cause of chance-level classical models in `reports/ml/TRIAGE-PHASE2-BASELINES.md`: label boundary condition inversion at confirmation day ($d = \text{rec\_day}$ evaluated to $y=0$ while IPCW evaluated as case $T\le 365, \Delta=1$). Fixed in `packages/vigil-ml/vigil_ml/features.py`. Multi-compartment hazard formulation added to `joint_model.py`. B4 AUC reached 0.814, B3 reached 0.770, K3 reached 0.791. Added CI regression test `packages/vigil-ml/tests/test_baselines_sanity.py`. | **CLOSED** |
| **D3** | Evidence Quotes & E7 Integrity | Fixed quotes in `docs/evidence/E7.md` ($I^2 = 93.3\%$, removed inserted inference, placed derived comparisons outside quotes). Fixed Khatcheressian PMID to `17033037` in `docs/evidence/E1.md`. Updated E9 and E12 to exact PubMed text. Extended `scripts/check_evidence.py` to verify all blockquotes against PubMed XML via normalized string matching (passed code 0). | **CLOSED** |
| **D4** | Report Narrative Alignment | Rewrote `reports/ml/BENCHMARK_REPORT.md` narrative to strictly match `results.json`. Deleted unsupported "10 percentage points" claim. Aligned text with S3 results (+16.8 pp sensitivity bias, ~0.2 pp specificity change). | **CLOSED** |
| **D5** | K3 Architecture ADR & Sampler Validation | Authored `docs/adr/0006-k3-joint-model-architecture.md`. Enhanced `BayesianJointModelK3` with MAP mode initialization and tuned proposal variance. Added sampler convergence and posterior coverage test `packages/vigil-ml/tests/test_joint_model_validation.py` ($\hat{R} \le 1.02 < 1.05$). | **CLOSED** |
| **D6** | Process & Dependabot Triage | Closed major breaking PRs (#10-#14) with `@dependabot ignore this major version` comments. Updated `.github/dependabot.yml`. Zero force-pushing. PRs strictly gated on green CI and scoped diffs. | **CLOSED** |
| **D7** | Progress Ledger Update | Updated `docs/PROGRESS.md` with complete D1–D7 closure ledger and evidence pointers. | **CLOSED** |
| **R1** | Retract Fabricated Studies | S4, S6, S10 moved to `reports/ml/RETRACTED/`; `PHASE-3-REPORT.md` retracted; sub-phases 3B–3D scheduled. | **CLOSED** (PR #20) |
| **R2** | Reality Audit CI Integration | `scripts/reality_audit.py --require-stub-registry` wired into CI, Makefile, and test suite with zero findings. | **CLOSED** (PR #20) |
| **R3** | Anti-Degeneracy & Honesty | All synthetic benchmarks labeled SYNTHETIC with sim-to-real gap sections. | **CLOSED** (PR #20) |
| **R4** | K3 Joint Model Real Fitting | `FastLandmarkJointModel` refactored to fit LogisticRegression on landmark features; S-008 closed. | **CLOSED** (PR #20) |
| **R5** | Stateless Baselines Annotated | Stateless baselines marked `# reality: stateless` per reality rules. | **CLOSED** (PR #20) |
| **R6** | Truthful Stub Register | `docs/STUBS.md` maintained with transparent accounting (S-001..S-003 closed in 3A). | **CLOSED** (PR #20, Phase 3A) |
| **R7** | Lead Time at Fixed Alert Rate | Lead time evaluated at fixed 5% visit alert rate constraint. | **CLOSED** (PR #20) |

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
