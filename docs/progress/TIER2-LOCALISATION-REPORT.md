# Tier 2g report: localisation review-state and glossary

> Status: SUBMITTED FOR REVIEW. Verdict, maturity and every overseer column are untouched. Maturity stays L0. Native-speaker review is **not** claimed.

## Outcome in one paragraph
Patient-facing dictionaries for Pidgin, Yoruba, Hausa and Igbo already existed with an unreviewed banner. This item adds the machine-checkable ledger and medical glossary named in MASTER_PLAN §10.4: `packages/ui/i18n/review_state.json`, `packages/ui/i18n/glossary/terms.json`, CI via `scripts/check_i18n_review_state.py`, and HANDOVER H-118 for the human sign-off. Non-English locales stay `unreviewed`. No translation was marked reviewed by the executor.

## What was built
| Item | Where |
|---|---|
| Review-state ledger | `packages/ui/i18n/review_state.json` |
| Medical glossary | `packages/ui/i18n/glossary/terms.json` |
| CI / governance test | `scripts/check_i18n_review_state.py`, `tests/governance/test_i18n_review_state.py` |
| Docs | `docs/localization/README.md`, ADR-0029, stub S-017, H-118 |
| Header locale list | Driven from dictionary metadata (no hard-coded reviewed flags) |

## Findings and deviations
1. Glossary non-English definitions are English text wrapped in `[UNREVIEWED DRAFT]` rather than invented medical Yoruba/Hausa/Igbo/Pidgin. Inventing polished clinical copy without a native speaker would overclaim.
2. `metadata.unreviewedNotice` is optional on en-NG; the ledger records it as `absent` for that locale.

## Files changed outside this item's scope
CI workflow (one step), ledger row T2g (executor's own), STUBS/HANDOVER/CHANGELOG/README. `tests/acceptance_*`: untouched.
