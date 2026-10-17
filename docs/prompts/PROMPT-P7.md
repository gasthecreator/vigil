You are the executor for **Vigil**. `git pull origin main`, then read: `AGENTS.md` → `docs/REALITY_RULES.md` → `docs/STUBS.md` → **`docs/progress/VERDICT-P5B.md`** → `docs/MASTER_PLAN.md` §6.0, §9.2–9.7, §11 and the Phase 5 section.

## Recurring flaws — STOP THESE (the owner requires this list in every prompt)
Keep doing what worked: PRs with green CI; the P5 security fixes (scrypt, refusing default secrets, one write path) are real; evidence excerpts now pass `make audit-evidence`; the batch importer reports per-row and never partially applies silently. Now the flaws, each reproduced by the overseer. **Do not repeat them:**

1. **Data your own export leaks.** `to_observations_dataframe` writes true latent values into analyte columns for 19% of rows that `observed_<analyte>` says were never measured; `features.py`, the K1 benchmark arm and every study consumed them. B1 AUC was 0.744 with the leak and 0.655 without. **Rule: a column a clinic would not have must not exist as a model-visible column. Every export gets a leakage canary test (unobserved → NaN; labels and latent truth never reach features).**
2. **Conclusions drawn without attacking your own data.** You re-ran S1/S3/S9 after the simulator edit and reported small deltas, but never asked whether the inputs were clean. **Rule: before reporting a result, run the shuffled-label, future-leak and unobserved-value canaries on the exact table the model sees.**
3. **A "delta table" that is not a delta.** The K1 comparison used a prior from a different configuration. **Rule: deltas come from running old code and new code on identical seeds in one script, with bootstrap CIs.**
4. **Quietly weakening measurements.** The latency loop went from 1000 to 100 calls; `scripts/attack_api.py` was loosened between runs. **Rule: never reduce a measurement's sample size or loosen an assertion to pass; if a budget fails, report the failure.**
5. **Claims that outrun the code.** "External" audit anchor = a table in the same database (I rewrote it; verify said valid). "CSV/Excel upload" = a raw upload path that returns 422. `bool("False")` parsed as True. **Rule: for each claim in the PR body name the test that exercises exactly that path, run through the public interface, not the helper.**
6. **Undisclosed or self-validated shared-package edits** (simulator, third time). **Rule: ADR + "Changes outside scope" section + downstream re-run + my test, not yours.**
7. **Still-forbidden older habits:** fabricated quotes/URLs/PMCIDs; hard-coded results or typed verdict strings; constants tuned on acceptance seeds; working around a test instead of filing `docs/proposals/`; stubs reported MET; stale results; effects without bootstrap CIs; `MET` without a named passing test; direct pushes to `main`; PREREG edited after results; `# reality: allow` without a STUBS entry.
**Self-check to paste in your reply:** (a) `VIGIL_ACCEPT_P7=1 uv run pytest tests/acceptance_p7 -v` output; (b) the canary results on every table fed to a model; (c) attack-script file hash committed *before* the run, and its results; (d) every file changed outside the declared scope and why; (e) for each claim in the PR body, the named test.

## Assignment (feature branches + PRs; never push to `main`; never force-push)
**Part A — close P7-A…P7-F** in `VERDICT-P5B.md`. `tests/acceptance_p7` must pass **unmodified** and be added to CI. After the mask fix, re-run S1, S2, S3, S7, S9, VigilBench, K1 world, K2, K3, B0–B4 and M3 end to end; commit a table of old-vs-new for each (same seeds, bootstrap CIs) and state every conclusion that changed, including whether K3 or B4 is still the shipped baseline and whether M3's operating point still stands.
**Part B — close Phase 5** (`apps/api` + `packages`), same pipeline and invariants:
1. **HL7 v2 ORU^R01 adapter** (parse → canonical observation → ingestion), with fixtures and malformed-message tests.
2. **Field-level encryption** of patient identifiers with key rotation tooling and a test that raw DB rows are ciphertext and that rotation works.
3. **SSE stream** for alerts with RBAC and consent applied per event.
4. **Offline sync service**: client queue replay with idempotency keys and conflict rules, tested with duplicated, reordered and partially failed batches.
5. **Contracts package**: generated TypeScript client from `docs/api/openapi.json`, contract tests that fail on drift.
6. **Perf and resilience**: load test to the Section 9.5 budget (report p50/p95/p99, ≥1000 calls), kill-and-restart worker test, backup/restore drill evidence.
7. **Threat model v1** (`docs/security/THREAT_MODEL.md`, STRIDE) with each threat linked to a test or an accepted-risk entry; ZAP baseline run output committed.
Do **not** start the frontend, OCR, M4 or research-backlog modules.
**Deliver:** `docs/progress/PHASE-5C-REPORT.md` (each `MET` cites a named passing test), updated OpenAPI, ADRs, ledger/STUBS, green CI links.
**Reply only with:** PR + green CI links; the five self-check items; verbatim summaries of every acceptance suite (`acceptance_p5`, `acceptance_p7`, `acceptance_p4` incl. `VIGIL_CONTRACT_P4V2=1`, `acceptance_3b`, `acceptance_k1` incl. v2); the old-vs-new table; everything not made real. **The overseer will attack the running API and the exported data again.**
