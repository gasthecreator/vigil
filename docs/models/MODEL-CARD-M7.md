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
