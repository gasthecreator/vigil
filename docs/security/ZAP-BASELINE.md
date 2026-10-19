# ZAP baseline triage (G-07)

Nightly / `workflow_dispatch` workflow: `.github/workflows/zap-baseline.yml`.

## How it runs
1. Starts the seeded e2e API (`scripts/run_e2e_server.py`) on `127.0.0.1:8000` with `ENVIRONMENT=local` / `REQUIRE_AUTH=false` (research prototype profile).
2. Runs OWASP ZAP baseline against that origin.
3. Uploads the HTML/JSON report as a CI artefact; a short summary is written to `reports/quality/ZAP_SUMMARY.json` when the helper step runs.

## Expected findings on the local profile
The local e2e profile deliberately disables production auth. ZAP will typically flag:
- Missing security headers (CSP, HSTS, X-Frame-Options) on the FastAPI default responses.
- Cookie / session notions that do not apply to bearer-JWT API routes.
- Absence of HTTPS (loopback HTTP only).

These are **accepted on the local/e2e profile** and are not production claims. Production compose (`infra/.env.compose.example`) requires auth secrets and is the profile that must stay hardened (PR1).

## Triage rule
| Severity | Action |
|---|---|
| High/Critical on authenticated production-shaped routes | Open/keep a hazard; block release |
| Informational / low on local e2e | Document here; do not reword as “clean” |
| False positive | Note evidence and keep the ZAP rule id |

## Last triage note
Initial wiring (P16 PR2): baseline job added; first green/red run evidence lives in the workflow run artefacts, not hand-edited into this file.
