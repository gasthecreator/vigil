# M1 model card — withdrawn

**Status:** QUARANTINED; no supported model is available.

**Decision:** [ADR-0051](../adr/0051-quarantine-unsupported-m1-priors.md)

**Stub registry:** [S-020](../STUBS.md)

This duplicate card is withdrawn. Its former claims did not match the source implementation: subtype proportions differed, unsupported age/stage adjustments were present, normal approximations were called credible intervals, and confidence/latency claims lacked suitable supporting evidence. See the canonical [withdrawn M1 card](../models/MODEL-CARD-M1.md).

Do not use old M1 outputs or M1-derived results for inference, patient care, model selection, or as calibrated probabilities. The package prediction methods and M4 conversion helper fail closed; the API route was already quarantined under ADR-0041. E12 remains secondary pending reconciliation of its population, denominators, subtype estimates, and intended estimand. No replacement priors or performance claims are asserted.
