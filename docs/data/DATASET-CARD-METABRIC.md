# Dataset Card: METABRIC (external; not bundled)

**Dataset Identifier:** `DATASET-METABRIC`  
**Access:** External — not redistributed in this repository  
**Date:** 2026-10-19  
**Governing Documents:** `docs/data/ACCESS.md`, MASTER_PLAN public-data loaders (Tier 1)

---

## 1. Description
METABRIC (Molecular Taxonomy of Breast Cancer International Consortium) is a publicly described breast cancer genomics / clinical cohort used in oncology research. Vigil may reference it via **documented loaders** when credentials/paths are configured by the operator; the raw dataset is **not** committed here.

## 2. Intended use in Vigil
Optional external evaluation / feature research. Not a substitute for partner prospective data (Phase 9). Any metrics computed on METABRIC must be labelled with the dataset id and must not be presented as Vigil clinical performance.

## 3. Limitations / ethics
- Access subject to the dataset’s own terms; follow `ACCESS.md`.
- Genomic features are out of scope for the shipped surveillance MVP unless an ADR says otherwise.
- No PHI from METABRIC is stored in Vigil’s default synthetic deployments.
