# Stub registry (RR8)

Every placeholder, simplification or not-yet-real component must appear here. An empty registry is a claim that nothing is stubbed.

| ID | Component | What is missing | Why | Plan / phase | Gate item that is therefore NOT MET |
|---|---|---|---|---|---|
| S-001 | K1 `fit`/`predict_risk` | Trained recognition network; risk derived from the ODE/posterior | Fabricated in Phase 3 | Phase 3A | K1 |
| S-002 | K1 inference routes | Reference NUTS/MCMC route and SNPE route do not exist; particle filter absent | Phase 3 | Phase 3A | K1 |
| S-003 | K1 SBC / parameter recovery | Validation exercises a toy, not the model | Phase 3 | Phase 3A | K1 |
| S-004 | K4 `fit`, S4 study | No training; S4 numbers hard-coded | Phase 3 | Phase 3C | K4, S4 |
| S-005 | K6, S6 | Results hard-coded | Phase 3 | Phase 3D | K6, S6 |
| S-006 | M12/S10 | Results hard-coded; no federation or DP implemented | Phase 3 | Phase 3D | M12, S10 |
| S-007 | K8 ensemble | Re-implements member formulas with hand-set weights | Phase 3 | Phase 3B | K8 |
| S-008 | K3 `FastLandmarkJointModel` | RESOLVED (Condition R4): Learns coefficients from data | Closed | Phase 3A (R4) | None (Resolved) |
| S-009 | K2, K5 | Not audited by overseer; treat as UNVERIFIED until re-verified through RR1–RR4 | Phase 3 | Phase 3B | K2, K5 |
