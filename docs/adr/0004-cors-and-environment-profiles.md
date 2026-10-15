---
status: accepted
date: 2026-10-14
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0004. Strict CORS Profiles and Environment Deployment Controls (Defects A5, A6)

## Context and Problem Statement
The prototype backend configured `CORS_ORIGINS = ["*", ...]` permitting unrestricted cross-origin requests, including from arbitrary malicious websites. Furthermore, an open data-seeding endpoint (`POST /api/v1/analytics/seed-demo-cohort`) was publicly exposed without authentication or environment gating, allowing unrestricted mutation of database state.

## Decision Drivers
- Protection of health data and clinical operational state.
- Elimination of wildcard CORS access in compliance with security baseline standards.
- Safe separation of local testing environments from staging/production deployments.

## Considered Options
- **Option 1: Retain wildcard CORS with a warning comment**
- **Option 2: Explicit environment-based CORS profiles and route gating**

## Decision Outcome
Chosen option: **Option 2: Explicit environment-based CORS profiles and route gating**.
- Wildcard CORS (`"*"`) is strictly prohibited and removed from all configuration files.
- Environment profiles (`ENVIRONMENT=local`, `staging`, `production`) govern allowable origins:
  - `local`: `http://localhost:3000`, `http://127.0.0.1:3000`.
  - `staging` / `production`: strictly defined FQDNs via environment variables.
- The demo cohort seeding route (`/api/v1/analytics/seed-demo-cohort`) is gated: it executes only when `ENVIRONMENT=local`. In all other profiles, it returns HTTP 403 Forbidden with an explanatory payload.

### Confirmation
Unit and integration tests verify that non-local environments reject the seeding route and that wildcard CORS headers are not emitted.
