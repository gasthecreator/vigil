# P16 PR4 report — product gaps (G-20–G-24)

Status: SUBMITTED FOR REVIEW. Maturity remains L0. Acceptance tests, audit files, and `docs/MASTER_PLAN.md` were not edited.

## Delivered

- **G-20 / J8:** Added hash-verified K2 candidate governance, HMAC-attested silent-monitor reports, in-memory shadow evaluation, append-only hash-chained decision records, independent approval, replay refusal, promotion metadata, rollback, admin-only routes, and attack tests. Clinician inference routes are unchanged. See [ADR-0032](../adr/0032-j8-shadow-model-governance.md).
- **G-21 / J6:** Added a clinician/admin test-ladder workstation page, audited availability feedback POST and read history, and real-server Playwright coverage.
- **G-22:** Added Storybook 10.6.2, axe accessibility checks, RTL direction context and interaction test, user-initiated read-aloud with unsupported-browser fallback, plus a seeded-fail companion-route gzip gate. Measured bundle: 126,723 gzip bytes / 184,320 budget on macOS arm64.
- **G-23:** Added uncertainty/content policy and tests against M5 verbal bands and clinician narratives.
- **G-24:** Added usability moderator script, consent draft, alert-fatigue protocol, preregistration, and simulator-generated synthetic report. Seed 1624, 250 simulated patients, 80 alerts (0.32); this does not estimate clinical alert burden or utility.

## Verification

- `uv run ruff check .` — passed.
- Focused API/migration/silent-monitor checks — 51 passed; route-policy/security/content rerun — 59 passed.
- Full `uv run pytest` — 864 passed, 18 skipped; PostgreSQL-only migration cases skipped locally (CI runs its PostgreSQL service).
- All 12 CI acceptance suites — 86 passed in total.
- `npm run web:lint`, `npm run web:build` — passed.
- Companion gzip gate — 126,723 bytes; seeded failure confirmed above the 184,320-byte budget.
- Storybook build — passed; interaction/axe — 2 passed.
- Real-server Playwright e2e — 28 passed.
- MkDocs build and repository-wide docs links — passed (warnings remain for existing out-of-nav documents/relative links; the dedicated link checker passed with zero broken links).
- Generated API docs, indexes, card metrics, claims, evidence, excerpt, reality, i18n, and hazard checks — passed.
- `make reproduce` — passed, including study bit-diff, synthetic report verification, SBOM regeneration/diff, status freshness, and unsigned release-manifest verification.

## Limitations and deviations

- RTL test validates document direction behavior with an English sample; it does not establish Arabic translation quality.
- Read-aloud is browser speech synthesis, not a clinical accessibility validation.
- Governance operates on admin-supplied live-format series and stores aggregate metrics only; this is not evidence of model safety or clinical validity. HMAC report signing uses the configured JWT secret.
- Storybook 10 requires Node.js 20.19 or newer; root engine and CI Node pins were raised accordingly. Full npm audit still reports 7 high and 2 moderate development-tree advisories in the existing Tailwind 3 / ESLint dependency chain; the forced fix requires Tailwind 4. The CI production dependency audit reports zero vulnerabilities.
- No suppressions were added for this PR. Storybook emits existing-style `use client` bundler and large-chunk warnings; build succeeds.
