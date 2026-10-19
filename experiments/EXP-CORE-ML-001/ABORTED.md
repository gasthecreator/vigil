# EXP-CORE-ML-001 aborted before a result was produced

The preregistered runner generated its train, validation, and test cohorts, selected validation configurations, and began the frozen test bootstrap. The run was interrupted during patient-cluster bootstrap before `results.json` or a report was written. The frozen-test access is recorded in `data/audit/frozen_test_access.jsonl`.

No test metrics were emitted or inspected. The run exposed two protocol weaknesses before completion: per-patient weight normalization did not actually equalize total patient contribution, and the arbitrary sigmoid scales of rule baselines were not independently calibrated. EXP-CORE-ML-001 is withdrawn and its test seed will not be reused. EXP-CORE-ML-002 has a new pre-registration, a fresh test cohort, equal patient-total IPCW weights, and a separate calibration cohort.
