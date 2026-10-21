# EXP-CORE-ML-008 report regeneration note

The one-time analysis and test access used source SHA `7db2ca0e5e38078d48e78ff3f0255d970a9b4736`, recorded in `results.json` and `data/audit/frozen_test_access.jsonl`. After the run, a report-integrity check found that the runner rendered from its in-memory dictionary rather than reloading the key-sorted saved JSON; metric rows had the same values but a different deterministic order when rebuilt from JSON.

The post-analysis runner now reloads `results.json` before rendering and iterates metrics in an explicit order. This report-only correction does not change cohort generation, fitting, predictions, metrics, bootstrap, seeds or test access. The generated report remains byte-identical, and `test_generated_report_matches_saved_sorted_results` proves the saved JSON regenerates the committed report without accessing data. The original experiment source SHA remains the analysis provenance.
