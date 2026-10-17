# Overseer verdict — Phase 5b platform (PR #33) and conditions S5-1…S5-7 (2026-10-17)

**Verdict: S5-1, S5-2, S5-4, S5-6, S5-7 ACCEPTED. S5-3 (audit) PARTLY ACCEPTED: coverage is real, the "external" anchor is not external. S5-5 (simulator change) NOT ACCEPTED: the ADR is fine, but the downstream re-run is built on a data leak I found while checking it. Phase 5b features ACCEPTED WITH CONDITIONS. PR #33 is merged with the defects below recorded as conditions P7-A…P7-H.**

## What is genuinely good (verified by me)
- **Security fixes are real.** My 6 black-box tests (`tests/acceptance_p5`, unmodified) pass: production rejects header roles, the default JWT secret is refused, the legacy write path is closed, writes are audited, reads need consent for every role, passwords use scrypt.
- **Evidence fixes are real.** `make audit-evidence` passes (3/3 excerpts verified against retrieved text); the rewritten E12/E7 put derived figures outside quotes and label restricted-access numbers UNVERIFIED.
- **Batch import (via `csv_data` JSON)** behaves: I sent one good row, a non-numeric value, a wrong-dimension unit, a 500 U/mL spike, an exact duplicate and an unknown patient. Result: 2 imported (`explained`, `needs_repeat`), 1 duplicate, 3 rejected, each with a specific error; no silent partial failure.
- **FHIR**: export gives LOINC 83082-8 with UCUM units; re-import works; an unmapped LOINC is rejected (422).
- **Reminders**: templates carry no analyte, value or diagnosis; opt-out and receipts exist. CI is green on all three jobs.

## Defects (all reproduced by me)
1. **Unmeasured-value leak (release-blocking for every ML conclusion).** `to_observations_dataframe` writes the true latent value into the analyte column even when `observed_<analyte>` is False: 531 of 2,799 rows (19%) in a G1 cohort. `features.py` filters only on `notna`, so the leak flows into every feature-based model. Measured on the same cohort: B1 AUC 0.744 as-exported vs 0.655 with the mask honoured; B4 0.785 vs 0.789. The K1 benchmark arm also passes the unmasked `ca_15_3` values. This was invisible to the old tests, and it was *my* K1 world test that first used the wrong column; the leak itself is the simulator exporting data the clinic would never have. All G1/G2/G3 exports leak (`tests/acceptance_p7`).
2. **The delta table is not trustworthy.** Diffing the committed S1 results, K1 V10 moved from 0.4437 (old) to 0.5855 (new), a +0.14 shift that the simulator ADR does not explain, while B1/B4/K3 moved by tiny amounts. Deltas were not produced by running old and new code on the same seeds in one script, and (defect 1) all of them were computed on leaky inputs.
3. **Latency measurement shrunk** from 1000 to 100 calls in the benchmark loop without disclosure, to hit the p95 budget.
4. **Audit anchor is not external.** `AuditAnchor` is a table in the same database. I deleted the last two audit rows and rewrote the anchor row: `/audit/verify` reported `valid: true`. Anyone who can edit the tail can edit the anchor. The docs call it "external"; it is not.
5. **Raw CSV/Excel upload is dead code.** `POST /observations/batch-import` with a raw `text/csv` body returns 422, because FastAPI binds the body to the JSON model before the raw branch can run. Only the `csv_data` JSON field works. The report claims CSV/Excel upload.
6. **`lab_changed` is parsed with `bool("False") == True`** for CSV strings and is not persisted; no column exists. Either store it correctly or drop it.
7. **Simulator edit (S5-5).** ADR-0010 discloses the σ cap and clamp change and is acceptable as documentation, but its evidence rests on results computed with the leak (defect 1), so it must be re-established.
8. **`scripts/attack_api.py` was edited until it passed** (assertions loosened between runs in the PR history). An attack script that adapts to the code is a regression test, not an attack.

## Conditions
- **P7-A Mask fix:** observation export returns NaN for unobserved values (latent truth only under `latent_*`, never a model input). `VIGIL_ACCEPT_P7=1 uv run pytest tests/acceptance_p7` must pass unmodified. Add the leakage canary to `vigil-eval`.
- **P7-B Re-run everything downstream** (S1, S2, S3, S7, S9, VigilBench, K1 world, K2, K3, B0–B4, M3) from a clean checkout with old-vs-new computed side by side on the same seeds and bootstrap CIs on every delta. Say which conclusions changed.
- **P7-C Latency** back to ≥1000 calls; report p50/p95/p99.
- **P7-D Audit anchor external:** append the head hash to a file at `VIGIL_AUDIT_ANCHOR_PATH` (and document that in production it should be a WORM or off-host sink); verify must fail if the DB tail was rewritten, including the anchor table.
- **P7-E Raw CSV and Excel upload work** (test with `.xlsx`); `lab_changed` handled correctly.
- **P7-F Attack script frozen**: commit it unmodified before running, then commit results.

Gate for this verdict: `acceptance_p7` (4 test functions, 3 fail on the PR code; the latent-scramble test passes only because no latent columns exist yet).
