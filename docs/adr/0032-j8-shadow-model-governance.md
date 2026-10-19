# ADR-0032: J8 shadow model governance

- **Status:** Proposed with P16 PR4; Maturity remains L0.
- **Context:** Candidate model changes need evidence, independent approval, integrity protection, and rollback without changing clinician inference routes.
- **Decision:** Admin-only governance endpoints accept a silent-monitor report signed with the configured server HMAC key. A hash-verified candidate allowlist evaluates aggregate alert-rate criteria over in-memory live-format series. Reports cannot be reused. Append-only, hash-chained records capture evaluation, second-admin approval, promotion, and rollback. The active governance pointer is metadata only; the clinical inference route remains unchanged.
- **Consequences:** This is operational governance plumbing, not clinical validation. HMAC key custody and monitor availability remain deployment responsibilities. Evaluation series are not persisted; only aggregate counts, provenance, hashes, and decision metadata are stored. Candidate allowlist updates require code review and regenerated hashes.
- **Evidence:** `apps/api/vigil_api/model_governance.py`, `apps/api/tests/test_model_governance.py`, migration `010_product_governance`.
