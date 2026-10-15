# Security Policy — Vigil

> **Status:** Active. Aligned with OpenSSF Best Practices and ISO/IEC 29147.

Vigil is a safety-relevant health project. We take security vulnerabilities seriously, especially those concerning health data privacy (under NDPA 2023, HIPAA, GDPR), authorization bypasses, or integrity of clinical decision-support logic.

## Supported Versions
| Version | Supported | Description |
|---|---|---|
| `main` (trunk) | Yes | Current active development |
| < 0.2.0 | No | Legacy prototype |

## Reporting a Vulnerability
**Do NOT open a public GitHub issue.**

Please report security issues privately via:
1. GitHub Security Advisory: Navigate to the **Security** tab of `gasthecreator/vigil` and select **Report a vulnerability**.
2. Email: Send encrypted or plain reports to `gideonsanni2023@gmail.com` with the subject line `[SECURITY] Vigil Vulnerability Report`.

Please include:
- Affected component or package (`apps/api`, `packages/vigil-core`, etc.).
- Commit SHA or version.
- Step-by-step reproduction instructions or proof of concept.
- Assessment of potential clinical, privacy, or system impact.

## What to Expect
- **Acknowledgement:** Within 48 hours.
- **Triage & Assessment:** Within 7 business days.
- **Coordinated Disclosure:** We aim to remediate all verified vulnerabilities within 30 to 90 days depending on severity before public disclosure.
- **Recognition:** Reporters who practice responsible disclosure will be credited in our security advisories and CHANGELOG.

## Scope
- **In Scope:** Application code in `apps/`, domain packages in `packages/`, CI workflows in `.github/`, Docker/infra configurations.
- **Out of Scope:** Volumetric DoS attacks, physical attacks, social engineering, issues in third-party cloud services outside our configuration.

## Safe Harbor
Good-faith security research in compliance with this policy is protected under safe harbor; we will not initiate legal action against researchers acting in good faith.
