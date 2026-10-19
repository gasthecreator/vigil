# ADR 0029: i18n review-state ledger and medical glossary

## Status
Accepted as an engineering decision. Native-speaker review of pcm / yo / ha / ig is **not** done (HANDOVER H-118).

## Context
MASTER_PLAN §10.4 and the final-build Tier 2 localisation item require:

- Languages: en-NG, Nigerian Pidgin, Yoruba, Hausa, Igbo for patient-facing flows.
- Machine translation may draft; humans approve; unapproved strings stay visibly marked.
- A medical terminology glossary per language under `packages/ui/i18n/glossary`.

Phase 6b already shipped dictionaries with an unreviewed banner. What was missing was a **machine-checkable** review ledger and the glossary path the plan names.

## Decision
1. **Review state** lives in `packages/ui/i18n/review_state.json` (locale, per UI string key, per glossary term). Non-English locales stay `unreviewed` until H-118.
2. **Glossary** lives in `packages/ui/i18n/glossary/terms.json`. Unreviewed locale definitions keep an `[UNREVIEWED DRAFT]` prefix; English is the source.
3. **CI** runs `scripts/check_i18n_review_state.py` so a locale cannot be marked reviewed while its strings are still unreviewed, and so new keys cannot be added without a review-state row.
4. **Runtime** still uses `packages/ui/src/i18n/translations/*.ts`; `metadata.isReviewed` must match the ledger.

## Alternatives considered
- Only a banner, no ledger: rejected; the banner can be removed without a record.
- Inventing polished Yoruba/Hausa/Igbo/Pidgin medical copy without a native speaker: rejected; that would overclaim.

## Consequences
- Stub S-017 records what is built (ledger + glossary + CI) and what is not (human review).
- HANDOVER H-118 is the only way to flip a non-English locale to reviewed.
