# Repo-standards audit (rubric T0-T5) — commit `22fcaeb`

> Written by `scripts/audit_repo_standards.py --write`. Do not edit by hand. Scores come from inspecting the repository; they are not self-awarded.
> Mode: online (GitHub API consulted).

Supersedes `REPO-AUDIT-P8B.md`, whose 3.00/3.00 was awarded for file presence (VERDICT-P8B defect 5).

## Scorecard (Master Plan §12 target: T0-T4 average >= 3, T5 >= 2)

| Tier | Average | Target | Result |
|---|---:|---:|---|
| T0 Foundation | 3.00 | 3.0 | MET |
| T1 Collaboration | 1.83 | 3.0 | **NOT MET** |
| T2 Quality gates | 2.14 | 3.0 | **NOT MET** |
| T3 Security & supply chain | 2.29 | 3.0 | **NOT MET** |
| T4 Operations | 2.17 | 3.0 | **NOT MET** |
| T5 Maturity | 2.83 | 2.0 | MET |

**Overall: targets NOT met for T1, T2, T3, T4.** Critical findings: none.

## Items

### T0 Foundation

| Item | Score | Evidence | Gap |
|---|:-:|---|---|
| T0.1 No hazards tracked | 3/3 | git ls-files scanned: 626 files<br>.gitignore covers db/.env/node_modules/__pycache__: True<br>tracked data artifacts: 10 files under data/synthetic/ (synthetic generator output; verify none is real patient data: dataset cards in data/dataset_cards/) | — |
| T0.2 Root is clean | 3/3 | 20 tracked root files<br>GEMINI.md is a <=10-line pointer to AGENTS.md (agent-tool shim, accepted)<br>present in the working tree but not tracked (ignored or untracked): ['vigil_dev.db', 'quarantine', '__pycache__', '.hypothesis']<br>tracked top-level dirs: ['.agent', '.github', 'apps', 'benchmarks', 'data', 'docs', 'experiments', 'packages', 'quarantine', 'reports', 'scripts', 'tests'] | — |
| T0.3 README | 3/3 | sections present: ['purpose', 'quickstart', 'architecture', 'status', 'disclaimer']<br>README `make` targets and script paths checked against Makefile/git ls-files: 0 dangling<br>quickstart execution itself is exercised by CI (reproducibility job), not by this audit | — |
| T0.4 LICENSE | 3/3 | LICENSE is the full Apache-2.0 text: True<br>license metadata declared in pyproject/CITATION/package.json: True | — |
| T0.5 .gitignore and .editorconfig | 3/3 | .gitignore missing patterns: []<br>.editorconfig tracked: True | — |
| T0.6 Reproducible setup | 3/3 | PASS: uv.lock tracked<br>PASS: package-lock.json tracked<br>PASS: python version pinned (.python-version or exact requires-python upper bound)<br>PASS: node version pinned (.nvmrc or engines)<br>PASS: task runner with setup/test/lint<br>PASS: CI installs with frozen lockfiles | — |
| T0.7 Layout follows stack convention | 3/3 | packages: ['contracts', 'ui', 'vigil-core', 'vigil-eval', 'vigil-ml', 'vigil-sim']<br>packages without manifest: []<br>python packages without tests: [] | — |

### T1 Collaboration

| Item | Score | Evidence | Gap |
|---|:-:|---|---|
| T1.1 CONTRIBUTING / CODE_OF_CONDUCT / SECURITY | 3/3 | CONTRIBUTING.md: 1684 bytes<br>CODE_OF_CONDUCT.md: 3318 bytes<br>SECURITY.md: 1985 bytes<br>problems: [] | — |
| T1.2 CODEOWNERS | 1/3 | 14 rules, distinct owners: ['@gasthecreator']<br>rules with >=2 owners: 0/14<br>workflows owned: True | single owner for everything: no independent reviewer exists for safety-critical paths (rubric asks 2+ owners per critical area) |
| T1.3 Issue and PR templates | 3/3 | PR template 1100 bytes; checklist items: 13<br>issue templates: ['.github/ISSUE_TEMPLATE/bug_report.md', '.github/ISSUE_TEMPLATE/clinical_safety_concern.md'] | — |
| T1.4 Conventional Commits enforced | 1/3 | commit-message lint config tracked: []<br>CI step that enforces it: False<br>convention documented: True | convention is documented but nothing rejects a non-conforming commit/PR title |
| T1.5 History readable | 3/3 | last 56 commit subjects: 51 conventional (91%), 0 throwaway, 0 <10 chars | — |
| T1.6 Default branch protected (PR-only, required checks, review, no force-push) | 0/3 | gh api branches/main/protection -> gh: Branch not protected (HTTP 404)<br>no rulesets | main is not protected on GitHub (owner action: docs/ops/GITHUB-SETTINGS.md) |

