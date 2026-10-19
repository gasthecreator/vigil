# Plan traceability and gap analysis (overseer, 2026-10-19, `main` at `64e8cb0`)

Method: the plan's own definition of "software-complete" (`MASTER_PLAN.md` §18.2) and its module map (§5), journeys (§4), architecture (§9), standards (§12), phases (§14), `ML_PROGRAM.md` studies, were each checked against the repository with commands (existence, grep, running tests, GitHub API). Items I only skimmed are marked *skimmed*. Nothing here is a maturity claim: the level stays **L0** (§18.1); L1 needs the gaps below closed **and** the owner's sign-off.

## 1. §18.2 L1 checklist
| # | Requirement | State | Evidence / gap |
|---|---|---|---|
| 1 | Every module M0–M13 meets its AC with committed evidence; kills resolved by protocol | **Mostly** | See §2. Missing: M11 change control (J8), model cards for K7/M4/M7/M10/OCR, dataset cards for T-P sets. |
| 2 | Every journey J1–J8 has a passing automated e2e | **No** | J1–J5, J7 have Playwright coverage; **J6** (M4 ladder) has API tests only, no UI/e2e; **J8** (model governance) does not exist. |
| 3 | All §15 findings closed with references | **Yes, but not recorded** | Substance closed (A3: BiLSTM gone, K4 uses forward-only encoders; A15: triage by action urgency since Phase 5b). The ledger has no A1–A17 closure table → gap G-26. |
| 4 | CI gates green; Scorecard ≥ 8; repo audit ≥3 T0–T4, ≥2 T5 | **No** | CI green. Scorecard score not measured; branch protection absent (owner). Independent audit scores below target on T1, T2, T4, T5 (`REPO-AUDIT-OVERSEER-2026-10.md`). |
| 5 | `make reproduce` regenerates all reports from a clean checkout | **Partial** | `make reproduce-ml` and the `clean-clone-reproducibility` CI job exist; no single `make reproduce` covering all reports → G-11. |
| 6 | Performance, accessibility, offline, security budgets met | **Partial** | Lighthouse (7 views) and axe in CI. **Not verified:** 10⁵ patients / 10⁷ observations on Postgres, triage p95 < 400 ms, timeline p95 < 600 ms, JS ≤ 180 KB gz, ZAP baseline (G-02, G-03, G-07, G-22). |
| 7 | Documentation complete (Diataxis) | **Partial** | Install, DR, hazard log, regulatory drafts, prereg, ADRs (29) exist. No Diataxis structure or docs-site build, no SLOs, only one runbook, no content style guide, no USABILITY folder (G-08, G-09, G-23, G-24). |
| 8 | Claims-policy CI passes; no unsupported claim | **Yes** | `check_claims`, STATUS generated, honesty sweep done in Tier 3 (*skimmed* beyond CI). |
| 9 | Owner walkthrough signed in `PROGRESS.md` | **Owner** | `make demo` + `docs/demo/OWNER-SCRIPT.md` ready. |

## 2. Modules (§5)
| Module | State |
|---|---|
| M0 platform core | Done: auth/RBAC/consent (HTTP-tested), hash-chained audit with external anchor and versioned scheme, FHIR/HL7/CSV/Excel, SSE, offline sync, field encryption. **Gaps:** only exercised on SQLite (no Postgres), no containers (G-01, G-02). |
| M1 organ profiler | Rebuilt on cited SEER distributions; model card exists. |
| M2 signal engine | Done (features, B0–B4, K3; leakage canaries). |
| M3 plausibility | Done (accepted with conditions earlier; tests green). |
| M4 test ladder | Engine + registry + API + route policy done; evidence rows sourced or excluded. **Gap:** no UI, no availability/cost feedback loop (J6), no model card (G-21, G-25). |
| M5 narrative | Verified templates, plain-language explainer. **Gap:** English only (WP4.2 asks for machine-drafted flagged translations) → decision G-27. |
| M6 guardian | Done (state machine, reminders, escalation, sandbox provider). |
| M7 RT triage | Ships the urgency ranking (ADR-0019); CP-SAT research, not promoted. Hazards H10/H16 open. No model card (G-25). `packages/vigil-opt` does not exist (scheduler lives in `vigil-ml`) → G-12. |
| M8 companion | Done (explainer, second look, bad-news gate, diary, caregiver shares, PWA, OCR with confirm gate). **Gaps:** audio read-aloud, RTL, Storybook, bundle budget (G-22). |
| M9 workstation | Done (triage, timeline, adjudication, alerts, tasks, intake, continuity, quality). |
| M10 quality audit | Done (K2/M3 detection, clinician-action attribution, k≥5, consent). No model card. |
| M11 eval/governance | Harness, VigilBench, model registry (hash-verified), model cards (most), reproducibility jobs. **Gap: drift → shadow → evaluate → promote/rollback with signed change record (J8) does not exist** (G-20). |
| M12 federated/DP | Feasibility study done (not wired, as planned). |
| M13 simulation lab | Done (G1–G3 generators, multilab, department twin). |

