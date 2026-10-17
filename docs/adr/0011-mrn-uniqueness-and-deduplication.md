# ADR 0011: Medical Record Number (MRN) Uniqueness and Deduplication Policy

## Status
Accepted

## Context
In healthcare surveillance systems, patient identification integrity is paramount. Permitting duplicate Medical Record Numbers (MRNs) or external enterprise IDs can lead to chart fragmentation, misattribution of serial longitudinal biomarkers (e.g. CA 15-3 kinetics), corrupted Martingale sequential alerting ($K_2$), and potential HIPAA / NDPA data leakage.

During the Phase 6a review (`docs/progress/VERDICT-P6A.md`, defect 6), it was observed that `POST /api/v1/patients/` permitted registering two distinct patient records with the same plaintext MRN (and hence identical HMAC blind indices `mrn_bidx`).

## Decision
1. **Site-Level Uniqueness Enforcement:** An MRN uniquely identifies an individual patient within a clinical institution. When `POST /api/v1/patients/` or `PATCH /api/v1/patients/{id}` receives an `mrn`, the system computes the blind index `mrn_bidx = compute_blind_index(mrn)`.
2. **Conflict Prohibition:** If another patient record already exists with the same `mrn_bidx`, the API immediately rejects the operation with `409 Conflict`:
   ```json
   {
     "detail": "Patient with MRN already registered in surveillance database. Duplicate MRNs are prohibited by policy."
   }
   ```
3. **Database-Level Protection:** In addition to application-level validation before insertion, the blind index column `mrn_bidx` enforces an index constraint to prevent race conditions during concurrent patient onboarding.
4. **Patient Record Merging / Duplicate Resolution:** In the event of clerical duplicate creation in upstream hospital systems, reconciliation must be handled via an audited Administrative Linkage flow rather than silent record aliasing.

## Consequences
- **Positive:** Guarantees one-to-one mapping between clinical MRN and Vigil surveillance trajectory. Eliminates accidental observation misrouting and split-chart errors.
- **Positive:** Complies with Master Plan §11 and Condition P9-F.
- **Negative:** Callers attempting to re-enrol an already registered patient must query the existing record rather than re-creating it.
