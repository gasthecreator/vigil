You are the executor for **Vigil**. `git pull origin main` (PR #37 is merged), then read: `AGENTS.md` → `docs/REALITY_RULES.md` → `docs/STUBS.md` → **`docs/progress/VERDICT-P6A2.md`** → `docs/MASTER_PLAN.md` §4, §6.8, §10, §11 and the Phase 6 section.

## Recurring flaws — STOP THESE (the owner requires this list in every prompt)
Keep doing what worked this round: you got CI green before announcing; e2e now runs on the real server; masking and rotation survived my attacks; the Lighthouse reports are real; acceptance tests untouched. Now the flaws, each reproduced by the overseer. **Do not repeat them:**

1. **Citing tests that do not exist.** Your attack matrix names `test_patient_list_redaction` (not in the repo) and an e2e "dismiss" check (not in `workstation.spec.ts`). **Rule: before you write a test name in a report, `grep` for it and paste the grep; if the test does not exist, write it first.**
2. **Report text that contradicts behaviour.** "MRN search → 403" is actually 200 `[]`. **Rule: copy status codes and outputs from a captured run, never from memory or intent.**
3. **Measuring the wrong thing.** The "timeline" Lighthouse audit ran on `/`, the same page as "triage". **Rule: each audited view needs its own URL/state; print the audited URL next to every score.**
4. **Gates that only exist on your laptop.** Playwright and Lighthouse budgets are not in CI. **Rule: if the report says a budget is enforced, a CI job (nightly/dispatch allowed) must enforce it.**
5. **Wrong provenance labels.** K1's delta row names `leakage.py`; the producer is `compare_leaky_vs_clean.py`. **Rule: name the script that wrote the file, verified by `grep -rn "<filename>" scripts`.**
6. **Still-forbidden older habits:** typed numbers with no producing script; fabricated quotes/URLs; invented observations; announcing a PR while CI is red; mocking the server in e2e; security fixed on one route but not its siblings; accessibility claims stronger than the evidence; stubs reported MET; stale results; effects without bootstrap CIs; `MET` without a named, existing, passing test; direct pushes to `main`; shared-package edits without ADR and downstream re-run.
**Self-check to paste in your reply:** (a) `gh pr checks` table, all green; (b) acceptance outputs `P5/P7/P8/P9`; (c) for every test named in your report, the `grep` line proving it exists; (d) the attacks run on every new route, with captured outputs; (e) assignment checklist (done/partial/not done).

## Assignment (feature branch `feat/phase-6b-companion` from `main`; PR only; never push to `main`)
**Part A — close P10-A…P10-D** (see `VERDICT-P6A2.md`) in this same PR.
**Part B — Phase 6b: Companion PWA core** (MASTER_PLAN §6.8/M8; `apps/companion` or a route group in `apps/web`, decision recorded in an ADR), using the generated contracts client, `@vigil/ui` and i18n:
1. **Plain-language result explainer** driven only by M5 verified narratives and M3 verdicts (explained / needs_repeat / escalate); never a diagnosis; no "dismissed"; reading-level and length checks as tests.
2. **Second-Look Request**: patient/caregiver asks for a result to be re-reviewed; creates a follow-up task via the real API, audited, consent-checked.
3. **Bad-news mode**: opt-in gated disclosure, clinician-controlled release, safe wording; tests for every gated path.
4. **Symptom diary** (text; voice only if the browser API exists, otherwise a documented fallback), stored via the API with consent.
5. **Caregiver sharing**: scoped, revocable, audited access; attack it (revoked link, wrong patient, expired, replay).
6. **Offline-capable PWA** (service worker, manifest, queue replay through `/sync/batch`); en-NG complete, Pidgin/Yoruba/Hausa/Igbo present and marked unreviewed.
7. **Tests**: real-API Playwright for every journey above (consent withdrawal, revoked share, offline), axe, Lighthouse per distinct view with budgets enforced in CI, screenshots in `docs/design/screens/`.
Do **not** start OCR, M4, M7/M10 or research-backlog modules.
**Deliver:** `docs/progress/PHASE-6B-REPORT.md` (each `MET` cites an existing passing test; full checklist), ADRs, ledger/STUBS, green CI table.
**Reply only with:** the five self-check items; verbatim summaries of every acceptance suite (`p5/p7/p8/p9`, `p4` incl. `VIGIL_CONTRACT_P4V2=1`, `3b`, `k1` incl. v2); everything not made real. **The overseer will attack the API and drive the UI against the real server.**
