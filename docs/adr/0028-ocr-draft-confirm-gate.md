# ADR 0028: Local OCR lab importer is draft-only; the confirm body is the record

## Status
Accepted as an engineering decision. `DRAFT-UNREVIEWED` clinically. Synthetic reports only.

## Context
MASTER_PLAN §6.8 and the final-build prompt (Tier 2, S-015) require an open-source, local (no cloud) pipeline from photo/PDF to a *draft* structured result, with mandatory human confirmation before anything enters the record, confusion-prone fields highlighted, and an accuracy report on generated reports with injected noise.

An unconfirmed draft that became an observation would be a safety defect (wrong analyte, unit or decimal driving alerts). Cloud OCR would send identifiable health data off-box.

## Decision
1. **Upload is JSON** `{filename, content_type, content_base64}` (PNG, JPEG or PDF, 2 MiB). Multipart is not used so the route-policy matrix can send a valid body.
2. **Extraction is local.** PDF text layer via pypdf; images via Tesseract when the binary is installed. No network. A missing Tesseract binary still creates a draft with empty suggestions and `engine_missing`; the human types the values. Image OCR of PDF pages without a text layer is not implemented.
3. **Drafts are not observations.** `POST .../ocr-drafts` never writes `observations`. Confirm requires `confirmed: true` **and** human-reviewed `analyte_code`, `value`, `unit`, `specimen_collected_at`. The server ignores suggestion fields on confirm.
4. **Confirm is WRITERS only** (clinician, nurse_clerk, admin) so patients photographing a report cannot ingest labs (H24). Patients and caregivers may upload, list, and reject. Quality-lead may list.
5. **Accuracy is EXP-OCR-001** on generated print-style English reports. H1 (PDF) is a kill of the PDF arm. H2/H3 (images) do not kill the importer: a wrong suggestion is still a draft.

## Alternatives considered
- Multipart upload: rejected; the HTTP matrix cannot attach files today.
- Copy OCR suggestion into the observation when `confirmed: true` is the only field: rejected; that is an unreviewed commit of machine text.
- 503 when Tesseract is missing: rejected; it would make draft creation environment-dependent and block a human from typing the values.

## Consequences
- Hazard H27 records residual risk that a human confirms a wrong value (OPEN; usability unmeasured, H-117).
- Stub S-015 records what is built (confirm gate, synthetic accuracy) and what is not (real photographs, handwriting, non-English, PDF raster OCR).
