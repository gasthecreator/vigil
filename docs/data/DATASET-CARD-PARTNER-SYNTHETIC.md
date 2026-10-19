# Dataset Card: Partner-format synthetic evaluation set

**Dataset Identifier:** `DATASET-PARTNER-SYNTHETIC`  
**Data Tier:** `[SYNTHETIC]` — partner *schema* shape, synthetic values  
**Date:** 2026-10-19  
**Governing Documents:** ADR-0021 (partner evaluation toolkit), `docs/clinical/PREREGISTRATION.md`, Tier 1 partner packet

---

## 1. Description
Synthetic patients and observations generated to match the **field layout and coding conventions** expected from a partner site, without using real patient data. Used to dry-run ingestion, silent mode, and evaluation tooling before T-R data arrive.

## 2. Relationship to G1–G3
Mechanistic generators G1–G3 (`DATASET-CARD-SYNTHETIC-G1-G3.md`) stress physiological dynamics. This card covers the **partner-shaped** synthetic bundle used for integration and governance drills (toolkit paths under partner packet / Tier 1 artefacts).

## 3. Intended use
- Validate loaders, consent, and silent-mode diversion on realistic schemas.
- Never report partner-synthetic metrics as real-world clinical performance.

## 4. Limitations
Until real partner data exist, external validity is unknown. Silent mode and stop rules in `docs/clinical/PILOT/` still apply when any real data are introduced.
