# Vigil documentation index

Organised by who is reading and why. `docs/MASTER_PLAN.md` is the single canonical plan; everything else points to it rather than restating it. Living documents are kept true by CI (`scripts/check_docs_links.py`, `scripts/check_claims.py`, `scripts/check_evidence.py`, `scripts/reality_audit.py`); historical documents are kept as written and carry an erratum when they were wrong.

## I want to understand what Vigil is and what it may claim
- [`DISCLAIMER.md`](DISCLAIMER.md), [`regulatory/INTENDED_USE.md`](regulatory/INTENDED_USE.md) (draft, unreviewed)
- [`MASTER_PLAN.md`](MASTER_PLAN.md) (plan, standards, definition of success), [`ML_PROGRAM.md`](ML_PROGRAM.md) (the ML/statistics program)
- [`EVIDENCE.md`](EVIDENCE.md) and [`evidence/`](evidence/) (what is known vs. only claimed), [`REALITY_RULES.md`](REALITY_RULES.md), [`STUBS.md`](STUBS.md)

## I want the current state and open work
- [`PROGRESS.md`](PROGRESS.md) (phase ledger; verdict and maturity columns are overseer-owned), [`progress/`](progress/) (phase reports and verdicts), `docs/STATUS.md` once generated (not yet present on this branch)
- [`HANDOVER.md`](HANDOVER.md) (what only a human can do)
- [`audits/`](audits/) (repo-standards audits; `REPO-AUDIT-P15.md` is script-written)

## I am a developer
- Decisions: [`adr/`](adr/) (one per significant decision), proposals: [`proposals/`](proposals/)
- API: [`api/openapi.json`](api/openapi.json) (generated), design screens: [`design/`](design/)
- ML contracts and model cards: [`ml/`](ml/) (M4 ladder: [`M4-CONTRACT.md`](ml/M4-CONTRACT.md), [`M4-WORKED-EXAMPLES.md`](ml/M4-WORKED-EXAMPLES.md); K5 harmonisation: [`experiments/EXP-K5-001/CONCLUSION.md`](../experiments/EXP-K5-001/CONCLUSION.md); K4 deep families: [`experiments/EXP-K4-001/CONCLUSION.md`](../experiments/EXP-K4-001/CONCLUSION.md); K6 active sensing: [`experiments/EXP-K6-001/CONCLUSION.md`](../experiments/EXP-K6-001/CONCLUSION.md); M12 federated/DP: [`experiments/EXP-M12-001/CONCLUSION.md`](../experiments/EXP-M12-001/CONCLUSION.md); OCR lab drafts: [`experiments/EXP-OCR-001/CONCLUSION.md`](../experiments/EXP-OCR-001/CONCLUSION.md)), [`model_cards/`](model_cards/) and the older [`models/`](models/) (duplicate cards; consolidation tracked in the repo audit)
- Studies: pre-registrations in [`studies/`](studies/) and `experiments/EXP-*/`; results are written only by their scripts

## I operate it
- [`deployment/ON_PREM_INSTALL.md`](deployment/ON_PREM_INSTALL.md), [`runbooks/`](runbooks/), [`resilience/DISASTER_RECOVERY.md`](resilience/DISASTER_RECOVERY.md), [`operations/`](operations/)
- Release: [`release/REPRODUCIBILITY.md`](release/REPRODUCIBILITY.md), [`release/SIGNING.md`](release/SIGNING.md), [`release/COMPATIBILITY.md`](release/COMPATIBILITY.md)
- GitHub configuration: [`ops/GITHUB-SETTINGS.md`](ops/GITHUB-SETTINGS.md)

## I review safety, security, privacy
- [`clinical/SILENT-MODE.md`](clinical/SILENT-MODE.md) (silent-mode design, operation and limits), [`clinical/PILOT/`](clinical/PILOT/) (stop rules, training, incident template, go/no-go; all draft)
- [`safety/HAZARD_LOG.md`](safety/HAZARD_LOG.md) (verified by `scripts/verify_hazard_log.py`), [`risk/RISK-REGISTER.md`](risk/RISK-REGISTER.md)
- [`security/THREAT_MODEL.md`](security/THREAT_MODEL.md), [`security/VULNERABILITY_POLICY.md`](security/VULNERABILITY_POLICY.md)
- [`regulatory/`](regulatory/) (all `DRAFT-UNREVIEWED`), [`usability/`](usability/), [`clinical/`](clinical/), [`data/`](data/)

## Archive (not maintained)
- [`archive/`](archive/), [`prompts/`](prompts/) (instructions given to the executor per phase)
