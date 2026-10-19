# Runbook: Consent gate failure

**Alert:** Patient-scoped read succeeded without active consent, or consent withdrawal ignored over HTTP.  
**Related:** ADR-0023, security suite, SLO “Consent gate”.

## Immediate
1. Identify the route and role from access logs (`X-Request-ID`).
2. If partner data: revoke affected share tokens and rotate JWTs if issuance was compromised.

## Diagnose
1. Run `tests/security/test_route_policy_full_matrix.py` and acceptance consent suites.
2. Diff `ROUTE_POLICY` vs OpenAPI for the leaking path.
3. Confirm consent middleware order (auth → consent → handler).

## Recover
1. Deny by default on the route; ship a fix with a failing-then-passing test.
2. Re-verify withdrawal: after consent revoke, subsequent reads must 403/404 per contract.

## Verify
Matrix test green; spot-check companion share token revocation.
