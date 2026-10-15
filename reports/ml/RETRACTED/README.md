# Retracted Studies Registry (Condition R1 / Master Plan v1.2)

> **Date:** 2026-10-16  
> **Authority:** Overseer Verdict P3 (`docs/progress/VERDICT-P3.md`) and Master Plan v1.2 (`docs/MASTER_PLAN.md` §14 Phase 3).  
> **Status:** RETRACTED & WITHDRAWN from benchmark reports and active claims.

## Overview
During the review of Phase 3 (commit `bcc0f12`), the overseer identified that studies S4, S6, and S10 contained hard-coded numerical literals and synthetic dictionary returns rather than computed outputs from trained models executing on data. Under `docs/REALITY_RULES.md` (RR1, RR2), hard-coded results are strictly forbidden.

Per Overseer Condition R1, these studies have been moved here and withdrawn from `reports/ml/BENCHMARK_REPORT.md` and `reports/ml/results.json`.

## Retracted Studies

| Study ID | Title | Reason for Retraction | Rescheduling | Stub ID in `docs/STUBS.md` |
|---|---|---|---|---|
| **S4** | Deep Zoo Pre-Training & Scaling | Pre-training and scaling curves returned hard-coded literal dictionaries; K4 fit learned nothing. | Sub-phase 3C | S-004 |
| **S6** | Active Sensing & Adaptive Scheduling | Latency, visit counts, and dollar costs were hard-coded literals. | Sub-phase 3D | S-005 |
| **S10** | Multi-Site Synthetic Trial & Federated Learning (M12) | Per-site AUCs and federated utility numbers were hard-coded literals. | Sub-phase 3D | S-006 |

No metric or claim from these retracted studies may be cited anywhere in the repository until they are re-established by real code executing in their designated sub-phases.
