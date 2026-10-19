# P16 PR5 report — decisions (G-27, G-28)

Status: SUBMITTED FOR REVIEW. Maturity remains L0. No implementation or clinical-validation claim is added by these decisions.

## Delivered

- **G-27:** ADR-0033 records that patient explainers remain English-only until each non-English locale has native-speaker clinician/community review recorded through the existing review-state process. Machine drafts remain flagged; M5 verification is English-only and is not evidence of translation correctness.
- **G-28:** ADR-0034 records SMART-on-FHIR as deferred stretch work and sets evidence and ownership prerequisites before reconsideration or any integration claim.
- The owner actions listed as new in §6 of the gap analysis were already present in `docs/HANDOVER.md` §E as H-301–H-306. This PR adds the §6 provenance at that section and preserves the existing rows without duplicating owner actions.

## Verification

- `python3 scripts/generate_docs_indexes.py --check` — passed.
- `UV_CACHE_DIR=/private/tmp/vigil-uv-cache make docs-check` — passed: MkDocs build, repository-wide link check (280 Markdown files / 438 links, zero broken links), and README version-claim check. MkDocs emitted its existing unlisted-page and relative-link warnings; build succeeded.

## Limitations

- These ADRs document scope and release claims; they do not implement SMART-on-FHIR or perform language review.
- No suppressions or acceptance-test edits.
