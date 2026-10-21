# Study S2: retracted pending a corrected independent replication

**Status: RETRACTED.** Do not use the legacy metrics below as evidence of an anytime-valid guarantee or as a matched-false-alarm comparison. All historical results are synthetic and retain their original values in `results.json` for audit traceability.

The repository had two different K2 implementations writing to this study location. The recorded report matches the deprecated `sequential_k2.py` prototype, which clips likelihood increments and cumulative scores; those operations do not establish a nonnegative test supermartingale. Its “severe MNAR missingness” scenario generates no missing observations. Five empirical scenario rates cannot prove Ville validity.

The newer `scripts/run_study_s2.py` is not a valid replacement report: `calibrate_operating_points()` hard-codes `alpha_pt=0.25`, threshold `40.0`, and calibration FAR `0.0094`; it does not perform the grid search described in the preregistration. It also uses the already examined test cohort (seed 42). No rerun on that cohort can repair the evidence.

The legacy benchmark writer is disabled. A new S2 result requires an amended preregistration, an actually computed calibration procedure, explicit assumptions supporting the e-process, and an independent test cohort that has not been examined. Until then, no K2 false-alarm guarantee or matched-FAR performance claim is earned.

See [`QUALITY-RERUN-2026-10.md`](../../../docs/audits/QUALITY-RERUN-2026-10.md) for code references, remediation, and the wider core audit.
