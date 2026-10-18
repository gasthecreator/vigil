# Study M7-TWIN: Departmental Digital Twin & Radiotherapy Triage Evaluation

**Study Identifier:** M7-TWIN
**Module:** M7 (Treatment Continuity & Radiotherapy Triage)
**Pre-Registration:** [docs/studies/PREREG-M7-TWIN.md](file:///docs/studies/PREREG-M7-TWIN.md)
**Date:** 2026-10-18T00:00:00Z
**Replications:** Baseline N=50, Sweep cells N=20 per cell (Total 12 cells)
**Execution Time:** 187.22s
**Clinical Gate Status:** **UNVALIDATED IN SIMULATION** (Prominently displayed in UI and API per P13-A)

---

## 1. Executive Summary & Honest Baseline Comparison

In accordance with Vigil Reality Rules and overseer directives, we report the strongest baseline first:

| Policy | Total Mean Harm | Wait Harm | Interruption Harm | Unscheduled Harm | Mean Wait (Days) | Mean Subgroup Disparity (Days) |
|---|---|---|---|---|---|---|
| **Clinical Urgency Heuristic** (Strongest Baseline) | **0.01880** | 0.00055 | 0.01825 | 0.03530 | 13.11 | 1.82 |
| **First-Come-First-Served (FCFS)** | **0.02128** | 0.00261 | 0.01867 | 0.04384 | 12.72 | 1.0 |
| **Greedy Marginal Harm (Proxy)** | **0.01674** | — | — | — | — | — |
| **Vigil M7 CP-SAT Solver** | **0.09116** | 0.00073 | 0.09044 | 0.04132 | 6.28 | 1.27 |

### Key Finding on Harm Decomposition (P13-A)
- **The Harm Ratio:** CP-SAT total harm (0.09116) is approximately **4.8&times; worse** than the Clinical Urgency Heuristic (0.01880) and **4.3&times; worse** than FCFS (0.02128).
- **Decomposition:** In CP-SAT, waiting harm is very low (0.00073) because CP-SAT aggressively starts waiting patients early (mean wait 6.28d vs 12.72d). However, interruption harm accounts for **99.2%** of CP-SAT's total harm (0.09044).
- **Root Cause Analysis:** Under the E8 continuity model, daily interruption harm ($0.010$–$0.025$/day) is **20 to 50 times more damaging** than initial wait harm ($0.0002$–$0.0005$/day). Heuristic and FCFS policies strictly protect ongoing courses by completing every started patient before allocating slots to waiting patients. CP-SAT solves a rolling 7-day horizon with finite lookahead; without long-horizon multi-week capacity reservations, it starts new patients during temporary capacity abundance, which creates unmanageable ongoing queues when linac breakdowns occur (MTTR 3–14 days).

### Paired Differences vs Vigil M7 CP-SAT (95% Percentile Bootstrap CI)
- **Urgency Heuristic vs CP-SAT:** $\Delta = -0.07237$ [-0.08444, -0.05998]
- **FCFS vs CP-SAT:** $\Delta = -0.06989$ [-0.08230, -0.05765]
- **Greedy Proxy vs CP-SAT:** $\Delta = -0.07442$ [-0.08686, -0.06208]

---

## 2. Solver Diagnostics & Status Counts

| Solver Status | Total Decision Steps in Baseline |
|---|---|
| **OPTIMAL** | 765 |
| **FEASIBLE** | 749 |
| **TIMEOUT** | 1298 |
| **INFEASIBLE** | 21 |
| **FALLBACK** | 1326 |

- **Objective-vs-Realised Harm Correlation (Pearson $r$):** **0.0657**. The negative/weak correlation demonstrates that the rolling-horizon integer program objective (fraction delivery reward vs local wait penalty) does not track long-term realised harm under stochastic multi-week machine downtime.

---

## 3. Pre-Registered 12-Cell Parameter Sweep Grid

Full committed results for $\lambda \in [2.0, 2.5, 3.0, 3.5] \text{ patients/day} \times \text{MTTR} \in [3, 7, 14] \text{ days}$:

| Arrival Rate ($\lambda$) | MTTR | Reps | CP-SAT Harm | Urgency Harm | FCFS Harm | Proxy Harm | CP-SAT Wait Harm | CP-SAT Int Harm | Disparity |
|---|---|---|---|---|---|---|---|---|---|
| $\lambda=2.0$ | 14d | 20 | 0.08982 | 0.02244 | 0.02511 | 0.02114 | 0.00023 | 0.08958 | 0.84d |
| $\lambda=2.0$ | 3d | 20 | 0.05581 | 0.00833 | 0.01022 | 0.00800 | 0.00030 | 0.05551 | 0.43d |
| $\lambda=2.0$ | 7d | 20 | 0.07895 | 0.01692 | 0.01989 | 0.01655 | 0.00036 | 0.07858 | 0.69d |
| $\lambda=2.5$ | 14d | 20 | 0.09576 | 0.02216 | 0.02435 | 0.01992 | 0.00075 | 0.09500 | 1.27d |
| $\lambda=2.5$ | 3d | 20 | 0.05865 | 0.00772 | 0.00954 | 0.00687 | 0.00062 | 0.05804 | 1.01d |
| $\lambda=2.5$ | 7d | 50 | 0.09116 | 0.01880 | 0.02128 | 0.01674 | 0.00073 | 0.09044 | 1.27d |
| $\lambda=3.0$ | 14d | 20 | 0.08978 | 0.02210 | 0.02395 | 0.02003 | 0.00094 | 0.08884 | 1.47d |
| $\lambda=3.0$ | 3d | 20 | 0.04962 | 0.00668 | 0.00937 | 0.00601 | 0.00092 | 0.04870 | 1.24d |
| $\lambda=3.0$ | 7d | 20 | 0.07523 | 0.01574 | 0.01802 | 0.01260 | 0.00113 | 0.07409 | 1.54d |
| $\lambda=3.5$ | 14d | 20 | 0.07727 | 0.02104 | 0.02183 | 0.01786 | 0.00120 | 0.07607 | 1.39d |
| $\lambda=3.5$ | 3d | 20 | 0.04582 | 0.00672 | 0.00908 | 0.00522 | 0.00096 | 0.04486 | 1.58d |
| $\lambda=3.5$ | 7d | 20 | 0.06371 | 0.01516 | 0.01676 | 0.01134 | 0.00136 | 0.06235 | 1.61d |

---

## 4. Pre-Registered Hypotheses Evaluation

### Hypothesis H1 (CP-SAT vs FCFS): REFUTED
- Mean Harm difference: -0.06989 (95% CI: [-0.08230, -0.05765])
- **Conclusion:** FCFS achieves lower realised harm than CP-SAT across all operational regimes due to zero course fragmentation.

### Hypothesis H2 (CP-SAT vs Urgency Heuristic): URGENCY_ACHIEVES_LOWER_RAW_HARM
- **Analysis:** The Clinical Urgency Heuristic achieves substantially lower realized harm (~4x lower) because it never starts a new patient if an ongoing patient would suffer a treatment break. In contrast, CP-SAT over a rolling 7-day horizon with finite lookahead initiates waiting patients, which leads to treatment interruptions when machines break down. Interruption harm is 20-50x more damaging per day than initial wait harm under the E8 continuity model.

### Hypothesis H3 (Subgroup Fairness): SUPPORTED
- Observed Disparity: **1.27 days** (Bound: $\le 5.0$ days).
- **Conclusion:** CP-SAT successfully bounds demographic wait disparity across all arrival regimes.

### Hypothesis H4 (Ranking Stability): SUPPORTED
- Minimum Spearman rank correlation: **0.982** (Bound: $\ge 0.80$).

---

## 5. Clinical Readiness Gate ("Unvalidated in Simulation")
Per condition P13-A and Reality Rules:
- The scheduler UI and API response schemas prominently display **`validation_status: "unvalidated in simulation"`**.
- No automated radiotherapy reallocation recommendation may be applied without explicit clinician review and confirmation.
