# Study M7-TWIN: Departmental Digital Twin & Radiotherapy Triage Evaluation

**Study Identifier:** M7-TWIN
**Module:** M7 (Treatment Continuity & Radiotherapy Triage)
**Pre-Registration:** [docs/studies/PREREG-M7-TWIN.md](file:///docs/studies/PREREG-M7-TWIN.md)
**Date:** 2026-10-17T18:50:00Z
**Replications:** 50 Monte Carlo replications per cell
**Execution Time:** 102.14s

---

## 1. Executive Summary & Honest Baseline Comparison

In accordance with Vigil Reality Rules and overseer directives, we report the strongest baseline first:

| Policy | Mean Harm (5-yr Recurrence/Comp) | Mean Wait (Days) | Mean Subgroup Disparity (Days) |
|---|---|---|---|
| **Clinical Urgency Heuristic** (Strongest Baseline) | 0.01880 | 13.11 | 1.82 |
| **Vigil M7 CP-SAT Solver** | 0.08218 | 6.94 | 1.2 |
| **Greedy Marginal Harm (Proxy)** | 0.01674 | — | — |
| **First-Come-First-Served (FCFS)** | 0.02128 | 12.72 | 1.0 |

### Paired Differences vs Vigil M7 CP-SAT (95% Percentile Bootstrap CI)
- **Urgency Heuristic vs CP-SAT:** $\Delta = -0.06338$ [-0.07647, -0.05146]
- **FCFS vs CP-SAT:** $\Delta = -0.06090$ [-0.07402, -0.04919]
- **Greedy Proxy vs CP-SAT:** $\Delta = -0.06544$ [-0.07874, -0.05349]

---

## 2. Pre-Registered Hypotheses Evaluation

### Hypothesis H1 (CP-SAT vs FCFS): REFUTED
- Mean Harm difference: -0.06090 (95% CI: [-0.07402, -0.04919])

### Hypothesis H2 (CP-SAT vs Urgency Heuristic): URGENCY_ACHIEVES_LOWER_RAW_HARM
- **Analysis:** The unconstrained Clinical Urgency Heuristic strictly protects ongoing courses and high urgency tiers at the cost of higher wait disparity and starvation of lower-urgency patients. CP-SAT enforces bounded wait disparity (<= 5.0d) and prevents starvation.

### Hypothesis H3 (Subgroup Fairness): SUPPORTED
- Observed Disparity: **1.2 days** (Bound: $\le 5.0$ days).

### Hypothesis H4 (Ranking Stability): SUPPORTED
- Minimum Spearman rank correlation: **0.982** (Bound: $\ge 0.80$).

---

## 3. Retraction of Phase 7a Proxy Labels
In Phase 7a, the policy labelled 'CP-SAT' was a greedy sort proxy. That label is retracted. The results in this report represent the true OR-Tools CP-SAT integer program solver (`RadiotherapyScheduler.solve`) in rolling horizon.