## 3. Studies and models (`ML_PROGRAM.md`)
S1–S10 and K1–K8: all have pre-registered, reproducible records; negative results are recorded (K4, K5 kill rules fired; K6 simulation-only; CP-SAT not promoted; M12 not wired). Open stub S-016 (K8 `ProductionEnsembleK8`) is registered, not a hidden gap. Real-data validation (L3+) is human-dependent.

## 4. Architecture/standards deviations the plan did not authorise (§9, §12)
No `infra/` (Docker/compose), no Postgres run, no `apps/worker`/`packages/vigil-opt`, no `mypy --strict`/`import-linter`/`pytest-randomly`, no coverage gate or mutation testing, no gitleaks/Semgrep/Bandit/Trivy/licence check/ZAP in CI, no MkDocs build, no release workflow with provenance, no `NOTICE`/licence inventory, no pre-commit. Each is either built in Tier 4 or recorded as an ADR deviation.

## 5. Gap register (executor: `docs/prompts/PROMPT-P16.md`)
| ID | Gap | Class |
|---|---|---|
| G-01 | Dockerfiles (multi-stage, non-root, pinned) + compose (api, web, worker, postgres) under `infra/` | build |
| G-02 | Postgres: driver, Alembic on Postgres, CI service container running the API suite | build |
| G-03 | Scale test at plan budgets on Postgres; report numbers honestly | build+measure |
| G-04 | `.pre-commit-config.yaml` (ruff, prettier/eslint, gitleaks, commit-msg) | build |
| G-05 | `mypy --strict` on core packages, `import-linter` layering contracts | build |
| G-06 | Coverage gate (≥90 % core/verifier, ≥80 % elsewhere, ratchet) and nightly mutation testing | build |
| G-07 | gitleaks, Semgrep, Bandit, Trivy, licence check, dependency-review, ZAP baseline, `pytest-randomly` in CI | build |
| G-08 | MkDocs-Material docs site in Diataxis structure, API reference from OpenAPI, build + link check in CI | build |
| G-09 | `/metrics`, tracing hooks (off by default), readiness/liveness, `SLOS.md`, alert runbooks | build |
| G-10 | Tag-triggered release workflow (SBOM, build provenance attestation, hash manifest, cosign when key exists), `NOTICE` + licence inventory, README version-claims check | build |
| G-11 | One `make reproduce` covering all reports, run in CI | build |
| G-12 | `apps/worker` and `packages/vigil-opt`: implement or ADR the deviation | decide |
| G-13 | Make `test_worker_kill_and_restart_lifecycle` deterministic; flake register | fix |
| G-14 | Dependabot: policy for merging, enable grouped updates | build |
| G-20 | **J8** model governance engine + API + tests + ADR | build |
| G-21 | **J6** M4 UI page + availability/cost feedback endpoint + e2e | build |
| G-22 | Storybook, RTL, audio read-aloud, JS bundle budget (≤180 KB gz) | build |
| G-23 | `docs/design/CONTENT.md` + test tying explainer wording to it | build |
| G-24 | `docs/clinical/USABILITY/` (scripts, consent, alert-fatigue simulation protocol + simulation report from the simulator) | build |
| G-25 | Model cards K7/M4/M7/M10/OCR; dedupe `docs/models` vs `docs/model_cards`; dataset cards METABRIC/TCGA/partner-synthetic | docs |
| G-26 | A1–A17 closure table with evidence | docs |
| G-27 | ADR: no machine-translated patient explainers ship before native review (flagged strings only) | decide |
| G-28 | ADR: SMART-on-FHIR deferred (stretch item) | decide |

## 6. Human/owner only (already in `HANDOVER.md` unless marked NEW)
Partner, ethics, DUA/DPIA, prereg ratification, clinical advisors, local-language review, signing keys, hosting. **NEW to add:** branch protection/rulesets on `main` (currently *not protected*), a second CODEOWNER or team, enable Dependabot security updates, first tagged release, OpenSSF Best Practices badge, record the Scorecard score, the §18.2-9 walkthrough sign-off.
