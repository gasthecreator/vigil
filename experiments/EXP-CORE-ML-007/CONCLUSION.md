# EXP-CORE-ML-007 conclusion

Status: **exploratory output; registered analysis incomplete**.

The committed runner at source SHA `7efc7f7bf716f988a464a2e02a72dd13d44c65a2` generated the results in `results.json` and `REPORT.md` once using the registered new seed namespace and profile hash. Its synthetic point estimates and per-model intervals are preserved as generated; they are not clinical evidence or a model-promotion decision.

Two post-access audit findings prevent treating this as the complete preregistered comparison:

1. The one-time access records used `SYNTHETIC-CORE-ML-004-*` labels from a copied string literal. The append-only correction in `ACCESS-LOG-CORRECTION.md` links the original timestamps to EXP-CORE-ML-007 and its actual seed tuples.
2. The preregistration required paired patient-cluster contrasts for learned models against B0, B1, and B2. The runner produced those contrasts only against B1. The missing contrasts cannot be reconstructed from the saved aggregate metrics.

The original results and access log were not rewritten. A complete registered comparison requires a new experiment ID and independent seeds with all registered contrasts implemented before frozen test access. The output of this study is not used to select a model or tune a later test cohort.
