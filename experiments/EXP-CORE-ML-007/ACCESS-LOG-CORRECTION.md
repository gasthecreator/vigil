# EXP-CORE-ML-007 access-log correction

The one-time test evaluation completed from source SHA `7efc7f7bf716f988a464a2e02a72dd13d44c65a2`. The original append-only access log records its three dataset names as `SYNTHETIC-CORE-ML-004-{G1,G2,G3}-TEST` because the copied runner retained the old dataset-name string. The run itself used EXP-CORE-ML-007's registered seeds: G1 `54410–54414`, G2 `54420–54424`, G3 `54430–54434`; the caller, source SHA, results JSON, and generated report identify EXP-CORE-ML-007.

The original entries were not edited. Three appended `metadata_correction` records in `data/audit/frozen_test_access.jsonl` link each wrong label to its original timestamp and correct experiment/seed set. They have `is_frozen_test: false` because they document metadata and do not access any cohort.

A separate protocol deviation was found after test access: the preregistration asked for paired patient-cluster contrasts against B0, B1, and B2, but the runner produced paired contrasts only against B1. The committed results/report are preserved as exploratory synthetic results; they do not fulfill EXP-CORE-ML-007's registered comparison. A complete comparison requires a new experiment ID, new seeds, and a runner that computes every registered contrast before test access.
