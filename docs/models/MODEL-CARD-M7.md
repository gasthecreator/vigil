# Model Card: M7 — RT urgency ranking (shipped) and CP-SAT research

**Model Identifier:** `MODEL-M7-RT-TRIAGE`  
**Model Version:** urgency ranking default; CP-SAT research opt-in  
**Date:** 2026-10-19  
**Module Reference:** `packages/vigil-ml/vigil_ml/scheduler.py`, `scheduler_research.py`  
**Governing Documents:** ADR-0019, `docs/studies/PREREG-M7-TWIN.md`, `reports/ml/STUDY_M7_DIGITAL_TWIN.json`, `experiments/EXP-M7-001/`  
**Claim status:** **Urgency ranking** is the shipped API/UI recommendation (explainable rule; simulation-compared only). **CP-SAT** is research-only, badged unvalidated; simulation showed higher harm than urgency/FCFS in committed cells.

---

## 1. Intended use
Rank radiotherapy courses for scheduling triage. Clinician confirmation required (`/schedule/confirm`). Not an optimiser guarantee; fairness bound not enforced on the default path (ADR-0019).

## 2. Shipped vs research
| Arm | Status | Notes |
|---|---|---|
| Urgency ranking | Shipped | Reasons on every assignment; synthetic twin comparison only |
| CP-SAT (`cpsat_research`) | Research | Admin / `VIGIL_ENABLE_RESEARCH_SCHEDULER=1`; promotion criterion unmet |

## 3. Hazards
H10 (RT inequity/error) and H16 (over-trust in harm model) remain open per ADR-0019.

## 4. Package layout
Scheduler code remains in `vigil-ml` (not `packages/vigil-opt`); see ADR-0031.

<!-- measured:start -->
## Measured results (script-written)

Source: `reports/ml/STUDY_M7_DIGITAL_TWIN.json` (pre-registered `docs/studies/PREREG-M7-TWIN.md`; 50 simulated replications; synthetic department, 2 linacs). Simulation only: no clinical data.

| Arm | Mean harm | Mean wait (days) | Subgroup disparity (days) |
|---|---|---|---|
| cpsat | 0.07935 | 7.09 | 1.25 |
| urgency_heuristic | 0.0188 | 13.11 | 1.82 |
| fcfs | 0.02128 | 12.72 | 1.0 |
| greedy_proxy | 0.01674 | n/a | n/a |

- H1 (CP-SAT lower harm than FCFS): **REFUTED** (mean difference -0.05807, 95% CI [-0.06892, -0.0478]).
- H2 (CP-SAT vs urgency heuristic): **URGENCY_ACHIEVES_LOWER_RAW_HARM** (mean difference -0.06055).
- Consequence: CP-SAT is research-only; the shipped default is the explainable urgency ranking.
<!-- measured:end -->
