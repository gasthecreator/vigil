# Model Card: OCR lab-report draft importer

**Model Identifier:** `MODEL-OCR-LAB-DRAFT`  
**Model Version:** Tier 2 local OCR (`feat/tier2-ocr-lab-importer`)  
**Date:** 2026-10-19  
**Module Reference:** API OCR draft routes; Tesseract local pipeline  
**Governing Documents:** ADR-0028, `experiments/EXP-OCR-001/`, hazard H27  
**Claim status:** Draft suggestions only. **Human confirm gate is mandatory** before values become observations. Synthetic accuracy study only.

---

## 1. Intended use
Parse uploaded lab-report images/PDFs into a **draft** the clinician/clerk must confirm or reject. Suggestions are ignored on confirm if the human posts different values (server-side).

## 2. Safety
- No auto-posting of OCR output to the clinical record.
- Silent mode: confirm path diverts per route policy.
- Hazard H27 tracks mis-read analyte risk.

## 3. Evaluation
`experiments/EXP-OCR-001/` — synthetic; not a clinical accuracy claim.
