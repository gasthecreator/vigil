# `packages/ui/i18n`

Committed review ledger and medical glossary for Vigil localisation (MASTER_PLAN §10.4, ADR-0029).

Runtime string tables stay in `../src/i18n/translations/`. This directory is the **honesty layer**: which locales and terms have been reviewed by a native-speaker clinician/community validator.

- `review_state.json` — locale / string-key / glossary-term status
- `glossary/terms.json` — clinical terms; unreviewed locales keep `[UNREVIEWED DRAFT]`
- Human review: `docs/HANDOVER.md` H-118
- CI: `scripts/check_i18n_review_state.py`