### T2 Quality gates

| Item | Score | Evidence | Gap |
|---|:-:|---|---|
| T2.1 Formatter and linter enforced in CI | 2/3 | PASS: ruff check in CI<br>FAIL: ruff format --check in CI<br>PASS: eslint in CI<br>FAIL: type check in CI (mypy/pyright/tsc) | missing: ruff format --check in CI; missing: type check in CI (mypy/pyright/tsc) |
| T2.2 Unit tests cover behaviour and failure paths | 3/3 | 71 python test files, 352 test functions<br>129 failure-path assertions (raises / 4xx / is False) => 0.37 per test | — |
| T2.3 Integration/e2e for critical flows | 3/3 | 4 e2e specs; 11 acceptance suites<br>PASS: playwright e2e in CI<br>PASS: acceptance suites run in CI<br>PASS: e2e specs<br>PASS: security suite in CI<br>PASS: lighthouse in CI | — |
| T2.4 Flakes tracked; presubmit CI under ~10 min | 2/3 | flake tracking artifact/policy: []<br>median CI wall time over 19 successful main runs: 4.4 min | no flake tracking |
| T2.5 Coverage reported as a signal | 0/3 | FAIL: coverage measured in CI (--cov)<br>FAIL: threshold/ratchet (fail_under / --cov-fail-under)<br>FAIL: report published as artifact/summary | missing: coverage measured in CI (--cov); missing: threshold/ratchet (fail_under / --cov-fail-under); missing: report published as artifact/summary |
| T2.6 Fuzz/property tests where input is parsed | 2/3 | 3 @given property tests across 2 files<br>input-parsing modules: ['apps/api/vigil_api/api/endpoints/batch_import.py', 'packages/contracts/contracts/loaders/metabric_loader.py', 'packages/contracts/contracts/loaders/mimic_loader.py', 'packages/contracts/contracts/loaders/pds_loader.py', 'packages/contracts/contracts/loaders/seer_loader.py', 'packages/contracts/contracts/loaders/tcga_loader.py'] | parsing modules without property/fuzz tests: ['apps/api/vigil_api/api/endpoints/batch_import.py', 'packages/contracts/contracts/loaders/metabric_loader.py', 'packages/contracts/contracts/loaders/mimic_loader.py', 'packages/contracts/contracts/loaders/pds_loader.py', 'packages/contracts/contracts/loaders/seer_loader.py', 'packages/contracts/contracts/loaders/tcga_loader.py'] |
| T2.7 CI green on default branch; badge honest | 3/3 | README workflow badges: []; pointing at missing workflows: []<br>latest ci.yml run on main: {'conclusion': 'success', 'headSha': '7e1a97516c79cf2fbc9b44ab265b67593afc5ca7', 'status': 'completed'} | — |

### T3 Security & supply chain

