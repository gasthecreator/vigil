# ADR-0034: SMART-on-FHIR remains deferred as a stretch item

- **Status:** Accepted with P16 PR5; Maturity remains L0.
- **Context:** SMART-on-FHIR is a stretch integration, not a prerequisite for the current local and partner-evaluation workflows. The repository does not have a deployed SMART authorization flow, registered client, production identity configuration, or conformance evidence.
- **Decision:** Defer SMART-on-FHIR implementation. Do not describe Vigil as SMART-on-FHIR integrated or conformant. Reconsider only when a named deployment partner supplies its FHIR endpoint, SMART authorization requirements, test environment, and an accountable security/clinical integration owner; then document the scope and validate the integration against that environment before making an integration claim.
- **Consequences:** No SMART launch flow, FHIR resource synchronization, or SMART conformance claim is delivered by this decision. Existing API and partner-ingest capabilities do not imply SMART support. Maturity remains L0.
- **Evidence:** `docs/audits/PLAN-GAP-ANALYSIS.md` G-28 and `docs/prompts/PROMPT-P16.md` PR5.
