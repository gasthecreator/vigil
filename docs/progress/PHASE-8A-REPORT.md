# Vigil Phase 8a Progress & Governance Report

**Deliverable:** Phase 8a Safety Engineering, Security Hardening, and Regulatory Documentation  
**Branch:** `feat/phase-8a-governance`  
**Governing Documents:** `docs/progress/VERDICT-P7B.md`, `docs/MASTER_PLAN.md` §3, §6.7, §6.10, §11, and Phase 8  

---

## 1. Executive Summary & Status

Phase 8a delivers the complete Clinical Safety, Security, and Governance package for the Vigil Precision Oncology Platform, resolving all Overseer Verdict P7B conditions (P13-A through P13-F) and completing Work Packages WP8.1 and WP8.2.

Key achievements in this phase:
1. **P13-A (CP-SAT Harm Diagnosis & 12-Cell Sweep):** Completely decomposed simulated harm across waiting, interruption, and unscheduled penalty. Proved root cause of the 4.8× harm gap (daily interruption penalty is 20–50× more damaging than initial wait penalty; rolling 7-day lookahead initiates patients without machine downtime reservations). Calculated objective-vs-realised harm correlation ($r = 0.0657$). Ran and committed all 12 cells ($\lambda \in \{2, 2.5, 3, 3.5\} \times \text{MTTR} \in \{3, 7, 14\}$). Prominently badged `"unvalidated in simulation"` across web UI and API responses.
2. **P13-B, C, D, F (M10 Audit Engine Decoupling & Governance):** Rebuilt M10 audit detection on real independent K2 sequential recurrence and M3 plausibility engines without shared simulation signals. Redefined clinician action attribution strictly to verified `AlertAcknowledgement` and completed `FollowUpTask`. Removed `expose_raw_for_testing`. Enforced patient consent filtering in retrospective audits (ADR 0017). Wired `tests/acceptance_p13` into CI.
3. **P13-E (Study S8-K7 H3 Reframe):** Reframed observational causal analysis to state accurately that unmeasured confounding cannot be ruled out and quantified vulnerability using Ding & VanderWeele E-values.
4. **WP8.1 Item 1 (Hazard Log v1):** Authored `docs/safety/HAZARD_LOG.md` (and `HAZARD-LOG.md`) cataloguing 22 clinical hazards (H1..H22). Delivered AST test verifier (`scripts/verify_hazard_log.py`) and wired into CI.
5. **WP8.1 Item 2 (STRIDE Threat Model v2):** Authored `docs/security/THREAT_MODEL.md` v2.0.0 expanding to 4 trust boundaries, 8 security roles, and 24 STRIDE threats with mapped test verifications.
6. **WP8.1 Item 3 (Automated Penetration Test Suite):** Delivered `tests/security/test_penetration_suite.py` with 9 automated tests covering authorization matrix (8 roles), HTTP consent lifecycle, SQLi/parameter fuzzing, companion token security, offline sync replay idempotency, HL7 v2 fuzzing, and error leakage hygiene.
7. **WP8.1 Item 4 (Supply Chain Governance):** Delivered `docs/security/VULNERABILITY_POLICY.md` (ISO 29147/30111), ADR 0018, automated CycloneDX v1.5 SBOM generator (`scripts/generate_sbom.py`), and committed Python/NPM SBOMs.
8. **WP8.2 Item 5 (Regulatory Documentation Set):** Authored full regulatory suite under `docs/regulatory/` (`INTENDED_USE.md`, `DPIA.md`, `PCCP.md`, `CLINICAL_EVALUATION_PLAN.md`, `RISK_MANAGEMENT_FILE.md`), all carrying the required `DRAFT-UNREVIEWED` banner.

---

## 2. Verdict P7B Conditions Checklist (P13-A .. P13-F)

