# EXP-CORE-ML-008 conclusion

Status: **registered synthetic baseline comparison executed**.

The study ran once at code SHA `7db2ca0e5e38078d48e78ff3f0255d970a9b4736` with profile SHA-256 `70cfed8bfe8c28c668434b5e409d2350b276784461f54a56e3ecd69ae98469b3`. Its exact G1/G2/G3 access records and five-seed test cohorts are in the frozen access log and `results.json`. The runner selected B3 `C=0.05` and B4 `depth=3, estimators=150, learning_rate=0.05` on validation IPCW Brier only. All 72 preregistered paired contrasts (B3/B4 versus B0/B1/B2 across four metrics and three generators) have 1,000 valid patient-cluster bootstrap resamples.

On synthetic G3, B4 had IPCW AUC 0.7907 (95% patient-cluster CI 0.7782–0.8036), IPCW Brier 0.1008 (0.0966–0.1049), IPCW calibration error 0.0478 (0.0440–0.0556), and weighted average precision 0.5508 (0.5293–0.5708). The paired B4-minus-B1 ECE difference was +0.0170 (0.0131–0.0254), so its calibration error was worse than B1 despite stronger discrimination and lower Brier score. G1/G2/G3 outputs and all comparator intervals are in the generated report and machine-readable results.

These findings are conditional on the committed synthetic generator and observed-diagnosis estimand. They do not establish clinical performance, real-site transport, alert policy, decision utility, subgroup safety, or an optimal real-world model. Package C remains open: the legacy fixed-AUC gates and K3 shuffled-outcome canary remain unresolved, and the broader decision-curve, alert-burden, subgroup and runtime requirements are not answered by this experiment.
