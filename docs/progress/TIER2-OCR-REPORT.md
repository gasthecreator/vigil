# Tier 2f report: local OCR lab importer (S-015)

> Status: SUBMITTED FOR REVIEW. Verdict, maturity and every overseer column are untouched. Maturity stays L0. `DRAFT-UNREVIEWED`. Synthetic generated reports only.

## Outcome in one paragraph
A local (no cloud) pipeline turns a PNG, JPEG or PDF into an `OcrDraft`. **An unconfirmed draft is not an observation.** Confirm requires `confirmed: true` and human-posted analyte, value, unit and specimen time; the server ignores OCR suggestions. EXP-OCR-001 on 40 generated print-style English reports (seed `20261019`): PDF exact-match 1.000 (H1 met); clean PNG 1.000 (H2 met); JPEG 1.000, rotate 0.975, speckle 0.825 (H3 met). Kill did not fire. These rates are not a claim about real laboratories, photographs or handwriting.

## What was built
| Item | Where |
|---|---|
| Pre-registration, committed alone | `experiments/EXP-OCR-001/PREREG.md` (commit `27704e4`) |
| Extractor, parser, synthetic renderer | `apps/api/vigil_api/ocr.py` |
| Draft routes + confirm gate | `apps/api/vigil_api/api/endpoints/ocr_drafts.py`, ADR-0028 |
| HTTP attack tests (no Tesseract) | `apps/api/tests/test_ocr_http.py` |
| Frozen accuracy | `scripts/run_ocr_accuracy.py` → `experiments/EXP-OCR-001/results.json` |
| Companion vault + clinician confirm panel | `apps/web/src/app/companion/vault/page.tsx`, `apps/web/src/components/OcrDraftsPanel.tsx` |
| Hazard H27 (OPEN) | `docs/safety/HAZARD_LOG.md` |

## Findings and deviations
1. PREREG said a missing Tesseract binary could 503 image uploads. ADR-0028: drafts are still created with `engine_missing` so a human can type values; the matrix test must not depend on Tesseract.
2. PDF pages without a text layer are not raster-OCR'd (no poppler). Empty suggestions, human types.
3. Image H2/H3 met on this high-contrast typed set. That does not license real photos.
4. Confirm is WRITERS only so photographing a report does not reopen H24.

## Files changed outside this item's scope
Route-policy table, OpenAPI/TS client, CI Tesseract apt step, hazard verifier citations, study-reproducibility PDF-arm check, ledger row T2f (my own). `tests/acceptance_*`: untouched.