| Item | Score | Evidence | Gap |
|---|:-:|---|---|
| T3.1 Secret scanning and push protection | 2/3 | secret-scan step in CI: False<br>GitHub secret_scanning=enabled, push_protection=enabled | enable GitHub secret scanning + push protection and add a CI secret scan |
| T3.2 SAST and dependency vulnerability scanning | 2/3 | PASS: CodeQL analysis workflow (github/codeql-action/analyze)<br>PASS: python dependency audit (pip-audit/osv-scanner/safety)<br>FAIL: npm audit / osv for web<br>FAIL: static analysis other than ruff (bandit/semgrep) | missing: npm audit / osv for web; missing: static analysis other than ruff (bandit/semgrep) |
| T3.3 Dependabot/Renovate configured and PRs merged | 3/3 | ecosystems configured: ['github-actions', 'npm', 'pip']; missing: []<br>merged Dependabot PRs found: 3 | — |
| T3.4 Actions pinned to SHAs; least privilege; no dangerous triggers | 3/3 | 5 workflows, 28 third-party `uses:`<br>unpinned: []<br>no top-level permissions: []<br>write-all: []<br>risky triggers: []<br>unpinned remote scripts piped to a shell (curl \| sh): [] | — |
| T3.5 Threat model | 3/3 | 13867 bytes<br>PASS: assets<br>PASS: trust boundaries<br>PASS: threats (STRIDE or equivalent)<br>PASS: mitigations mapped to tests/code<br>PASS: review date | — |
| T3.6 SBOM and signed releases/provenance | 1/3 | CycloneDX SBOMs parsed with components: 2/2<br>signatures/attestations tracked: []<br>signing/provenance in CI: False<br>git tags: [] | no signed/attested release artifact exists: the release manifest is a hash manifest only (owner action: generate signing key, see docs/release/SIGNING.md) |
| T3.7 Scorecard run in CI; score tracked | 2/3 | scorecard workflow with publish_results: True<br>recorded score artifact: [] | no recorded score / target (Master Plan: >= 8) |

### T4 Operations

| Item | Score | Evidence | Gap |
|---|:-:|---|---|
| T4.1 Structured logging, metrics, tracing, health | 2/3 | PASS: structured (JSON) logging<br>PASS: request id correlation<br>PASS: health endpoints<br>FAIL: metrics endpoint<br>FAIL: tracing (OpenTelemetry) | missing: metrics endpoint; missing: tracing (OpenTelemetry) |
| T4.2 Config via environment; .env.example | 3/3 | 10 VIGIL_* environment variables read by the API<br>.env.example tracked: True<br>documented (in .env.example or install guide): 10/10 | — |
| T4.3 Runbooks linked to alerts; SLOs defined | 2/3 | runbooks: ['docs/runbooks/BACKUP_AND_RESTORE.md']<br>SLO documents: ['.agent/skills/repo-standards/assets/templates/postmortem.md', '.agent/skills/repo-standards/references/component-catalog.md', 'docs/MASTER_PLAN.md', 'docs/audits/REPO-AUDIT-P0.md']<br>alert definitions: ['apps/api/tests/test_alert_stream.py', 'apps/api/vigil_api/api/endpoints/alerts.py', 'apps/web/src/components/AlertInbox.tsx'] | 1 runbook(s);  SLO doc; alert->runbook linkage present |
| T4.4 Release process; rollback tested; migrations compatible | 3/3 | release docs: ['docs/release/COMPATIBILITY.md', 'docs/release/RELEASE_MANIFEST_v1.0.0-rc.1.json', 'docs/release/REPRODUCIBILITY.md', 'docs/release/SIGNING.md']<br>7 alembic migrations, 7 with a non-trivial downgrade<br>migration/rollback tests: ['apps/api/tests/test_migrations.py'] | — |
| T4.5 Dockerfile hardened | 0/3 | no Dockerfile tracked (on-prem install is a Python installer script) | no container image definition (Master Plan WP0.4 lists Docker/compose); installer-only distribution |
| T4.6 Incident/postmortem template | 3/3 | templates: ['.agent/skills/repo-standards/assets/templates/postmortem.md'] | — |

### T5 Maturity

