# EXP-K6-001 provenance and replay-safety audit

Status: **synthetic-only historical evidence; not clinical validation**.

The committed `dev_results.json`, `results.json`, and `REPORT.md` are existing study outputs. Before this audit, the runner's `--dev` and `--frozen` paths wrote over their respective JSON outputs, and `--rerender` rewrote the committed report without checking for an existing file. The runner now refuses those persistent modes when their output already exists. The `--smoke` path remains isolated in a temporary directory.

Regression tests invoke each persistent mode against the existing files and verify that it refuses before changing their bytes. No K6 cohort was generated, no report was rerendered, and no study result was regenerated during this repair. These guards protect the historical artifacts; they do not establish K6 model validity, clinical utility, or transportability. See `CONCLUSION.md` for the registered outcome and limitations.