| Condition | Status | Implementation Summary & Evidence |
|---|---|---|
| **P13-A** | **DONE** | Diagnosed CP-SAT harm gap: interruption harm accounts for 99.2% of CP-SAT harm. Solver status counts: 50 OPTIMAL, 0 FEASIBLE, 0 TIMEOUT, 0 INFEASIBLE, 0 FALLBACK. Correlation $r = 0.0657$. Committed all 12 sweep cells in `reports/ml/STUDY_M7_DIGITAL_TWIN.json` and `.md`. Badged `"unvalidated in simulation"` on UI (`apps/web/src/app/continuity/page.tsx`) and API (`ScheduleSolveResponse`). |
| **P13-B** | **DONE** | Rebuilt M10 missed signal detection: runs decoupled K2 sequential Bayes and M3 plausibility on trajectory observations instead of inspecting generator labels. |
| **P13-C** | **DONE** | Clinician action attribution in M10 strictly requires recorded clinician `AlertAcknowledgement` or completed `FollowUpTask`. Automated pending tasks do not count. |
| **P13-D** | **DONE** | Removed `expose_raw_for_testing` from `QualityAuditEngine`. Testing uses standard public API interfaces. |
| **P13-E** | **DONE** | Reframed Study S8-K7 H3: states clearly that unmeasured confounding cannot be ruled out from observational data, and reports E-values ($E = 1.05$) to quantify how weak an unmeasured confounder would suffice to explain away the association. |
| **P13-F** | **DONE** | Authored ADR 0017 establishing patient consent precedence in retrospective audits. Enforced `has_active_consent` filtering in `_extract_trajectories_from_db`. Isolated synthetic benchmarks. Wired `tests/acceptance_p13` into CI workflow. |

---

## 3. Study M7 Harm Decomposition & 12-Cell Sweep

### 3.1 Harm Decomposition (Baseline Cell: $\lambda = 3.0$, $\text{MTTR} = 7$)
Data extracted directly from committed `reports/ml/STUDY_M7_DIGITAL_TWIN.json`:

| Policy | Mean Total Harm | Mean Wait Harm | Mean Interruption Harm | Mean Unscheduled Harm | Status Counts | Realised Correlation ($r$) |
|---|---|---|---|---|---|---|
| **Urgency Heuristic** | **0.01880** | 0.00072 | 0.01808 | 0.0 | N/A (Greedy) | N/A |
| **FCFS Baseline** | **0.02128** | 0.00160 | 0.01968 | 0.0 | N/A (FIFO) | N/A |
| **CP-SAT Solver** | **0.09116** | 0.00073 | 0.09044 | 0.0 | 50 OPT / 0 FEAS / 0 TO / 0 INF | **0.0657** |

### 3.2 Root Cause Analysis of the Harm Gap
- **Harm Ratio:** CP-SAT total harm (0.09116) is **4.85× worse** than Urgency Heuristic (0.01880) and **4.28× worse** than FCFS (0.02128).
- **Decomposition:** Wait harm is minimal for CP-SAT (0.00073 vs FCFS 0.00160), but interruption harm accounts for **99.2%** of CP-SAT harm (0.09044).
- **Mechanism:** Daily interruption harm ($0.010$–$0.025$/day) is 20–50× more damaging than initial wait harm ($0.0002$–$0.0005$/day). Under rolling 7-day lookahead, CP-SAT fills available slots immediately with newly eligible patients without reserving capacity for in-flight fraction completion during inevitable stochastic breakdowns (MTTR 3–14 days).
- **Objective Correlation:** The correlation between the rolling MILP objective value and realised simulation harm is $r = 0.0657$, proving the rolling objective does not reflect downstream stochastic disruption.
- **Remediation & Transparency:** As mandated, CP-SAT is prominently badged `"unvalidated in simulation"` across the platform.

### 3.3 Full 12-Cell Parameter Sweep Grid ($\lambda \times \text{MTTR}$)
All 12 cells were fully executed and committed to `reports/ml/STUDY_M7_DIGITAL_TWIN.json`:

| Breakdown Rate ($\lambda$) | MTTR (Days) | Heuristic Total Harm | FCFS Total Harm | CP-SAT Total Harm | CP-SAT / Heuristic Ratio | CP-SAT Optimal / Feasible / Timeout |
|---|---|---|---|---|---|---|
| 2.0 | 3.0 | 0.00287 | 0.00392 | 0.01511 | 5.26× | 50 / 0 / 0 |
| 2.0 | 7.0 | 0.00808 | 0.00949 | 0.03883 | 4.81× | 50 / 0 / 0 |
| 2.0 | 14.0 | 0.02521 | 0.02983 | 0.09919 | 3.93× | 50 / 0 / 0 |
| 2.5 | 3.0 | 0.00424 | 0.00551 | 0.02322 | 5.48× | 50 / 0 / 0 |
| 2.5 | 7.0 | 0.01306 | 0.01479 | 0.06307 | 4.83× | 50 / 0 / 0 |
| 2.5 | 14.0 | 0.03457 | 0.03960 | 0.14798 | 4.28× | 50 / 0 / 0 |
| 3.0 | 3.0 | 0.00627 | 0.00762 | 0.03223 | 5.14× | 50 / 0 / 0 |
| 3.0 | 7.0 | 0.01880 | 0.02128 | 0.09116 | 4.85× | 50 / 0 / 0 |
| 3.0 | 14.0 | 0.04639 | 0.05389 | 0.19894 | 4.29× | 50 / 0 / 0 |
| 3.5 | 3.0 | 0.00831 | 0.01016 | 0.04412 | 5.31× | 50 / 0 / 0 |
| 3.5 | 7.0 | 0.02497 | 0.02901 | 0.12133 | 4.86× | 50 / 0 / 0 |
| 3.5 | 14.0 | 0.05775 | 0.06746 | 0.25206 | 4.36× | 50 / 0 / 0 |

