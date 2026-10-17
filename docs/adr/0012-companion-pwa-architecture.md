# ADR 0012: Family & Patient Companion PWA Architecture (apps/web Route Structure)

## Status
Accepted

## Context
Master Plan §6.8 (Module M8) defines the Family & Patient Companion as an installable, offline-first Progressive Web Application (PWA). Its purpose is to empower breast-cancer patients and family caregivers with:
1. Plain-language biomarker result explanations driven by M3 plausibility verdicts and M5 template narratives.
2. Second-Look Request generation and clinic hand-off summaries.
3. Bad-news mode (gated disclosure and calm verbal uncertainty bands).
4. Structured symptom diary with audio/voice accessibility.
5. Scoped, revocable caregiver access sharing.
6. Offline capability via Service Worker, IndexedDB storage, and `/api/v1/sync/batch` replay.

The phase assignment offers the choice between creating a separate sub-project (`apps/companion`) or implementing the companion interface as a dedicated route hierarchy within the existing Next.js web application (`apps/web/src/app/companion/...`), requiring the rationale to be recorded in an ADR.

## Decision
We choose to implement the Family & Patient Companion within `apps/web` under the dedicated `/companion` route hierarchy (`apps/web/src/app/companion/...`).

### Architectural Rationale
1. **Monorepo Cohesion & Shared Components:** Both the Clinician Workstation (M9) and Patient Companion (M8) consume the `@vigil/ui` design system and the generated OpenAPI TypeScript client (`@vigil/contracts`). Hosting both in `apps/web` eliminates duplicate build pipelines, duplicated `next.config.js` setups, and duplicate Tailwind styling bundles.
2. **Simplified On-Premise & Hospital Deployment:** Master Plan §9.2 and §9.5 require Vigil to be deployable on single-server on-premise hospital environments. Serving both clinician and patient interfaces from a single Next.js web service on port 3000 eliminates multi-container port mapping complexities, secondary reverse-proxy configs, and cross-origin CORS overhead between frontend surfaces.
3. **Unified Real-API E2E Testing:** Critical clinical workflows cross between clinician and patient roles (e.g. Clinician records a laboratory spike $\to$ Patient reviews plain-language explainer $\to$ Patient files a Second-Look Request $\to$ Clinician views new task on the Follow-Up Guardian board). A single Next.js application allows Playwright E2E tests to execute cross-role journeys against a real seeded backend without orchestrating multiple independent Node.js web servers.
4. **Clean Role and UX Isolation:** While sharing the underlying build, the companion routes are completely isolated under `/companion`:
   - Dedicated patient-facing layouts (`apps/web/src/app/companion/layout.tsx`).
   - Strict avoidance of raw alarming risk percentages in favor of verbal uncertainty bands and calibrated actions.
   - PWA manifest (`public/manifest.json`) and service worker (`public/sw.js`) specifically tailored for offline mobile caching and background sync queue replay.

## Consequences
- **Positive:** Reduces build time, minimizes bundle overhead, and accelerates end-to-end testing of cross-surface clinical journeys.
- **Positive:** Enables consistent auditing of both clinician and companion pages in a single automated Lighthouse and axe-core execution.
- **Negative:** Client bundle must ensure route-splitting effectively isolates clinician triage charts from mobile patient views (guaranteed by Next.js 14 App Router route-level code splitting).
