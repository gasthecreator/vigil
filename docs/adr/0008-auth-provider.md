---
status: accepted
date: 2026-10-16
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0008. Authentication and Identity Provider Selection for Vigil Precision Oncology Platform

## Context and Problem Statement
The Vigil precision oncology decision-support platform (Master Plan §9.2, §11) requires strict, fine-grained access control across 6 core roles:
- `clinician`: oncologist/physician with full patient review, lab intake, and alert acknowledgement permissions.
- `nurse_clerk`: clinical coordinator with intake and outreach recording permissions.
- `quality_lead`: quality assurance director with missed-signal audit and alert review access.
- `admin`: hospital system administrator managing facilities and user accounts.
- `patient`: breast cancer survivor with access strictly limited to their own clinical record.
- `caregiver`: authorized family member/advocate with access strictly delegated via unexpired patient consent.

Additionally, Vigil operates across Nigerian tertiary and regional hospitals (e.g. LUTH, UCH) where network intermittent connectivity occurs and external SaaS authentication dependencies (e.g. Auth0, Firebase Auth) can cause clinical lockouts during internet outages.

We need an authentication and authorization architecture that supports:
1. Offline-capable local verification with zero cloud vendor lock-in.
2. Standard cryptographic token verification (JWT, RFC 7519).
3. Seamless bridging to hospital OAuth2 / OpenID Connect / SAML Enterprise IdPs (Keycloak, Microsoft Entra ID).
4. Strict consent enforcement at every patient clinical read.

## Decision Drivers
1. **Clinical Availability & Resilience:** Internet outages must not lock clinicians out of local workstations or hospital-hosted appliances.
2. **Data Sovereignty & Compliance:** Nigerian Data Protection Act (NDPA 2023) sensitive health data protections; hospital credentials must remain within institutional boundaries.
3. **Role & Consent Granularity:** Direct binding of role claims (`role`), facility multi-tenancy (`facility_id`), and patient identity (`patient_id`) within cryptographically verified tokens.
4. **Developer Experience & Testability:** Hermetic local development and deterministic testing without external network mocking.

## Considered Options
- **Option 1: Proprietary Cloud Identity SaaS (Auth0, Okta, Firebase Auth)**  
  *Pros:* Turnkey managed infrastructure, hosted login UI.  
  *Cons:* Hard dependency on external network access; monthly active user cost scaling; data leaves hospital jurisdiction; non-functional during regional fiber outages.
- **Option 2: Session-based cookie auth with centralized Redis**  
  *Pros:* Simple server-side invalidation.  
  *Cons:* Poor support for mobile/PWA companion apps and cross-service distributed architectures; complex offline token caching.
- **Option 3: Hybrid Architecture: Self-Contained JWT Bearer Auth with OpenID Connect (OIDC) Federation and Keycloak / Local Fallback (Selected)**  
  *Pros:*
  - Cryptographically signed stateless JWTs (RS256 / HS256) verified locally with zero network roundtrips.
  - Pluggable OIDC discovery enabling plug-and-play federation with hospital Keycloak instances or Entra ID in production.
  - Built-in local cryptographic token issuer in `apps/api/vigil_api/auth.py` providing hermetic testing and development.
  - Direct embedding of RBAC role claims and consent verification hooks.

## Decision Outcome
Chosen option: **Option 3: Self-Contained JWT Bearer Auth with OIDC Federation**.
1. **Token Standard:** JSON Web Tokens (JWT) signed with HMAC-SHA256 (local dev/staging) or RSA-256 (production Keycloak integration).
2. **Role Enforcement:** Strict FastAPI dependency injection factory `require_roles(*allowed_roles)`.
3. **Consent Interceptor:** Mandatory `verify_patient_consent` dependency on every patient-disclosing read endpoint.
4. **Unauthenticated Mutations:** Explicitly forbidden when `REQUIRE_AUTH=true` (enforced across production and staging profiles).