---

## 4. Work Package 8.1: Safety Engineering & Security Hardening

1. **Hazard Log v1 (`docs/safety/HAZARD_LOG.md` & `HAZARD-LOG.md`):**
   - 22 clinical hazards (H1..H22) spanning biological, software, cryptographic, and operational failure modes.
   - Every single hazard references an automated verification test function in the codebase.
   - Verified via `scripts/verify_hazard_log.py` (AST parsing, 22/22 verified).
2. **STRIDE Threat Model v2 (`docs/security/THREAT_MODEL.md`):**
   - Version 2.0.0.
   - Expands trust boundaries from 3 to 4 (Untrusted Networks, API Gateway & Auth Barrier, CDS Engine & Optimizers, Persistence & WORM Sink).
   - 8 distinct security roles mapped under Principle of Least Privilege.
   - Comprehensive 24-threat matrix with automated verification test links.
3. **Automated Penetration Test Suite (`tests/security/test_penetration_suite.py`):**
   - 9 automated black-box tests passing in CI:
     1. Complete OpenAPI Authorization Matrix across 8 roles.
     2. Patient Consent Lifecycle Matrix over HTTP (None, Granted, Withdrawn, Regranted).
     3. Forged Body Fuzzing on Mutating Routes (SQLi, buffer overflow, parameter injection).
     4. Companion Token Expiry & Revocation Enforcement.
     5. Cross-Patient Companion Token Isolation.
     6. Companion Token Zero-Plaintext at Rest.
     7. Offline Sync Replay Idempotency.
     8. HL7 v2 Robustness & LOINC Fuzzing.
     9. Error Message & Stack Trace Hygiene (Zero Internal Path / SQL / Secret Leakage).
4. **Supply Chain Governance & SBOM Generation:**
   - Authored `docs/security/VULNERABILITY_POLICY.md` specifying CVSS-based SLAs (Critical $\le 48$h, High $\le 7$d).
   - Authored `docs/adr/0018-supply-chain-provenance-and-artifact-signing.md`.
   - Developed `scripts/generate_sbom.py` producing CycloneDX v1.5 JSON SBOMs for Python (132 components) and NPM (511 components).

---

## 5. Work Package 8.2: Regulatory Documentation Set

All regulatory documents carry the required `DRAFT-UNREVIEWED` banner:
1. `docs/regulatory/INTENDED_USE.md`: Intended use, indications for use, user population, contraindications, and warnings.
2. `docs/regulatory/DPIA.md`: Data Protection Impact Assessment under NDPA 2023, GDPR Art. 35, and HIPAA.
3. `docs/regulatory/PCCP.md`: Predetermined Change Control Plan for post-market model updates under FDA AI/ML guidance.
4. `docs/regulatory/CLINICAL_EVALUATION_PLAN.md`: Clinical Evaluation Plan per EU MDR 2017/745 and MEDDEV 2.7/1 rev 4.
5. `docs/regulatory/RISK_MANAGEMENT_FILE.md`: Risk Management File adhering to ISO 14971:2019 and IEC 62304.

---

## 6. Verification & Verification Scripts Summary

All project truth and reality scripts pass without warnings:
- `python3 scripts/verify_hazard_log.py`: ✅ 22/22 hazards verified against AST.
- `python3 scripts/check_claims.py`: ✅ PASSED (zero personal machine paths, zero forbidden claims).
- `python3 scripts/check_evidence.py`: ✅ PASSED (all citations, DOIs, and PubMed excerpts verified).
- `python3 scripts/audit_excerpts.py`: ✅ PASSED (0 excerpt files failed).
- `python3 scripts/reality_audit.py --require-stub-registry`: ✅ PASSED (zero hard-coded results, zero toy validations).
- `git diff origin/main tests/acceptance_*`: ✅ **0 lines changed** (acceptance tests 100% untouched).
