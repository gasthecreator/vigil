# Stub registry (RR8)

Every placeholder, simplification or not-yet-real component must appear here. An empty registry is a claim that nothing is stubbed.

| ID | Component | What is missing | Why | Plan / phase | Gate item that is therefore NOT MET |
|---|---|---|---|---|---|
| S-001 | K1 `fit`/`predict_risk` | RESOLVED (Conditions V2, V3): Direct label head removed; risk strictly derived from posterior via kinetic rollout; detection threshold calibrated via Youden's J; zero formulaic losses | Closed | Phase 3A-3 | None (Verified by acceptance tests) |
| S-002 | K1 inference routes | RESOLVED (Conditions V1, V2): Four genuinely distinct routes (`amortized` with `AmortizedRecognitionNet` + safetensors, `ukf`, `nuts`, `npe` retrained at load with zero pickle); zero aliases | Closed | Phase 3A-3 | None (Verified by acceptance tests) |
| S-003 | K1 SBC / parameter recovery | RESOLVED (Conditions V1, V2): SBC rank uniformity (KS p>0.01) and parameter recovery (75-100% coverage, r=0.89-0.95) verified across all four distinct routes | Closed | Phase 3A-3 | None (Verified by acceptance tests) |
| S-004 | K4 `fit`, S4 study | No training; S4 numbers retracted | Phase 3 | Phase 3C | K4, S4 |
| S-005 | K6, S6 | S6 study retracted; active sensing suggestion engine requires simulator optimization | Phase 3 | Phase 3D | K6, S6 |
| S-006 | M12/S10 | S10 study retracted; federated & DP pipeline deferred to Phase 3D | Phase 3 | Phase 3D | M12, S10 |
| S-007 | K8 ensemble | Conformal risk control & production ensemble require Phase 3B member models | Phase 3 | Phase 3B | K8 |
| S-008 | K3 `FastLandmarkJointModel` | RESOLVED (Condition R4): Learns coefficients from data via LogisticRegression | Closed | Phase 3A (R4) | None (Resolved) |
| S-009 | K2, K5 | Re-verify through RR1–RR4 under Phase 3B | Phase 3 | Phase 3B | K2, K5 |
