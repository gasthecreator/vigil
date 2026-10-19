# Owner script — synthetic hospital demo

**Audience:** product owner showing Vigil to a hospital lead.  
**Data:** synthetic only (`synthetic=true` on every seeded patient).  
**Claim boundary:** this is a research prototype walkthrough, not evidence of clinical performance.

Prerequisites: `make setup` once. Then `make demo` (starts API `:8000` and workstation/companion `:3000`).

---

## Opening (30 seconds)

1. Open `http://127.0.0.1:3000/` and point to the **synthetic** banner. Say: “Everything you see is seeded demo data. No real patient records are in this build.”
2. State what Vigil is: a breast-cancer follow-up **decision-support** research platform. It does **not** diagnose, treat, or replace a clinician.

---

## Journey A — Surprising lab result → adjudication → follow-up → family explanation (~5 min)

1. Open `http://127.0.0.1:3000/patients/PAT-001`.
2. Show the timeline / observations. Note any alert or risk panel is on **synthetic** history.
3. If an observation is open for M3 adjudication, walk the **confirm-by-repeat / escalate** options. Emphasize: the system never silently dismisses a surprising result (no-dismissal policy).
4. Optional: open OCR drafts on the patient page — upload is local; confirm requires a human to type analyte, value, unit and time (drafts never become results alone).
5. Open companion: `http://127.0.0.1:3000/companion`. Show the plain-language path and that **bad news stays locked** until a clinician unlocks disclosure.
6. Note localisation: Pidgin/Yoruba/Hausa/Igbo strings exist but are **unreviewed machine drafts** (banner / review ledger). Do not claim native-speaker validation.

---

## Journey B — Radiotherapy scheduler view (~2 min)

1. Open `http://127.0.0.1:3000/continuity` (or the continuity/RT route in the nav).
2. Point at the **`unvalidated in simulation`** badge on CP-SAT / optimiser proposals.
3. Say honestly: in current simulation the optimiser can show **higher** harm than simple baselines; a human must confirm every schedule change (hazards H10, H16 remain OPEN).

---

## Journey C — Quality / missed-signal audit (~2 min)

1. Open `http://127.0.0.1:3000/quality`.
2. Run or view the synthetic missed-signal audit path. Label results **synthetic**.
3. Partner hook: a real hospital would get a confidential audit only after ethics + DUA + de-identified extract on **their** premises (`docs/clinical/PARTNERSHIP/PARTNER-PACKET.md`).

---

## Closing lines (honest claims)

**Can claim today:** software exists; safety gates (consent, disclosure lock, claims CI, hazard verifier) are tested; ML studies on synthetic data are reproducible from scripts; partnership packet and ethics drafts are prepared.

**Cannot claim today:** clinical validation on real patients; that the RT optimiser is safe to auto-apply; that OCR or translations are cleared for unsupervised clinical use; any NAFDAC/SaMD clearance; maturity above L0 (overseer-owned).

Leave them with: `docs/clinical/PARTNERSHIP/PARTNER-PACKET.md` and `docs/HANDOVER.md`.
