---
status: accepted
date: 2026-10-14
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0003. Claims Policy and Truth Reset (Defects A2, A11, A12)

## Context and Problem Statement
The original repository contained unevidenced marketing claims and puffery ("enterprise-grade", "production-ready", "frontier-grade", "zero compromises", "ROC-AUC 1.000"), had no clinical disclaimers, and presented synthetic demonstration data without labeling it as synthetic. In a clinical decision-support system, unevidenced claims or misleading reassurances can cause tangible physical harm to patients.

## Decision Drivers
- Non-negotiable Principle 1 (Truth over impressiveness).
- Non-negotiable Principle 2 (Safety before features).
- Compliance with regulatory guidance (FDA CDS guidance, NDPA 2023).

## Considered Options
- **Option 1: Informal editorial review of documentation**
- **Option 2: Strict Claims Policy enforced by automated CI gating**

## Decision Outcome
Chosen option: **Option 2: Automated Claims Policy & CI Gating**.
- All unevidenced badges and puffery are purged from documentation, README, and user interfaces.
- `scripts/check_claims.py` scans every commit for forbidden phrases ("detects metastasis", "predicts cancer", "enterprise-grade", "production-ready", etc.) and personal/machine-specific absolute paths.
- Mandatory `docs/DISCLAIMER.md` is instituted and rendered on every UI view and API payload.
- Every synthetic entity, endpoint, and chart carries an explicit `synthetic: true` label.

### Confirmation
`scripts/check_claims.py` runs in CI and as part of `make verify-phase`.
