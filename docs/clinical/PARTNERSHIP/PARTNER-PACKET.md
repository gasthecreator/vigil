# Vigil partner packet (two-page summary)

**Audience:** hospital research / oncology / pathology leadership considering a retrospective partnership.  
**Status:** research prototype materials. Not a sales claim of clinical effectiveness.  
**Version:** aligned with release candidate work on this branch (`v1.0.0-rc.2` when tagged).

---

## Page 1 — What Vigil is, and is not

### What it is
Vigil is an open, evidence-disciplined **decision-support research platform** for breast-cancer follow-up. It turns longitudinal laboratory and clinical follow-up data into alerts, adjudication prompts, plain-language explanations, radiotherapy continuity views, and quality audits — with explicit abstention when data are insufficient.

Verified software artefacts (not clinical outcomes):
| Capability | Artefact |
|---|---|
| Claims / synthetic labelling discipline | `scripts/check_claims.py`, hazard H15 |
| Consent and disclosure gates | `tests/acceptance_p11`, `tests/acceptance_p12`, hazard H17 |
| Missed-signal audit engine (synthetic study) | `reports/ml/STUDY_M10_MISSED_SIGNALS.json`, `scripts/run_study_m10_audit.py` |
| Silent-mode design (shadow store) | `docs/clinical/SILENT-MODE.md`, ADR-0022 |
| Hazard log with OPEN residual risks | `docs/safety/HAZARD_LOG.md` (H10, H16, H25–H27 OPEN) |

### What it is not
- Not a medical device clearance; not NAFDAC/SaMD approved.
- Not a diagnosis or treatment recommendation.
- Not validated on real Nigerian (or any) patient cohorts for clinical performance. Maturity remains **L0** until real-data validation (overseer-owned in `docs/PROGRESS.md`).
- Not permission to auto-apply radiotherapy queue optimisation (badged `unvalidated in simulation`; H10/H16 OPEN).
- Not a claim that local-language UI strings are clinically reviewed (H-118; pcm/yo/ha/ig unreviewed).

### Safety design (short)
No “low risk = safe”; no silent dismissal of surprising results; fact-table narrative verifier; synthetic rows always tagged; partner extracts stay on partner premises for ingest rehearsal.

---

## Page 2 — What a partner provides, what they get, validation plan

### Data a partner would need to provide
See the full dictionary and checklist (do not invent fields here):
- [`DATA-DICTIONARY.md`](DATA-DICTIONARY.md)
- [`DEIDENTIFICATION-CHECKLIST.md`](DEIDENTIFICATION-CHECKLIST.md)
- Ingest rehearsal: `scripts/run_partner_ingest.py` (rejection report only leaves the site)

Minimum idea: de-identified longitudinal labs + recurrence / last follow-up outcomes under an ethics-approved protocol and DUA. No identifiable fields leave the hospital in the standard path.

### What the partner gets back
| Deliverable | Honest scope | Pointer |
|---|---|---|
| Missed-signal audit report | Confidential quality analysis on **their** extract after ethics/DUA; method exercised on synthetic data in M10 | [`VALUE-PROPOSITION.md`](VALUE-PROPOSITION.md), M10 JSON above |
| RCV / lab variation discussion | Analytical support draft; not an EFLM accreditation | VALUE-PROPOSITION §3 |
| Co-authorship on manuscripts | If a study completes and is submitted | STUDY-PROTOCOL |
| Software for silent-mode / pilot | Only after go/no-go and stop-rules sign-off; today go/no-go is **NO-GO** | `docs/clinical/PILOT/` |

### Validation plan (order is binding)
1. Institutional ethics (NHREC / local HREC) — draft: [`ETHICS-APPLICATION.md`](ETHICS-APPLICATION.md)
2. DUA + DPIA — [`DUA-TEMPLATE.md`](DUA-TEMPLATE.md), [`DPIA.md`](DPIA.md)
3. Pre-registration freeze before any real-data analysis — `docs/clinical/PREREGISTRATION.md`, `scripts/check_prereg_freeze.py`
4. On-premises ingest → rejection report → agreed analysis under the frozen plan
5. Prospective silent mode only after separate ops (shadow DB, H-105) and pilot kit sign-off

### Outreach / next step
Use [`VALUE-PROPOSITION.md`](VALUE-PROPOSITION.md) for the briefing deck narrative, then this packet for claim boundaries. Human actions to actually contact a site, submit ethics, and sign DUAs are listed in [`docs/HANDOVER.md`](../../HANDOVER.md) (section D).

### Live demo on synthetic data
`make demo` + [`docs/demo/OWNER-SCRIPT.md`](../../demo/OWNER-SCRIPT.md). Say “synthetic” every time a number appears.
