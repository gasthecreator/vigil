# Localisation (en-NG, Pidgin, Yoruba, Hausa, Igbo)

> Machine-drafted strings for pcm / yo / ha / ig are **unreviewed**. English (en-NG) is the source locale. Native-speaker clinician/community validation is a human action (HANDOVER **H-118**). Until then the UI shows an unreviewed banner and glossary definitions carry an `[UNREVIEWED DRAFT]` marker.

## Where things live

| Artefact | Path |
|---|---|
| Runtime dictionaries | `packages/ui/src/i18n/translations/{en-NG,pcm,yo,ha,ig}.ts` |
| Review-state ledger | `packages/ui/i18n/review_state.json` |
| Medical glossary | `packages/ui/i18n/glossary/terms.json` (MASTER_PLAN §10.4) |
| CI gate | `scripts/check_i18n_review_state.py` |
| Decision | `docs/adr/0029-i18n-review-state-and-glossary.md` |

## Rules

1. Add a UI string to **en-NG first**, then draft the other locales (or leave a clear English fallback). Update `review_state.json` in the same change; new pcm/yo/ha/ig keys start as `unreviewed`.
2. Do **not** set `metadata.isReviewed: true` or locale `status: "reviewed"` for pcm/yo/ha/ig without naming `reviewed_by` and flipping every string/glossary entry for that locale.
3. Glossary terms that are still unreviewed must keep `[UNREVIEWED DRAFT]` in the definition.
4. The review itself is H-118: a native-speaker clinician or community validator signs off; the executor does not invent a review.

## Check locally

```bash
uv run python scripts/check_i18n_review_state.py
```
