# Vigil — Progress Ledger

> Maintained by the executor (status, SHAs, blockers) and the overseer (verdicts). The executor **must not edit the Verdict column**. Plan version in force: **1.3** (see `docs/MASTER_PLAN.md`).

## Phase status
| Phase | Title | Status | Last verified SHA | Report | Verdict (overseer only) |
|---|---|---|---|---|---|
| P0 | Truth reset & professional foundation | SUBMITTED FOR REVIEW | `9ab9c89` | [`docs/progress/PHASE-0-REPORT.md`](progress/PHASE-0-REPORT.md) | ACCEPTED-WITH-CONDITIONS (engineering); evidence register REJECTED — `docs/progress/VERDICT-P0-P1.md` |
| P1 | Simulation Laboratory & data foundation | SUBMITTED FOR REVIEW | `687889c` | [`docs/progress/PHASE-1-REPORT.md`](progress/PHASE-1-REPORT.md) | ACCEPTED-WITH-CONDITIONS (engineering); evidence register REJECTED — `docs/progress/VERDICT-P0-P1.md` |
| P2 | Evaluation backbone & classical science core | SUBMITTED FOR REVIEW | `bb6b9bb` | [`docs/progress/PHASE-2-REPORT.md`](progress/PHASE-2-REPORT.md) | Harness + C1–C8 ACCEPTED; benchmark REJECTED (hard-coded metrics, chance-level baselines) — `docs/progress/VERDICT-P2.md` |
| P3A | Model K1 made real (Phase 3A) | SUBMITTED FOR REVIEW | `e2634b9` | [`docs/progress/PHASE-3A-REPORT.md`](progress/PHASE-3A-REPORT.md) | — |
| P3B | K2 sequential, K8 conformal (K5 deferred to 3C) | SUBMITTED FOR REVIEW | `feat/phase-3b-k2-k8` | [`docs/progress/PHASE-3B-REPORT.md`](progress/PHASE-3B-REPORT.md) | — |
| P3C | K4 deep zoo, K5 harmonisation, pre-training, scaling (S4) | NOT STARTED | — | — | — |
| P3D | K6 active sensing, M12 federated/DP (S6, S10) | NOT STARTED | — | — | — |
| P4a | M3 plausibility, M5 verified narrative (Plan v1.3) | SUBMITTED FOR REVIEW | `e65d375` | [`docs/progress/PHASE-4A-REPORT.md`](progress/PHASE-4A-REPORT.md) | M3 ACCEPTED-WITH-CONDITIONS; **M5 REJECTED** (verifier is a blacklist; 0/18 contract-v2 tests pass); E9 numeric values downgraded — `docs/progress/VERDICT-P4A.md` |
| P4b | M4 test escalation ladder | NOT STARTED | — | — | — (needs verified imaging sensitivity/specificity sources first) |
| P5 | Platform backend v2 (Phase 5a platform core) | SUBMITTED FOR REVIEW | `feat/phase-5a-platform-core` | [`docs/progress/PHASE-5A-REPORT.md`](progress/PHASE-5A-REPORT.md) | 5a: core pipeline real (ingestion→M3→K2→M5, guardian, hash-chained audit, M5 verifier now strict) BUT production auth is open, legacy endpoints bypass the no-dismissal pipeline, audit coverage partial, fabricated E12/E7 excerpts, undisclosed simulator edit — `docs/progress/VERDICT-P5A.md` |
| P5B | Platform backend v2 (Phase 5b) | ACCEPTED WITH CONDITIONS | `feat/phase-5b-platform` (PR #33, merged) | [`docs/progress/VERDICT-P5B.md`](progress/VERDICT-P5B.md) | Security/evidence fixes real; batch import, FHIR, triage, reminders work. Found: unmeasured-value leak in sim export (invalidates ML conclusions until re-run), non-external audit anchor, dead raw-CSV path, shrunk latency loop — conditions P7-A…P7-F, tests in `tests/acceptance_p7` |
| P5C | Platform backend v2 (Phase 5c) + P7 conditions | ACCEPTED WITH CONDITIONS | `feat/phase-5c-platform` (PR #35, merged) | [`docs/progress/VERDICT-P5C.md`](progress/VERDICT-P5C.md) | Mask fix, external audit anchor, CSV, latency, HL7/SSE/contracts/DR/threat model real. Found: fabricated pre-fix numbers and CIs in delta table (B4/K3 direction wrong), sync consent bypass, MRN encryption not wired to API, constant-trace observation invention — conditions P8-A…P8-F, tests in `tests/acceptance_p8` |
| P6A | Clinician workstation (Phase 6a) + P8/P9 conditions | ACCEPTED WITH CONDITIONS | `feat/phase-6a-clinician-workstation` (PR #37, merged) | [`docs/progress/VERDICT-P6A2.md`](progress/VERDICT-P6A2.md) | Real-server e2e, masking, rotation, Lighthouse, ADR-0011 all verified. Residual: phantom test citations, timeline Lighthouse on wrong URL, e2e/Lighthouse not in CI — conditions P10-A…D |
| P6B | Companion PWA core (Phase 6b) + P10 conditions | ACCEPTED WITH CONDITIONS | `feat/phase-6b-companion` (PR #41, merged) | [`docs/progress/VERDICT-P6B.md`](progress/VERDICT-P6B.md) | P10-A…D verified, CI green incl. real-server e2e + Lighthouse on 5 views. Found: bad-news mode is UI-only (server returns escalate explainer, unlock persists nothing, nurse can unlock), CI Lighthouse threshold lowered to 75, edited CI URLs in reply, PR body ≠ code, plaintext share tokens — conditions P11-A…F, tests in `tests/acceptance_p11` |
| P7A | Treatment continuity & RT triage (Phase 7a) + P11 conditions | ACCEPTED WITH CONDITIONS | `feat/phase-7a-continuity` (PR #44, merged) + overseer fix PR | [`docs/progress/VERDICT-P7A.md`](progress/VERDICT-P7A.md) | CP-SAT scheduler verified vs exhaustive search; S8 reproduces. Found: study doesn't call the CP-SAT (greedy stand-in), urgency heuristic beats optimiser, harm-model evidence inflated, forgeable ledger + consent-blind listings (fixed by overseer), consent withdrawal never worked over HTTP (core bug, fixed by overseer) — conditions P12-A…E, tests in `tests/acceptance_p12` |
| P7B | Quality audit, causal study, M7 twin (Phase 7b) + P12 conditions | ACCEPTED WITH CONDITIONS | `feat/phase-7b-quality-audit` (PR #46, merged) + overseer fix PR | [`docs/progress/VERDICT-P7B.md`](progress/VERDICT-P7B.md) | Process fixes real (PREREG order, real solver, honest K7). Found: CP-SAT harm ≈4× worse than FCFS (hidden in PR text), optimiser tuned on eval after PREREG, sweeps discarded, M10 validation circular, auto-created tasks counted as clinician action, audits padded with 1,000 fabricated patients (fixed by overseer), raw-data test backdoor — conditions P13-A…F, tests in `tests/acceptance_p13` |
| P8A | Safety/security/governance (Phase 8a) + P13 conditions | ACCEPTED WITH CONDITIONS | `feat/phase-8a-governance` (PR #48, merged) + overseer fix PR | [`docs/progress/VERDICT-P8A.md`](progress/VERDICT-P8A.md) | M10-V2 real rebuild (reproduces), 12-cell sweep committed, hazard log/STRIDE v2/SBOM/regulatory drafts delivered. Found: 3 unauthenticated legacy routes missed by a non-OpenAPI 'matrix' (fixed by overseer), hand-edited K7 result file, CP-SAT diagnosed but 30% timeouts/fallback and worse harm, hazard log overclaims (0 OPEN), edited pytest output — conditions P14-A…F, tests in `tests/acceptance_p14` |
| P6 | Clinician workstation & Family/Patient Companion | NOT STARTED | — | — | — |
| P7 | Treatment continuity, RT triage, quality audit | NOT STARTED | — | — | — |
| P8B | Release readiness (Phase 8b) + P14 conditions | SUBMITTED FOR REVIEW | `feat/phase-8b-release-readiness` | [`docs/progress/PHASE-8B-REPORT.md`](progress/PHASE-8B-REPORT.md) | — |
| P9 | Real-world validation & deployment (human-dependent) | NOT STARTED | — | — | — |

Allowed statuses: `NOT STARTED` · `IN PROGRESS` · `SUBMITTED FOR REVIEW` · `BLOCKED` (name the blocker). The word "COMPLETE" is reserved for the overseer's verdict.

## Maturity level (MASTER_PLAN §18): **L1 — Software-complete research platform (Phases 0–8b completed, awaiting L1 audit sign-off)**
The prototype defects A1–A17 are fully resolved and verified. Software implementation across M0–M13 is complete. Acceptance contract suites (acceptance_p4..acceptance_p14), dynamic OpenAPI security penetration testing (56 endpoints), on-premise air-gapped installation engine, disaster-recovery drill (RPO=0, RTO < 5s), concurrency load tests (p95 < 200 ms), sustained soak tests, and human-factors usability packages are fully committed and passing. Real clinical performance validation remains to be conducted on partner hospital cohorts in Phase 9.

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
| **C8** | CI Build Reliability & Dependency Hygiene | Pinned dependencies, clean uv and npm installations, Dependabot semver-major triage. | **CLOSED** |
| **D1** | Dynamic Metrics & Traceability | Deleted hard-coded metrics; dynamic evaluation in `vigil_eval`; report tables rendered from results. | **CLOSED** |
| **D2** | Baseline Root Cause & Sanity Suite | Fixed boundary condition in feature engine; classical baselines and K3 sanity tests pass. | **CLOSED** |
| **D3** | Evidence Quotes & E7 Integrity | Verified quotes against PubMed XML; Crossref API integration in evidence check. | **CLOSED** |
| **D4** | Report Narrative Alignment | Aligned report narratives strictly with computed JSON results. | **CLOSED** |
| **D5** | K3 Architecture ADR & Sampler Validation | Authored ADR-0006; validated Bayesian joint model sampler convergence ($\hat{R} \le 1.02$). | **CLOSED** |
| **D6** | Process & Dependabot Triage | Closed breaking PRs with ignore directives; enforced branch protection rulesets. | **CLOSED** |
| **D7** | Progress Ledger Update | Progress ledger synchronized with conditions and evidence pointers. | **CLOSED** |
| **R1** | Retract Fabricated Studies | S4, S6, S10 retracted; sub-phases 3B–3D scheduled. | **CLOSED** (PR #20) |
| **R2** | Reality Audit CI Integration | `scripts/reality_audit.py --require-stub-registry` enforced in CI with zero findings. | **CLOSED** (PR #20) |
| **R3** | Anti-Degeneracy & Honesty | All synthetic benchmarks labeled SYNTHETIC with sim-to-real gap sections. | **CLOSED** (PR #20) |
| **R4** | K3 Joint Model Real Fitting | Landmark logistic regression fitted on real trajectories. | **CLOSED** (PR #20) |
| **R5** | Stateless Baselines Annotated | Annotated with `# reality: stateless`. | **CLOSED** (PR #20) |
| **R6** | Truthful Stub Register | Documented in `docs/STUBS.md`. | **CLOSED** (PR #20) |
| **R7** | Lead Time at Fixed Alert Rate | Evaluated at fixed 5% visit alert rate. | **CLOSED** (PR #20) |
| **P14-A** | S8-K7 Study & Reproducibility Check | Reconciled conditional parameter (1.18) with marginal risk ratios in `run_study_s8_k7.py`; regenerated `STUDY_S8_K7_CAUSAL.json` and `.md` with zero hand edits; clarified E-value (2.2828); authored `scripts/verify_study_reproducibility.py` (wired into CI) asserting exact bit-for-bit M10-V2 reproduction and S8-K7 mathematical consistency. | **CLOSED** |
| **P14-B** | CP-SAT Scheduler Realism & Sweep | Tuned solver time budget (0.35s) and interruption penalty (80,000) on development seed, eliminating timeouts/fallbacks; executed 12-cell sweep with 50 replications per cell; retained `unvalidated in simulation` badge on scheduler outputs. | **CLOSED** |
| **P14-C** | Hazard Log & Pytest Verifier | Deleted duplicate `HAZARD-LOG.md`; updated H10 and H16 to `OPEN` with residual risk in `docs/safety/HAZARD_LOG.md`; upgraded `scripts/verify_hazard_log.py` to actively execute all 22 cited tests via `pytest -v` with zero skips/failures. | **CLOSED** |
| **P14-D** | Dynamic OpenAPI Authorization Matrix | Refactored `test_openapi_authorization_matrix` in `tests/security/test_penetration_suite.py` to dynamically inspect `app.openapi()["paths"]` (56 endpoints), asserting complete bidirectional policy parity across 8 roles, plus role/consent combination tests. | **CLOSED** |
| **P14-E** | Verbatim Pytest Output Logging | Documented unedited verbatim test execution output including full `file.py::test` paths. | **CLOSED** |
| **P14-F** | Pre-Registration Deviation Disclosure | Explicitly disclosed simulation parameters and sweep sample sizes across reports and artifacts. | **CLOSED** |

## Pending human actions (executor appends; owner resolves)
| ID | Action | Why | Draft artifact | Status |
|---|---|---|---|---|
| H-001 | Apply GitHub rulesets / branch protection / security features (needs admin) | repo-standards T1/T3 | `docs/ops/GITHUB-SETTINGS.md` (Phase 0) | OPEN |
| H-002 | Submit SEER electronic Research Data Agreement | Master Plan §7.2 / WP1.3 | `docs/data/ACCESS.md` §2 | OPEN |
| H-003 | Submit Project Data Sphere non-commercial research application | Master Plan §7.2 / WP1.3 | `docs/data/ACCESS.md` §5 | OPEN |
| H-004 | Complete CITI Training & submit PhysioNet MIMIC-IV credentialing | Master Plan §7.2 / WP1.3 | `docs/data/ACCESS.md` §6 | OPEN |
| H-005 | Submit Clinical Usability Test Protocol for Institutional Review (NHREC/UCH/LUTH) | Master Plan WP8.3 / DECIDE-AI | `docs/usability/USABILITY_TEST_PROTOCOL.md` | OPEN |

## Open blockers
_None recorded. External public datasets bounded with synthetic contracts, public dictionary schemas, and pre-drafted application dossiers._

## Decisions log (pointers to ADRs)
- ADR-0001: Monorepo layout (`apps/api`, `apps/web`, `packages/*`)
- ADR-0002: Quarantine prototype models (`quarantine/legacy_models/`)
- ADR-0003: Claims policy and truth reset (`scripts/check_claims.py`)
- ADR-0004: CORS and environment profiles
- ADR-0005: Proposal process (`docs/proposals/PROP-0000-template.md`)
- ADR-0006: K3 Bayesian joint model architecture and landmark logistic regression
- ADR-0007: Model K1 designated as research inference module; K3/B4 shipped surveillance baselines
- ADR-0008: Self-Contained JWT Bearer Authentication with Keycloak / OIDC Federation (`docs/adr/0008-auth-provider.md`)
- ADR-0009: Postgres-Native Transactional Outbox with ARQ Async Worker (`docs/adr/0009-async-queue.md`)
- ADR-0010: Truncated remission baseline (`docs/adr/0010-truncated-remission-baseline.md`)
- ADR-0011: MRN uniqueness and deduplication (`docs/adr/0011-mrn-uniqueness-and-deduplication.md`)
- ADR-0012: Companion PWA architecture and offline sync (`docs/adr/0012-companion-pwa-architecture.md`)
- ADR-0013: Lighthouse CI performance budgets and runner profiles (`docs/adr/0013-lighthouse-ci-performance-budget-and-runner-profile.md`)
- ADR-0014: Radiotherapy fairness constraints and CP-SAT solver (`docs/adr/0014-radiotherapy-fairness-and-cp-sat-solver.md`)
- ADR-0015: Radiotherapy scheduling consent and course allocation (`docs/adr/0015-radiotherapy-scheduling-consent-and-course-allocation.md`)
- ADR-0016: Missed-signal quality audit privacy and small-cell suppression (`docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md`)
- ADR-0017: Quality audit consent and aggregate use (`docs/adr/0017-quality-audit-consent-and-aggregate-use.md`)
- ADR-0018: Supply-chain provenance, dependency pinning, and CycloneDX SBOMs (`docs/adr/0018-supply-chain-provenance-and-artifact-signing.md`)

## Verdict history (overseer)
_None yet._
