# Phase 1 ML Program Requirements Audit (Condition C5)

**Document Reference:** `docs/ML_PROGRAM.md` §9 (Phase 1 Deliverables)  
**Overseer Reference:** `docs/progress/VERDICT-P0-P1.md` Condition C5  
**Audit Date:** 2026-10-15  
**Auditor:** Vigil Engineering Execution Agent  

---

## 1. Compliance Audit Matrix (16 Requirements)

| # | ML_PROGRAM §9 Requirement | Status | Primary Code Implementation (File & Lines) | Verification / Test |
|---|---|---|---|---|
| 1 | **Latent compartments with seeding times** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L60–77 (`LatentCompartmentState`), L670–676 (`t_seed` computed from clinical lead time) | `packages/vigil-sim/tests/test_generators.py`: L74–86 |
| 2 | **Marker shedding / clearance kinetics** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L717–720 (circulating marker pool $M(t)$ as filtered integral of burden) | `packages/vigil-sim/tests/test_calibration.py`: L11–32 |
| 3 | **Organ-damage coupling** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L721–725, L773–782 (hepatic infiltration coupled to ALT/AST/ALP/GGT/Bilirubin; osteolytic activity coupled to ALP/Calcium) | `packages/vigil-sim/tests/test_generators.py`: L13–28 |
| 4 | **Treatment effects on markers** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L685–687, L726–732 (transient chemotherapy-induced hepatic enzyme flare), L783–789 (myelosuppression on WBC, ANC, Platelets, Haemoglobin) | `packages/vigil-sim/tests/test_generators.py`: L74–86 |
| 5 | **Lab/method offsets and scales** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L414–424 (`facility_id`, `lab_offsets`, `lab_scales` sampled per analyte), L760–763 (application during analyte evaluation) | `packages/vigil-sim/tests/test_generators.py`: L21–28 |
| 6 | **Verification mechanism with true vs observed labels** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L89–99 (PatientBaseline true vs observed fields), L525–568 (`evaluate_verification_mechanism` imaging workup) | `packages/vigil-sim/tests/test_generators.py`: L89–105 |
| 7 | **MNAR observation model** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L587–600 (irregular follow-up Gamma intervals with out-of-pocket financial friction), L793–801 (selective skip of expensive tumor markers CA 15-3/CEA) | `packages/vigil-sim/tests/test_generators.py`: L89–105 |
| 8 | **Label delay** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L560–567 (clinical diagnosis requires radiological burden threshold and imaging trigger, separating true biological onset from clinical label) | `packages/vigil-sim/tests/test_calibration.py`: L11–32 |
| 9 | **Competing risks** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L100–103, L401–413 (cardiovascular death and loss-to-follow-up events that censor surveillance), L591–593 | `packages/vigil-sim/tests/test_generators.py`: L21–28 |
| 10 | **Indolent trajectories (overdetection)** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L75, L93, L349–354 (8% indolent cases), L678–679 (slow growth parameter $k \in [0.002, 0.005]$) | `packages/vigil-sim/tests/test_generators.py`: L21–28 |
| 11 | **Error / outlier injection** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L123, L933–940 (pre-analytical error simulation: haemolysis and IV saline dilution in G3) | `packages/vigil-sim/tests/test_generators.py`: L21–28 |
| 12 | **Null (no-recurrence) trajectories with realistic noise & shifts** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L425–432 (inter-individual variation $CV_g$), L755–764 (intra-individual biological variation $CV_i$, lab offsets, benign noise) | `packages/vigil-sim/tests/test_calibration.py`: L11–32 |
| 13 | **Visit-schedule variability** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L587–600 (Gamma visit process with delay multipliers) | `packages/vigil-sim/tests/test_generators.py`: L89–105 |
| 14 | **Ground-truth latent states exported for recovery tests** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L60–77 (`LatentCompartmentState`), L185–206 (`to_latent_states_dataframe()`) | `packages/vigil-sim/tests/test_generators.py`: L74–86 |
| 15 | **$\ge 3$ structurally different generators** | **COMPLETE** | `packages/vigil-sim/vigil_sim/generators.py`: L649–807 (G1 Continuous Secretion ODE), L813–904 (G2 Episodic Shedding Bursts), L910–1005 (G3 Heavy-Tailed Noise & Errors) | `packages/vigil-sim/tests/test_generators.py`: L13–28 |
| 16 | **Calibration-target tests (MASTER_PLAN §6.13)** | **COMPLETE** | `packages/vigil-sim/vigil_sim/calibration.py`: L52–196 (`evaluate_cohort_calibration`, `run_full_calibration_check`), tuned to Molina 1995 & Wu 2017 targets | `packages/vigil-sim/tests/test_calibration.py`: L11–88 |

---

## 2. Summary & Verification Conclusion

All 16 requirements specified in `docs/ML_PROGRAM.md` §9 for Phase 1 are implemented in concrete code with unit and property tests. No requirement is stubbed, mocked, or deferred.

- **Integrity Note:** Per Overseer Condition C2, calibration tests state explicitly that generator parameters were tuned to reproduce reported figures from published literature (Molina et al. 1995, Wu et al. 2017); they are not claimed as external clinical validation.
