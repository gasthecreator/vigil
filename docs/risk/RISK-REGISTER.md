# Vigil — Risk Register

> **Document Status:** Active. Maintained per `docs/MASTER_PLAN.md` §17.5.  
> **L:** Likelihood (L = Low, M = Medium, H = High)  
> **I:** Impact (L = Low, M = Medium, H = High)

| ID | Risk | L | I | Mitigation Strategy | Owner |
|---|---|---|---|---|---|
| **R1** | Real clinical data never obtained from partners → no real clinical validation | M | H | Parallel multi-source acquisition (SEER, METABRIC, TCGA, Project Data Sphere); structured partner hospital proposal package; silent-mode architecture; honest labelling ensuring synthetic platform remains valuable as reproducible open software. | PO / Overseer |
| **R2** | Synthetic-to-real gap invalidates trained predictive methods | H | H | Multi-generator simulation (G1, G2, G3) with cross-generator validation; biological calibration targets; early public registry cross-checks (T-P tier). | Executor |
| **R3** | Oncology clinical guideline stance (serial tumor markers not recommended in asymptomatic early stage) hinders adoption | H | M | Position product around plausibility adjudication, loop closure, treatment continuity, and scarce resource allocation; generate prospective evidence rather than making premature claims. | PO / Clinical Lead |
| **R4** | AI agent/executor over-claims performance or declares completion prematurely | H | H | Strict MASTER_PLAN §0.4 and §16 rules; automated claims-policy CI (`scripts/check_claims.py`); exit-gate verification scripts (`scripts/verify_phase.py`); independent overseer review before phase acceptance. | Overseer / CI |
| **R5** | Alert fatigue and automation bias among overworked oncology clinicians | M | H | Conformal false-alarm budgets ($\alpha$-control); multi-tiered alerts (`watch`, `review`, `urgent`); mandatory disposition tracking; human-factors usability studies. | Clinical / UX Lead |
| **R6** | Privacy or data protection non-compliance (NDPA 2023, HIPAA, GDPR) | M | H | Formal DPIA draft; data minimization by design; full on-premise air-gapped installation capability; counsel review prior to live pilot. | DPO / Legal |
| **R7** | Offline and low-bandwidth client complexity underestimated | M | M | Early technical spikes in Phase 0/5; local-first PWA architecture with IndexedDB; automated airplane-mode end-to-end tests in CI. | Frontend Lead |
| **R8** | Radiotherapy harm model clinical evidence base is weak or heterogeneous | H | M | Transparent evidence-level tagging; parameter uncertainty intervals; sensitivity analyses; retain decision-aid / queue visualization fallback. | Research Lead |
| **R9** | Localisation errors in health explanations (Yoruba, Hausa, Igbo, Nigerian Pidgin) | M | H | Machine translation outputs strictly tagged as unapproved; mandatory native-speaker oncology nurse/clinician validation; fallback to English with visible flag. | Localisation Lead |
| **R10** | Maintenance burden and bus factor with solo product owner | H | M | Comprehensive Diataxis documentation; explicit ADR trail; fully automated CI/CD and verification; open-source contributor guides; simplified on-premise deployment. | PO / Community |
| **R11** | Dependency or supply-chain compromise | L | H | Pinned dependencies with lockfile hashes; CycloneDX SBOM generation; minimal external dependency policy; automated secret/vulnerability scanning. | Security / CI |
| **R12** | Emotional and psychological burden on product owner | M | M | Overseer review manages the evaluation rigor; development proceeds without artificial time pressure; nothing ships without product owner explicit comfort and sign-off. | Overseer |
