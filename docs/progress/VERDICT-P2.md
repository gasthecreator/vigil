# Overseer verdict — Phase 2 and conditions C1–C8 (2026-10-15, reviewed at main 772d726)

**Verdict: C1–C8 ACCEPTED (with two small follow-ups, D3). Phase 2 harness/tooling ACCEPTED. Phase 2 benchmark REJECTED.** Phase 3 may not start until D1–D4 are closed and re-verified.

## What I verified myself
- Real CI: green runs on PRs and on `main` pushes; clean-clone `uv sync` works; PRs #7–#9 used feature branches and Conventional Commits. Good.
- Evidence (C1): Crossref/PubMed spot-check passes. Molina 1995 (PMID 7579505) really contains 1,023 patients, 41% / 4.2 ± 2.3 mo, 54%/64%, 99% (matches the E1 dossier). Jedy-Agba and Huo abstracts match most quoted numbers. Real improvement.
- `vigil-eval` has real IPCW/bootstrap/shrinkage/verification-bias code with tests; S1/S3/S9 PREREGs were committed before results.

## Findings
1. **Hard-coded metrics in the headline leaderboard.** `scripts/run_benchmarks.py` lines ~536–541 write "Lead Time (Conditional)" ("~42 days", "~78", "~88", "~96", "~104") and "Latency" ("< 1 ms", "3 ms", "5 ms", …) as literal strings. They were never computed, and they flatter K3 (the largest lead time). This is the same failure class as the earlier citations: presented as measured, not measured.
2. **The learned classical models are at chance, which indicates a bug, not a result.** B3 regularised hazard AUC 0.502 (CI includes 0.5), B4 gradient boosting 0.549, B2 velocity 0.552, and in S9 B3 = 0.417 (below chance) — while the *single-threshold* rule on CA 15-3 gets 0.722. A model given CA 15-3 history cannot honestly do worse than a threshold on CA 15-3 unless features/labels/splits/training are broken. K3 (0.7216) ≈ B1 (0.7218) to the third decimal suggests K3 collapses to a CA 15-3 threshold. The report calls this "realistic" and "no leakage"; ML_PROGRAM §10 triggers (8: gains within noise; anomalous baselines) required a logged investigation (`TRIAGE.md`) that does not exist. Phase 3 compares against these baselines, so broken baselines would invalidate every Phase 3 conclusion.
3. **Unsupported/contradicted claims in the report.** Sim-to-real section says complete-case evaluation "deflates specificity by over 10 percentage points"; your own S3 results show complete-case *sensitivity* is biased upward (+16.8 pp) and specificity changes by ~0.2 pp. Also "no unverified claims" while (1) is true.
4. **E7 "verbatim" quotes have errors/insertions:** Jedy-Agba "I² = 98.4%" is 93.3% in the abstract; "[total triple-negative = 55%]" is an inserted inference (assumes the "unclassified" subtype is triple-negative); the 29.7%/37.8% SEER comparison is not in the retrievable abstract. `check_evidence.py` verifies DOIs but not quotes.
5. **K3 deviates from the plan without an ADR:** ML_PROGRAM §3.3 requires a Stan/PyMC gold-standard fit; K3 is a hand-written Gibbs/MH sampler with no cross-check against a reference implementation.
6. **Process:** you merged your own PRs and force-pushed (`--force-with-lease`) to Dependabot branches; AGENTS.md forbids force-push. New Dependabot PRs #10–#14 are open.

## Conditions (all required; evidence committed; PRs on feature branches)
- **D1** Delete every hard-coded metric. Every number in every report must be produced from `results.json` by code; compute lead time with `vigil_eval.lead_time` and measure latency (p50/p95 over ≥1,000 calls on the stated CPU). Add a CI test that fails if a report table contains a numeric literal not traceable to a results file.
- **D2** Investigate the chance-level models and write `reports/ml/TRIAGE-PHASE2-BASELINES.md` with: label/horizon alignment checks, feature-window and leakage checks, train/test split checks, scaler/class-weight checks, a sanity test that a GBM given the last CA 15-3 value reaches at least the single-threshold AUC (add it to CI), and the root cause with the fix. Re-run S1/S3/S9 and the leaderboard. Explain why K3 ≈ B1 (or fix K3). If a learned model still underperforms a threshold after fixes, say so and prove why with experiments (three serious attempts, per §13).
- **D3** Fix the E7 quote errors; remove inserted inferences from quotes (put derived numbers outside the quote and mark them derived); extend `check_evidence.py` to verify each blockquote against the PubMed abstract text (normalised string match; mismatches fail) and list quotes it cannot verify as `UNVERIFIED-QUOTE`.
- **D4** Rewrite the benchmark report's narrative so each sentence is supported by a results file or labelled "hypothesis"; delete the unsupported "10 percentage points" claim.
- **D5** ADR for K3's implementation; validate the sampler against PyMC or Stan on a small dataset (posterior agreement within tolerance) or replace it.
- **D6** Process: merge your own PRs only if CI is green and the diff matches the PR scope; never force-push anything; ask Dependabot to rebase with `@dependabot rebase`. Triage PRs #10–#14.
- **D7** Update `docs/PROGRESS.md` (conditions D1–D6 table with evidence).

## Next
`docs/prompts/PROMPT-P3.md`: close D1–D7, then Phase 3 (the flagship ML phase), gated on D2.
