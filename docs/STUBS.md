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
| S-007 | K8 Conformal Suite | RESOLVED (Phase 3B): ConformalRiskController (finite-sample FNR control), OODGate (Mahalanobis inlier/shift detection), AdaptiveConformal (ACI drift tracking) fully implemented in vigil_ml/k8.py; verified by tests/acceptance_3b/test_k8_contract.py | Closed | Phase 3B | None (Passes acceptance contract) |
| S-008 | K3 `FastLandmarkJointModel` | RESOLVED (Condition R4): Learns coefficients from data via LogisticRegression | Closed | Phase 3A (R4) | None (Resolved) |
| S-009 | K2 sequential detector, K5 | K2 RESOLVED (Phase 3B): SequentialDetector anytime-valid e-process with recursive standardisation and mixture supermartingale in vigil_ml/k2.py; verified by tests/acceptance_3b/test_k2_contract.py. K5 hierarchical lab harmonisation deferred to Phase 3C. | K2 complete; K5 scheduled for 3C | Phase 3C | K5 |
| S-010 | K1 surveillance role | K1 is a research inference module; K3/B4 are the shipped surveillance baselines (ADR-0007). Token `K1-WORLD`: K1 does not beat CA 15-3 baseline on vigil-sim cohort. | One-marker mechanistic model recovers parameters in its own world but adds nothing on vigil-sim over K3/B4; closed per MASTER_PLAN §13 fallback protocol | Closed (Research Module) | None (K1-WORLD registered) |

