# EXP-CORE-ML-009 conclusion

Status: **registered synthetic estimator validation executed once**.

The run used 100 replicates of 2,500 records for each MCAR, MAR, and MNAR
condition at implementation SHA `f2a1cf859009cd66b59386e19fca441826f627fc`.
The preregistration, runner, estimator source hash, environment lock hash,
results, and generated report are linked by `ACCESS_LOG.json`. All 300
registered IPW estimates were defined; all result and report hashes match the
access record.

In the registered MCAR condition, mean IPW estimate errors were within 0.001
of the full-cohort reference for all five metrics. Under the correctly
specified one-covariate MAR condition, IPW mean errors were 0.0027 for
sensitivity, -0.0006 for specificity, -0.0002 for prevalence, -0.0009 for
Brier score, and 0.0034 for AUC. Complete-case mean errors in MAR were +0.1439,
-0.1037, +0.1055, +0.0246, and -0.0165, respectively.

In the outcome-dependent MNAR condition, IPW did not recover the full-cohort
metrics: mean errors were -0.1271 for sensitivity, +0.0061 for specificity,
+0.2279 for prevalence, +0.1028 for Brier score, and -0.0706 for AUC. This is
the registered negative identification control: the propensity model omits
the outcome-dependent verification mechanism. It demonstrates that the
current observed-data IPW path does not identify latent outcomes under this
MNAR design.

These results support only the estimator's behavior under this simple,
correctly specified synthetic MCAR/MAR design and its failure under the
specified MNAR mechanism. They do not establish that real verification is
conditionally exchangeable, that positivity holds in partner data, that the
simulator matches a clinical cohort, or that any patient-level estimate is
valid. No model was selected or tuned. Package B remains open for the complete
source-to-serving audit and observed-diagnosis versus latent-recurrence
estimand closure.
