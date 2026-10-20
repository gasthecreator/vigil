# Vigil Release Candidate (v1.0.0-rc.2) Reproducibility Guide

**Document ID:** VIG-REL-001  
**Version:** 1.0.0-rc.2  
**Standard Compliance:** Master Plan §3, §10, §12, §18.2, Reality Rule RR1  
**Target:** Independent Evaluators, Overseers, Research Collaborators  

---

## 1. Reproduction and preservation boundary

Vigil does not claim that every historical study can be regenerated from current source. The repository distinguishes reproducible current artifacts from frozen, invalidated, or provenance-incomplete history. `scripts/verify_study_reproducibility.py` re-derives aggregates and reports from committed result records and checks explicit historical status records. It does not replay the one-time K4, K5, K6, M7, or M12 study cohorts. A green integrity check is not evidence that a historical study result is valid or reproduced from current code.

CI job `clean-clone-reproducibility` runs this verifier in a fresh checkout, checks `docs/STATUS.md`, regenerates SBOMs, and verifies a release manifest only when it belongs to the checked-out commit. Any result used for current model selection must have its own current preregistration, source/data lineage, and reproduction evidence.

### Frozen Environment Specifications
- **Operating System:** Ubuntu 22.04 / 24.04 LTS or macOS Sonoma 14+
- **Python Runtime:** Python 3.12 (managed via `uv 0.4+`)
- **Node Runtime:** Node.js 20 LTS (managed via `npm 10+`)
- **Evaluation Seeds:** Explicitly frozen random seeds (`seed=20261017` for study evaluations, `seed=42` for baseline synthetic cohort generation).

---

## 2. One-Command Full Verification Suite

From a clean checkout of `main` or the release candidate tag:

Committed release hash manifests identify one exact source commit. PR reproduction
checks verify a manifest only when its recorded `git_commit` matches `HEAD`; the
release workflow generates and verifies a fresh manifest for each tagged commit.

```bash
# 1. Install hermetic Python and Node dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --all-packages
npm ci

# 2. Run all governance and anti-fabrication gates
python3 scripts/check_claims.py
python3 scripts/check_evidence.py
python3 scripts/audit_excerpts.py
python3 scripts/reality_audit.py --require-stub-registry
python3 scripts/check_docs_links.py
python3 scripts/audit_repo_standards.py

# 3. Execute Safety Hazard Log verifier (runs all 22 cited control tests)
python3 scripts/verify_hazard_log.py

# 4. Verify derived reports and preserved study evidence without replaying frozen cohorts
python3 scripts/verify_study_reproducibility.py
python3 scripts/generate_status.py --check
```

STATUS and the release hash manifest:
```bash
python3 scripts/generate_status.py
python3 scripts/generate_sbom.py
python3 scripts/generate_release_manifest.py generate --release v1.0.0-rc.2
python3 scripts/generate_release_manifest.py verify   --release v1.0.0-rc.2
```

---

## 3. Study-specific reproduction

The commands below describe existing synthetic studies. Check each study's preregistration, result status, and access record before rerunning it. A historical result with a consumed seed must not be replayed merely to make a current-source hash match.

### Study M10-V2: Missed-Signal Quality Audit Engine
```bash
uv run python scripts/run_study_m10_audit.py
```
- **Inputs:** Mechanistic longitudinal trajectories across 5 facility archetypes.
- **Outputs:** `reports/ml/STUDY_M10_MISSED_SIGNALS.json` and `.md`.
- **Verification:** CI compares the committed deterministic report output; this is a synthetic audit, not model-performance evidence.

### Study S8-K7: Causal Inference of Delay Harm & Confounder Sensitivity
```bash
uv run python scripts/run_study_s8_k7.py
```
- **Outputs:** `reports/ml/STUDY_S8_K7_CAUSAL.json` and `.md`.
- **Expected Invariant:** Reconciles conditional parameter ($\exp(\beta) = 1.18$) with marginal risk ratios ($1.1436$ Scenario A, $1.1247$ Scenario B), E-value estimate $2.2828$.

### Study M7-TWIN: Departmental Digital Twin & Radiotherapy Triage
```bash
uv run python scripts/run_study_m7_twin.py
```
- **Outputs:** `reports/ml/STUDY_M7_DIGITAL_TWIN.json` and `.md`.
- **Expected Invariant:** 12-cell parameter sweep with 50 replications per cell; CP-SAT solver status diagnostics and plain reporting of relative policy harms.

---

## 4. End-to-End Test Pyramid Execution

Execute the full testing pyramid:

```bash
# Unit, property, and integration tests
uv run pytest tests/unit packages/ -v

# Acceptance contract suites (P4, P5, P7, P8, P9, P11, P12, P13, P14)
VIGIL_ACCEPT_P4=1 VIGIL_ACCEPT_P5=1 VIGIL_ACCEPT_P7=1 VIGIL_ACCEPT_P8=1 \
VIGIL_ACCEPT_P9=1 VIGIL_ACCEPT_P11=1 VIGIL_ACCEPT_P12=1 VIGIL_ACCEPT_P13=1 \
VIGIL_ACCEPT_P14=1 uv run pytest tests/acceptance_* -v

# Dynamic OpenAPI Security Penetration Suite (all 56 endpoints x 8 roles)
uv run pytest tests/security/test_penetration_suite.py -v

# On-prem installation and Disaster Recovery drills
uv run pytest tests/deployment/test_on_prem_install.py -v
uv run pytest tests/resilience/test_disaster_recovery.py -v
uv run pytest tests/resilience/test_load_and_soak.py -v
```

---

## 5. Artifact integrity (hash manifest, unsigned)

Verify committed release-candidate artifacts against `docs/release/RELEASE_MANIFEST_v1.0.0-rc.1.json`:

```bash
python scripts/generate_release_manifest.py verify --release v1.0.0-rc.1
```

This re-hashes every listed file and fails on a missing file or digest mismatch. The manifest is **unsigned**: it detects accidental or unnoticed change, not an attacker who can regenerate it. Signing is an owner action: see [`SIGNING.md`](SIGNING.md).
