# P16 PR3 report — operations and docs (G-08, G-09, G-10, G-12, G-25, G-26)

> Status: SUBMITTED FOR REVIEW. Maturity stays L0. Overseer audit files and acceptance tests untouched.

## Outcome
Prometheus `/metrics`, `/live`/`/ready`, optional OTel (off by default), SLOs + alert runbooks, MkDocs Material Diataxis site (CI build + link check), tag-triggered release workflow, NOTICE + licence inventory, README version-claim gate, `apps/worker` shim + ADR-0031 (vigil-opt deferred), model/dataset cards, and this A1–A17 closure table.

## Evidence
| Gap | Artefact |
|---|---|
| G-08 | `mkdocs.yml`, `docs/diataxis/index.md`, `make docs-build` / `docs-check`, CI job `docs-site` |
| G-09 | `vigil_api/observability.py`, `/live` `/ready` `/metrics`, `docs/operations/SLOS.md`, runbooks under `docs/runbooks/` |
| G-10 | `.github/workflows/release.yml`, `NOTICE`, `scripts/generate_licence_inventory.py`, `scripts/check_readme_version_claims.py` |
| G-12 | `apps/worker/`, `docs/adr/0031-worker-and-vigil-opt-layout.md` |
| G-25 | `docs/models/MODEL-CARD-{K7,M4,M7,M10,OCR}.md`, `docs/data/DATASET-CARD-{METABRIC,TCGA-BRCA,PARTNER-SYNTHETIC}.md`; `model_cards/` remains symlink |
| G-26 | A1–A17 table below |

## Gate fail-then-pass
| Gate | Fail (seed) | Pass |
|---|---|---|
| README version claims | `uv run python scripts/check_readme_version_claims.py --seed-fail` | same without flag |
| Licence inventory | `uv run python scripts/generate_licence_inventory.py --seed-fail` | same without flag |
| Docs links | plant a broken link (manual) / CI uses `check_docs_links.py` | `python3 scripts/check_docs_links.py` |
| MkDocs | broken `mkdocs.yml` nav path | `uv run --group docs mkdocs build` |

## Deviations
1. **`/live`, `/ready`, `/metrics` use `include_in_schema=False`** until overseer extends `acceptance_p14` `PUBLIC_EXACT` ([PROP-0007](../proposals/PROP-0007-observability-public-probes.md)). Endpoints work; OpenAPI omits them temporarily.
2. **`packages/vigil-opt` not extracted** — ADR-0031.
3. **Cosign** runs only when `COSIGN_PRIVATE_KEY` secret exists (owner).
4. **MkDocs `strict: false`**; link integrity is `check_docs_links.py` (full tree), not MkDocs nav-subset strict mode.

## A1–A17 closure table (G-26)

| ID | Finding (short) | Status | Evidence |
|---|---|---|---|
| A1 | Circular `is_anomaly` training label | CLOSED | Simulation Lab labels with horizons; PHASE-1 report; `vigil-sim` / features pipeline |
| A2 | Headline ROC-AUC 1.000 / meaningless R² | CLOSED | Claims purged; `scripts/check_claims.py`; PHASE-0 §9 |
| A3 | Bidirectional LSTM for forecasting | CLOSED | Forward-only encoders; K4 rebuild; PLAN-GAP-ANALYSIS; MODEL-CARD-K4 |
| A4 | Hard-coded personal DB path | CLOSED | `vigil_api/config.py` relative default; PHASE-0 |
| A5 | CORS `"*"` | CLOSED | Strict `CORS_ORIGINS`; PHASE-0 |
| A6 | Unauthenticated seed / open mutations | CLOSED | Auth + route policy; acceptance P14; seed gated to `local` |
| A7 | Magic threshold 0.75 | CLOSED | `CLINICAL_ALERT_THRESHOLD` setting; PHASE-0 |
| A8 | Pickled model artifacts in runtime | CLOSED | Quarantine + ADR-0002; no pickle exchange policy |
| A9 | Thin evaluation | CLOSED | Broad pytest / acceptance suites in CI |
| A10 | Zero governance files | CLOSED | LICENSE, CI, CODEOWNERS, SECURITY, ADRs, etc. |
| A11 | Puffery / unverifiable badges | CLOSED | README reset; claims CI; version-claim gate (this PR) |
| A12 | No disclaimer / synthetic labelling | CLOSED | `DISCLAIMER.md`, API `is_synthetic`, UI badges |
| A13 | Five analytes, no units/LOINC/symptoms | CLOSED | Phase 1 analyte registry / sim; PHASE-1 report |
| A14 | Stub `sentinel_backend` package | CLOSED | Removed; PHASE-0 |
| A15 | Triage by risk only | CLOSED | Urgency / action ranking since Phase 5b; ADR-0019 for RT |
| A16 | Machine-specific README paths | CLOSED | Make/`uv` quickstart; PHASE-0 |
| A17 | “Complete” after one pass | CLOSED | Progress ledger process §16; no completion claims without verdict |

## Pending human
- PROP-0007 (P14 public allowlist)
- Tag `v*` to exercise `release.yml`; cosign key (H-209 / H-304)
- H-305 dependency graph (from PR2)
