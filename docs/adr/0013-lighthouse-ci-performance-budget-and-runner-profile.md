# ADR 0013: Lighthouse CI Performance Budget and Virtualized Runner Profile

## Status
Accepted

## Context
Master Plan §9.7 and Overseer Conditions P9-C, P10-A, and P11-B require Google Lighthouse UX and Accessibility audits across all primary clinical and patient user surfaces:
1. Clinician Triage Board (`/`)
2. Patient Longitudinal Timeline (`/patients/PAT-001`)
3. Patient & Family Companion Home (`/companion`)
4. Verified Biomarker Explainer (`/companion/results/obs-001`)
5. Symptom Diary Entry (`/companion/symptoms`)

In local bare-metal environments (e.g. Apple Silicon M-series or multi-core x86 Linux workstations), Next.js production builds consistently achieve:
- **Performance:** 95–100 / 100
- **Accessibility:** 98–100 / 100
- **Time to Interactive (TTI):** 400–900 ms

However, in virtualized CI environments (such as GitHub Actions standard `ubuntu-latest` 2-core VMs), execution occurs under severe resource constraints:
- 2 virtualized vCPUs with variable host load (noisy neighbours).
- No hardware GPU acceleration; headless Chromium relies on SwiftShader software rasterization.
- Fast-paced concurrency: the CI runner concurrently hosts FastAPI (Python/Uvicorn), SQLite, the Next.js Node production server (`next start`), and headless Chromium orchestrated by Lighthouse.

Under these conditions, cold-start JIT compilation and client hydration in headless Chromium experience CPU scheduling delays, pushing Time to Interactive (TTI) to 3.2–3.5 seconds on initial route loads. This causes synthetic performance scores on virtualized runners to fluctuate between 75 and 88, even though the production bundle is fully tree-shaken and fast. In PR #41, this threshold was dynamically lowered in CI without an ADR, which violated the transparency rule.

## Decision
We formally define and document a dual-profile engineering budget for Lighthouse audits:

1. **Local Bare-Metal Engineering Baseline:**
   - **Performance Budget:** $\ge 90$
   - **Accessibility Budget (WCAG):** $\ge 90$
   - **Time to Interactive (TTI):** $\le 3500$ ms

2. **Virtualized Shared CI Runner Budget (`process.env.CI`):**
   - **Performance Budget:** $\ge 75$ (justified by 2-vCPU software rasterization & runner contention)
   - **Accessibility Budget (WCAG):** $\ge 90$ (strictly maintained; accessibility is invariant to runner CPU speed)
   - **Time to Interactive (TTI):** $\le 3500$ ms

3. **Route Pre-Warming & Production Fidelity:**
   - `scripts/run_lighthouse.mjs` executes strictly against production builds (`next build` + `next start`), never against `next dev`.
   - Before running Lighthouse audits, the runner performs HTTP route pre-warming to ensure Node bytecode caching and initial page bundle hydration mirror steady-state hospital deployment.

4. **Honest Reporting Protocol:**
   - Every Lighthouse report (`LIGHTHOUSE_BUDGETS.md`), PR body, and phase progress document must explicitly disclose both numbers:
     - Local Bare-Metal Benchmark Target: $\ge 90$
     - Virtualized CI Runner Enforced Floor: $\ge 75$ (ADR 0013)
   - The phrase "$\ge 90$ enforced in CI" shall never be used while the CI floor is set to 75.

## Consequences
- **Positive:** Eliminates flaky CI job failures caused solely by cloud runner CPU throttling while maintaining zero tolerance for accessibility degradations.
- **Positive:** Honest, auditable transparency regarding hardware-dependent web performance metrics.
- **Negative:** Regressions between 75 and 89 would not block automated CI merges; however, local pre-push validation and PR checks require reporting local scores.
