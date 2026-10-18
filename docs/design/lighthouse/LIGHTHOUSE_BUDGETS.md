# Lighthouse UX & Accessibility Audit Report
**Master Plan §9.7 / Condition P9-C / P10-A**
**Audit Date:** 2026-10-18T00:45:16.494Z

## Committed Engineering Budgets
- **Performance Budget:** $\ge 90$
- **Accessibility Budget (WCAG):** $\ge 90$
- **Time to Interactive (TTI):** $\le 3500$ ms

| Audited View & Exact URL | Performance | Accessibility | TTI | Best Practices | SEO | Status |
|---|---|---|---|---|---|---|
| **TRIAGE** (`http://127.0.0.1:3000/`) | **99** | **100** | **2314 ms** | **96** | **100** | ✅ MET |
| **TIMELINE** (`http://127.0.0.1:3000/patients/PAT-001`) | **98** | **98** | **2094 ms** | **96** | **100** | ✅ MET |
| **CONTINUITY** (`http://127.0.0.1:3000/continuity`) | **99** | **98** | **2020 ms** | **96** | **100** | ✅ MET |
| **QUALITY** (`http://127.0.0.1:3000/quality`) | **99** | **100** | **1961 ms** | **96** | **100** | ✅ MET |
| **COMPANION** (`http://127.0.0.1:3000/companion`) | **99** | **98** | **1959 ms** | **96** | **100** | ✅ MET |
| **EXPLAINER** (`http://127.0.0.1:3000/companion/results/obs-001`) | **97** | **98** | **2564 ms** | **96** | **100** | ✅ MET |
| **SYMPTOMS** (`http://127.0.0.1:3000/companion/symptoms`) | **99** | **94** | **1957 ms** | **96** | **100** | ✅ MET |

## Committed Artifacts
- **TRIAGE View:** [`triage-report.html`](./triage-report.html) / [`triage-report.json`](./triage-report.json)
- **TIMELINE View:** [`timeline-report.html`](./timeline-report.html) / [`timeline-report.json`](./timeline-report.json)
- **CONTINUITY View:** [`continuity-report.html`](./continuity-report.html) / [`continuity-report.json`](./continuity-report.json)
- **QUALITY View:** [`quality-report.html`](./quality-report.html) / [`quality-report.json`](./quality-report.json)
- **COMPANION View:** [`companion-report.html`](./companion-report.html) / [`companion-report.json`](./companion-report.json)
- **EXPLAINER View:** [`explainer-report.html`](./explainer-report.html) / [`explainer-report.json`](./explainer-report.json)
- **SYMPTOMS View:** [`symptoms-report.html`](./symptoms-report.html) / [`symptoms-report.json`](./symptoms-report.json)

## Audit Methodology & Environment
- **Device Profile:** Desktop / Emulated High-DPI Display
- **Network / Throttling:** Real local loopback / unthrottled CPU benchmark
- **Zero-Dismissal & Watermark State:** Confirmed active and visible during audit.
