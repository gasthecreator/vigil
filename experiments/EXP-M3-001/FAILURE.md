# EXP-M3-001 execution failure

The single registered attempt ran from source commit `720232a5948c29a92979daf2da3f8ba47fadc345` on 2026-10-20. It generated the nine registered synthetic cohorts in memory, then stopped during baseline scoring when the simulator supplied an observed CA 15-3 value of `0.0`. `vigil_ml.m3.adjudicate` rejected that value because its input contract requires a positive concentration.

The incomplete `ACCESS_LOG.json` records the protocol, source/environment hashes, exception type, and message. The run produced no `results.json` or `REPORT.md`; the cohort data were not persisted, so no cohort input hashes can be recovered from this attempt. This study ID is closed as a failed execution. Do not rerun it or treat it as a completed sensitivity result. A successor study must use new seeds and preregister the positive-value and strict-time eligibility rules before generation.
