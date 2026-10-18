# Partner path dry run (SYNTHETIC)

Written by `scripts/run_partner_dry_run.py`; do not edit. Every file here comes from invented data. `messy/` shows the rejection report and the analysis stopping at the stop rate; `signal/` and `null/` run the full evaluation on cohorts with and without a planted laboratory signal. They check plumbing and null behaviour; they are not performance results and say nothing about real patients.

Exit codes of the steps: `{"messy_evaluation": 2, "messy_ingest": 2, "null": 0, "signal": 0}` (messy_ingest 2 and messy_evaluation 2 mean 'stopped at the stop rate', as intended).
