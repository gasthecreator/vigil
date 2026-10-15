# Vigil: Continuous Multimodal Oncology Surveillance

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Status: Research Prototype](https://img.shields.io/badge/Status-Research_Prototype-orange.svg)](docs/PROGRESS.md)
[![Claims Policy: Enforced](https://img.shields.io/badge/Claims_Policy-Enforced-success.svg)](scripts/check_claims.py)
[![Master Plan: v1.0](https://img.shields.io/badge/Master_Plan-v1.0_Canonical-purple.svg)](docs/MASTER_PLAN.md)

> **MANDATORY CLINICAL DISCLAIMER:** Vigil is a research prototype and decision-support aid. It is **not** a medical device, does **not** diagnose or treat any condition, and must **not** replace the clinical judgement of a qualified healthcare professional. All risk estimates and metrics in current builds are derived from synthetic benchmark data and must be treated as research demonstrations. See [`docs/DISCLAIMER.md`](docs/DISCLAIMER.md) for full safety notices.

---

## 1. Mission and Context

Vigil is an open, evidence-disciplined clinical decision-support platform designed for breast cancer follow-up in resource-constrained environments. It addresses the critical oncology "dismissal window"—the period where sub-threshold longitudinal biomarker drifts and early physiological signals are frequently dismissed as noise or lost to follow-up in overloaded healthcare centers.

Vigil honors the lived experience of breast cancer patients and caregivers by adhering to four core non-negotiable principles:
1. **Truth over impressiveness:** Zero unevidenced performance claims, zero unlabelled synthetic metrics, and full transparency about epistemic uncertainty.
2. **Safety first:** Systematic hazard mitigation (ISO 14971-aligned), explicit abstention when data are insufficient, and no false reassurance.
3. **No data leakage:** Rigorous temporal causality, clinical event horizons, and elimination of outcome-derived features.
4. **Reproducibility:** Pinned dependencies, fixed random seeds, and automated verification suites.

For the canonical product specifications, module architecture (M0–M13), and roadmap, see [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md).

---

## 2. Monorepo Architecture

Vigil is organized as a modular monorepo (`docs/MASTER_PLAN.md` §9.1):

```
vigil/
├── apps/
│   ├── api/                     # FastAPI clinical decision-support REST services (vigil_api)
│   ├── web/                     # Next.js clinician workstation & patient companion PWA
│   └── worker/                  # Background worker (reminders, drift monitoring)
├── packages/
│   ├── vigil-core/              # Domain entities, LOINC/UCUM analyte registry, FHIR mappers
│   ├── vigil-ml/                # Causal inference runtime, conformal calibration, feature transforms
│   ├── vigil-sim/               # Mechanistic cohort simulators (G1, G2, G3)
│   ├── vigil-eval/              # Evaluation harness, metric suites, leakage test canaries
│   ├── vigil-opt/               # Radiotherapy queue optimization & fairness constraints
│   └── contracts/               # OpenAPI specifications and TypeScript contracts
├── docs/                        # Canonical Diataxis documentation, ADRs, clinical evidence
├── data/                        # Dataset cards, schema definitions, and ingestion contracts
├── quarantine/                  # Quarantined legacy prototype models (DEPRECATED-INVALID-LABELS)
└── scripts/                     # Automated phase verification & claims policy CI checkers
```

---

## 3. Quickstart & Local Development

### Prerequisites
- Python 3.11+ or 3.12+ (managed via `uv`)
- Node.js v20+ and npm v10+
- GNU Make

### 1. Setup Workspace Dependencies
```bash
# Clone the repository
git clone git@github.com:gasthecreator/vigil.git
cd vigil

# Install Python workspace packages and npm dependencies
make setup
```

### 2. Verify Standards & Run Tests
```bash
# Verify claims policy (no unevidenced badges or forbidden phrases)
python3 scripts/check_claims.py

# Run backend test suite
make test

# Verify phase completion exit gates
make verify-phase PHASE=0
```

### 3. Launch Local Development Services
```bash
# Terminal 1: Start FastAPI Backend (port 8000)
make api-dev

# Terminal 2: Start Clinician Workstation (port 3000)
make web-dev
```
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- Clinician Workstation Dashboard: `http://localhost:3000`

---

## 4. Defect Remediation & Model Quarantine Status

In accordance with Phase 0 of the Master Plan, the initial prototype's models have been quarantined:
- **Defects A1 & A2 (Circular Ground Truth & Leakage):** The prototype Model B relied on circular labels derived from the synthetic generator's internal anomaly flag. These models have been removed from the default runtime path.
- **Defect A3 (Acausal BiLSTM):** Bidirectional models that process future sequence data across the evaluation window are prohibited for prospective forecasting.
- **Defect A8 (Pickle Security Vulnerability):** Serialized `.pkl` files have been permanently quarantined to `quarantine/legacy_models/` with zero runtime loading.
- **Defects A4 & A5 (Hardcoded Paths & Wildcard CORS):** Replaced with environment-driven configuration profiles (`local`, `staging`, `production`) and strict origin whitelisting.

---

## 5. Governance and Evidence

- **Single Source of Truth:** [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md)
- **Clinical Evidence Register:** [`docs/EVIDENCE.md`](docs/EVIDENCE.md)
- **Progress Ledger:** [`docs/PROGRESS.md`](docs/PROGRESS.md)
- **Safety Hazard Analysis:** [`docs/safety/HAZARD-LOG.md`](docs/safety/HAZARD-LOG.md)
- **Architectural Decisions:** [`docs/adr/`](docs/adr/)
- **Contributing Guide:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Security Policy:** [`SECURITY.md`](SECURITY.md)
