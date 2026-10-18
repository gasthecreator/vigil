# Vigil Release Candidate (v1.0.0-rc.1) Reproducibility Guide

**Document ID:** VIG-REL-001  
**Version:** 1.0.0-rc.1  
**Standard Compliance:** Master Plan §3, §10, §12, §18.2, Reality Rule RR1  
**Target:** Independent Evaluators, Overseers, Research Collaborators  

---

## 1. Overview & Hermetic Guarantee

Vigil is committed to total mathematical and bit-for-bit computational reproducibility. All scientific studies, machine learning models, simulation benchmarks, and governance audits are deterministic and execute from a clean repository checkout without internet access or manual intervention.

### Frozen Environment Specifications
- **Operating System:** Ubuntu 22.04 / 24.04 LTS or macOS Sonoma 14+
- **Python Runtime:** Python 3.12 (managed via `uv 0.4+`)
- **Node Runtime:** Node.js 20 LTS (managed via `npm 10+`)
- **Evaluation Seeds:** Explicitly frozen random seeds (`seed=20261017` for study evaluations, `seed=42` for baseline synthetic cohort generation).

---

## 2. One-Command Full Verification Suite

From a clean checkout of `main` or the release candidate tag:

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

# 4. Execute Study Reproducibility verifier (asserts bit-for-bit reproduction)
python3 scripts/verify_study_reproducibility.py
```

---

## 3. Scientific Studies Deterministic Reproduction

Each study script generates its corresponding report in `reports/ml/` without manual edits:

### Study M10-V2: Missed-Signal Quality Audit Engine
```bash
uv run python scripts/run_study_m10_audit.py
```
- **Inputs:** Mechanistic longitudinal trajectories across 5 facility archetypes.
- **Outputs:** `reports/ml/STUDY_M10_MISSED_SIGNALS.json` and `.md`.
- **Expected Invariant:** 100% bit-for-bit reproduction of all detection metrics and hypotheses (H1–H4).

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

## 5. Artifact Provenance & Checksum Verification

Verify the integrity of committed release candidate artifacts against `docs/release/RELEASE_MANIFEST_v1.0.0-rc.1.json`:

```bash
python3 -c "
import json, hashlib
with open('docs/release/RELEASE_MANIFEST_v1.0.0-rc.1.json') as f:
    manifest = json.load(f)
for path, expected_sha in manifest['artifact_checksums'].items():
    with open(path, 'rb') as af:
        actual_sha = hashlib.sha256(af.read()).hexdigest()
    assert actual_sha == expected_sha, f'Checksum mismatch in {path}'
print('All release candidate artifact checksums verified!')
"
```