| Item | Score | Evidence | Gap |
|---|:-:|---|---|
| T5.1 ADRs for significant decisions | 3/3 | 20 ADRs; duplicate numbers: []; numbering gaps: []<br>missing Status/Context/Decision: [] | — |
| T5.2 Docs organised by reader need; canonical; fresh | 3/3 | link checker passes: True (✅ All documentation links successfully resolved. Zero broken links detected.)<br>docs index present: True<br>canonical docs present: True | — |
| T5.3 CHANGELOG + SemVer tags + release notes | 2/3 | CHANGELOG has Unreleased: True; release headings: 6<br>SemVer git tags: []<br>release notes docs: ['docs/release/COMPATIBILITY.md', 'docs/release/REPRODUCIBILITY.md', 'docs/release/SIGNING.md'] | no SemVer tag exists: the release candidate has never been tagged |
| T5.4 Deprecation and compatibility policy | 3/3 | documents mentioning deprecation/compat: ['docs/MASTER_PLAN.md', 'docs/README.md', 'docs/adr/0002-quarantine-prototype-models.md', 'docs/adr/0020-audit-hash-scheme-versioning.md']<br>documents with an explicit policy section: ['docs/release/COMPATIBILITY.md'] | — |
| T5.5 Benchmarks/load results committed; fault tests | 3/3 | load results: {'reports/load/LOAD_TEST_HTTP_RESULTS.json': 'http', 'reports/load/LOAD_TEST_RESULTS.json': 'unspecified', 'reports/load/SOAK_TEST_HTTP_RESULTS.json': 'http', 'reports/load/SOAK_TEST_HTTP_RESULTS_run1_10patients.json': 'http', 'reports/load/SOAK_TEST_HTTP_RESULTS_run2_200patients_before_triage_aggregation.json': 'http', 'reports/load/SOAK_TEST_RESULTS.json': 'unspecified'}<br>fault/resilience test files: 4 | — |
| T5.6 OpenSSF Best Practices progress; DORA observed | 3/3 | OpenSSF Best Practices referenced: True<br>DORA metrics referenced: True | — |

## Gap list (items scoring < 3, ranked low score first)

- **T1.6 Default branch protected (PR-only, required checks, review, no force-push)** (0/3): main is not protected on GitHub (owner action: docs/ops/GITHUB-SETTINGS.md)
- **T2.5 Coverage reported as a signal** (0/3): missing: coverage measured in CI (--cov); missing: threshold/ratchet (fail_under / --cov-fail-under); missing: report published as artifact/summary
- **T4.5 Dockerfile hardened** (0/3): no container image definition (Master Plan WP0.4 lists Docker/compose); installer-only distribution
- **T1.2 CODEOWNERS** (1/3): single owner for everything: no independent reviewer exists for safety-critical paths (rubric asks 2+ owners per critical area)
- **T1.4 Conventional Commits enforced** (1/3): convention is documented but nothing rejects a non-conforming commit/PR title
- **T3.6 SBOM and signed releases/provenance** (1/3): no signed/attested release artifact exists: the release manifest is a hash manifest only (owner action: generate signing key, see docs/release/SIGNING.md)
- **T2.1 Formatter and linter enforced in CI** (2/3): missing: ruff format --check in CI; missing: type check in CI (mypy/pyright/tsc)
- **T2.4 Flakes tracked; presubmit CI under ~10 min** (2/3): no flake tracking
- **T2.6 Fuzz/property tests where input is parsed** (2/3): parsing modules without property/fuzz tests: ['apps/api/vigil_api/api/endpoints/batch_import.py', 'packages/contracts/contracts/loaders/metabric_loader.py', 'packages/contracts/contracts/loaders/mimic_loader.py', 'packages/contracts/contracts/loaders/pds_loader.py', 'packages/contracts/contracts/loaders/seer_loader.py', 'packages/contracts/contracts/loaders/tcga_loader.py']
- **T3.1 Secret scanning and push protection** (2/3): enable GitHub secret scanning + push protection and add a CI secret scan
- **T3.2 SAST and dependency vulnerability scanning** (2/3): missing: npm audit / osv for web; missing: static analysis other than ruff (bandit/semgrep)
- **T3.7 Scorecard run in CI; score tracked** (2/3): no recorded score / target (Master Plan: >= 8)
- **T4.1 Structured logging, metrics, tracing, health** (2/3): missing: metrics endpoint; missing: tracing (OpenTelemetry)
- **T4.3 Runbooks linked to alerts; SLOs defined** (2/3): 1 runbook(s);  SLO doc; alert->runbook linkage present
- **T5.3 CHANGELOG + SemVer tags + release notes** (2/3): no SemVer tag exists: the release candidate has never been tagged
