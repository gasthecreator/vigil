# Vigil — Master Plan

> **Document status:** Canonical. Version 1.0 (2026-10-14). Owner: Gideon Sanni (product owner). Plan author and reviewer: Claude (overseer). Builder: Gemini / Google Antigravity (executor).
> **Formerly named:** Sentinel (renamed to Vigil, 2026-10-14). Any remaining "Sentinel" string in code, docs, config, UI or artifact names is a defect to fix in Phase 0.
> **This file is the single source of truth for what Vigil is, why it exists, what "finished" means, and how it gets built.** If another file, an old prompt, or your own prior output contradicts it, this file wins. If this file is wrong or incomplete, say so in a proposal (Section 17.4); do not silently deviate.

---

## 0. How the executor (Gemini / Antigravity) must use this document

1. **Read order at the start of every session:** `AGENTS.md` → this file (all of it; it is long on purpose) → `docs/PROGRESS.md` (where we are) → `docs/EVIDENCE.md` (what is known and what is only claimed) → the phase brief you were pointed at (Section 14).
2. **Operating skills (mandatory, always on):**
   - `.agent/skills/complete-solution/SKILL.md` — never take the easier route, never defer, never stub, never fake verification.
   - `.agent/skills/repo-standards/SKILL.md` (+ its `references/` and `assets/templates/`) — the repository must meet Google/Microsoft/Amazon/OpenSSF-grade standards at all times.
3. **Authority and precedence:** (1) Safety and honesty rules (Sections 3 and 11) > (2) this document > (3) the phase brief > (4) your own judgment. If you find a conflict, stop at the conflict, record it in `docs/proposals/`, and continue with every part that is not affected.
4. **"Done" is not a feeling.** A task, work package or phase is done only when its **exit gate** (Section 14) is met and the **evidence** it demands is committed (test output, metric files, screenshots, reports). Never write "complete", "done", "production-ready", "enterprise-grade" or "state of the art" in any file, commit message or report unless a committed artifact proves the specific claim. The previous builder session declared the project finished after one pass; that was wrong, and the reasons are itemised in Section 15. Do not repeat it.
5. **You are not the only reader.** A reviewer (Claude) will audit your reports with very little context and no ability to run your machine. Make every report self-contained (Section 16).
6. **No time pressure exists.** This is a multi-month product. Nothing is deferred because it is large, tedious, or complex. The *only* valid reason to drop or shrink something is a **failed feasibility experiment with committed evidence** (Section 13) or a **concrete external blocker** (missing access, data, credentials, legal permission, or a human-only action). Name the blocker, finish everything around it, and list what remains.
7. **Ask for nothing you can derive.** Make reasonable decisions, record them as ADRs (`docs/adr/`), and keep moving. Ask the product owner only for the things in Section 17.3 (human-only actions).

---

## 1. Mission and origin

Vigil exists because of one family's experience. A woman — a high-school teacher, who also lived with hypertension and kidney stones — found lumps. They were removed. Years later, at a routine check-up, cancer was found. Chemotherapy and radiotherapy followed in 2021–2022 at a Nigerian government hospital. Along the way: post-treatment test results were called "not plausible", probably wrong, and she relaxed when she should not have; radiotherapy appointments kept being rescheduled because the machine was scarce or unavailable; her family could not tell what was happening inside her body; the cancer eventually spread (ascites, weakness, inability to eat) and she died. Her son, the product owner, was her caregiver during the early treatment phase.

**Mission:** Make sure that in a resource-constrained cancer pathway, *a weak signal is never dismissed without an explanation, a required follow-up is never silently lost, a delayed treatment is never invisibly harmful, and a family is never left without understanding.*

**What Vigil is in one sentence:** an open, evidence-disciplined clinical-and-family decision-support platform for breast-cancer follow-up that (1) turns serial results into calibrated, explained, uncertainty-aware signals, (2) adjudicates whether a surprising result is real change or measurement noise instead of letting it be waved away, (3) closes the loop on every result and follow-up, (4) tells clinicians and families which affordable, reachable test would answer the question, and (5) protects patients when treatment capacity breaks down.

**What it is not:** it is not a diagnostic device, not a replacement for oncologists, not a consumer "cancer predictor", not a chatbot that gives medical advice. It never states that a person has or does not have cancer or metastasis.

The product honours her by being *right and humble*, not impressive. A tool that frightens a family with an unvalidated number, or reassures them falsely, would repeat the original harm. This is why Section 3 (principles) and Section 11 (safety) outrank every feature.

---

## 2. The problem, in evidence-grounded terms

Each failure the family experienced maps to a documented, general problem. Citations and caveats live in `docs/EVIDENCE.md`; claims in this section marked [E#] refer to entries there.

| # | Lived failure | General problem | Vigil response (module) |
|---|---|---|---|
| F1 | Post-treatment tests "not plausible", dismissed; patient relaxed | Single results are judged against population cut-offs and clinician intuition; individual change and measurement error are not quantified; outliers are dismissed instead of repeated [E1,E2,E9] | **M3 Plausibility Adjudicator** + **M2 Longitudinal Signal Engine** |
| F2 | Lump removal → cancer years later; unclear how serious it was; follow-up relied on one scheduled check-up | Loss to follow-up and un-acknowledged results are a leading patient-safety failure; SMS reminders raise re-attendance substantially in African trials (e.g., 67.1% vs 20.3% in a Kenyan cervical-screening RCT) [E10] | **M6 Closed-Loop Follow-up Guardian** |
| F3 | Radiotherapy machine scarce; appointments rescheduled | Nigeria has on the order of 7 linear accelerators and 3 cobalt units for ~200M people (≈280 LINAC shortfall by an IAEA benchmark) [E6]; each month of post-lumpectomy RT delay raises local recurrence RR ≈1.08 (95% CI 1.02–1.14) [E8]; scheduling is first-come, not harm-aware | **M7 Treatment Continuity & RT Triage** |
| F4 | Family could not understand what was happening | Information asymmetry; jargon; no caregiver-facing, plain-language, multilingual, offline-capable tooling | **M8 Family & Patient Companion** |
| F5 | Late, aggressive spread to abdominal organs; no organ-specific surveillance | Metastatic site follows subtype (bone most common overall; HER2+/TNBC more visceral) [E12]; surveillance is generic, and in low-resource settings the *affordable* test that would answer the question is rarely mapped | **M1 Baseline Organ-Tropism Profiler** + **M4 Resource-Aware Test Ladder** |
| F6 | Presentation at advanced stage, aggressive biology | In Nigerian series, roughly 65–80% present at stage III/IV and a large share (≈35–55% of tested tumours) are triple-negative; small single-centre studies, high uncertainty [E7] | Informs synthetic priors, subgroup evaluation, and the "late-stage-first" design of the whole product |

**An uncomfortable and essential fact the product must respect:** ASCO and ESMO guidance discourages routine serial tumour-marker testing (e.g., CA 15-3) in *asymptomatic* early-stage patients because trials showed no survival benefit from earlier detection [E1]. Serial markers can lead imaging by roughly 2–9 months with sensitivity around 55–70% for recurrence and variable specificity [E1,E2]; ctDNA leads by a median of roughly 6–12 months in published cohorts but is expensive and less sensitive in HR+ and brain-only disease [E3]. Therefore: **Vigil must never be sold as "early-detection AI that saves lives".** Its defensible value is (a) preventing *dismissal and loss* of information that clinicians are already collecting, (b) better use of scarce tests, (c) protecting treatment continuity, (d) family understanding, and (e) generating the evidence base (with consenting partners) to learn *whether* signal-driven follow-up helps in this population. Section 11 turns this into rules.

---

## 3. Non-negotiable principles

These are enforced by tests, linters and review, not just stated.

1. **Truth over impressiveness.** No metric, claim, screenshot or sentence in the product or repo may exceed what has been measured, on what data, with what uncertainty. Synthetic-data results are labelled synthetic everywhere they appear (code, UI, README, API responses).
2. **Safety before features.** A hazard analysis (Section 11.2) exists before any patient-facing output ships. Every output that could change behaviour has a defined failure mode and a mitigation.
3. **Humility is a feature.** The system can say "insufficient data", "I cannot tell", and "this is outside what I was validated for" — and does so by design (abstention, Section 8.7).
4. **Transparency of basis.** Every risk statement shows the inputs, the reasoning and the uncertainty, and is traceable to computed facts (provenance-bound narrative, Section 8.9). No unverifiable free-text claims.
5. **The human decides.** Vigil advises clinicians and informs families; it never auto-orders, never diagnoses, never overrides.
6. **Equity by construction.** Performance is reported per subgroup (age band, subtype, stage, comorbidity, facility tier, data-completeness). A model that works only where data are plentiful is a failed model for the target population.
7. **Privacy by default.** Health data are sensitive personal data under the Nigeria Data Protection Act 2023 [E14]. Minimum collection, encryption, consent, audit, and the ability to run with no raw data leaving a facility.
8. **Works where the users are.** Low bandwidth, intermittent power and connectivity, shared/older Android phones, multiple languages, low health literacy. Offline-first is a requirement, not a nice-to-have.
9. **Open and auditable.** Code, model cards, evaluation harnesses, simulators and datasets-cards are public (data themselves only where licence and consent allow).
10. **Reproducible.** Every number in any report can be regenerated from a tagged commit with a single documented command and fixed seeds. Every model artifact has a lineage record.
11. **Complete, not minimal.** `complete-solution` applies. No stubs, no TODO-as-delivery, no mock verification.
12. **Professional, not "vibe-coded".** `repo-standards` applies. A stranger must be able to tell what it is, why it is built this way, and what stops it breaking.

---

## 4. Users, jobs and journeys

### 4.1 Personas
| ID | Persona | Context | Primary jobs | Failure to avoid |
|---|---|---|---|---|
| U1 | **Oncologist / clinician** (government teaching hospital, 60–120 patients per clinic day) | Time-poor, paper + partial digital records, alarm fatigue | See who needs attention *first*; understand why in 10 seconds; confirm or refute a surprising result; justify a request for imaging | Alert fatigue; opaque scores; extra data-entry burden |
| U2 | **Nurse / records officer / data clerk** | Does the data entry; shared devices | Enter results fast, offline, with minimal typing; never lose a result | Duplicate entry; unit mistakes |
| U3 | **Patient** | May have limited literacy; may be frightened; phone is shared | Know the next step, the date, what a result means in plain words; keep her own record | False reassurance; terror from raw probabilities |
| U4 | **Family caregiver** (the product owner's own role) | Coordinates appointments, medications, symptoms; often far from the hospital | Track symptoms and appointments; get reminders; understand; advocate (“please repeat this test, here is why”) | Being ignored; losing the thread across visits |
| U5 | **Radiotherapy department scheduler / physicist** | Machine downtime, queue of 50–200 patients | Re-sequence patients fairly and defensibly when capacity drops | Ad-hoc, opaque, inequitable rescheduling |
| U6 | **Hospital quality / patient-safety lead** | Wants to know what is falling through cracks | Audit missed signals, lost follow-ups, delays | Anecdote instead of data |
| U7 | **Researcher / ML contributor** | Wants a rigorous, reproducible benchmark | Reuse datasets-cards, simulators, evaluation harness | Irreproducible claims |
| U8 | **Administrator / DPO** | Compliance, access control, audit | Consent, retention, access logs, exports | Un-auditable access |

### 4.2 Core journeys (each must be an automated end-to-end test by Phase 6)
- **J1 Enrolment → baseline → surveillance → signal → escalation → confirmed outcome** (the original product thread).
- **J2 Surprising result → plausibility adjudication → repeat-test recommendation → resolved (real change / lab error) → signal updated.**
- **J3 Missed follow-up → reminder cascade (SMS/WhatsApp/app) → escalation to caregiver → clinic outreach list → closed or documented decline.**
- **J4 Machine down → RT queue re-sequenced with explained harm model → patients notified → delay ledger updated → audit trail.**
- **J5 Family member asks "what does this mean?" → plain-language, language-selectable explanation with uncertainty and "what to ask your doctor" card → printable/QR hand-over to the clinician.**
- **J6 Facility with no MRI → Test Ladder recommends the best locally available test for the suspected organ → records availability/cost feedback.**
- **J7 Quality lead runs Missed-Signal Audit over a facility's historical results → report.**
- **J8 Model governance: drift alarm → shadow model → evaluation → controlled promotion (or rollback) with a signed change record.**

---

## 5. Product scope: the module map

Vigil is a platform of cooperating modules with strict contracts. Each module has a purpose, inputs/outputs, algorithms, UX surface, acceptance criteria and a kill/pivot criterion where it is research-grade. IDs are stable; tests, ADRs and reports reference them.

| ID | Module | Class | Status at v1.0 of this plan |
|---|---|---|---|
| M0 | Platform core (identity, consent, audit, data model, interoperability, sync) | Engineering | Partially exists (prototype); rebuild properly |
| M1 | Baseline Organ-Tropism Profiler | ML | Prototype exists; **scientifically invalid as built** (Section 15) |
| M2 | Longitudinal Signal Engine | ML | Prototype exists; **circular labels** (Section 15) |
| M3 | Plausibility Adjudicator (real change vs measurement noise) | Statistics/ML | New (frontier) |
| M4 | Resource-Aware Test Ladder | Decision support | New (frontier) |
| M5 | Provenance-Bound Explanation & Narrative Engine | ML/NLG | New (replaces template text) |
| M6 | Closed-Loop Follow-up Guardian | Workflow | New |
| M7 | Treatment Continuity & Radiotherapy Triage | Optimisation/simulation | New (original “Option 2”) |
| M8 | Family & Patient Companion (offline-first PWA, multilingual) | Product/UX | New |
| M9 | Clinician Workstation (triage queue, patient view, dossiers) | Product/UX | Prototype exists; rebuild |
| M10 | Quality & Missed-Signal Audit | Analytics | New |
| M11 | Evaluation, Benchmark & Governance (harness, model cards, drift, change control) | MLOps/Science | New (backbone for credibility) |
| M12 | Federated & Privacy-Preserving Learning | Research | New (frontier; feasibility-gated) |
| M13 | Simulation Laboratory (mechanistic cohort simulator, department digital twin) | Science | Prototype generator exists; rebuild |

Sections 6–10 specify them. Sections 11–13 govern safety, standards and feasibility. Section 14 is the phased build; Section 15 is the audit of what exists.

---

## 6. Module specifications

> Notation: **AC** = acceptance criteria (all must pass, each backed by an automated test or a committed evidence file). **Kill** = the condition under which a research-grade element is dropped or replaced (Section 13). **Frontier** marks things not known to be implemented elsewhere in this combination; they are hypotheses to be tested, never claims.

### 6.0 M0 — Platform core
**Purpose:** a trustworthy substrate: identity, consent, audit, data model, interoperability, offline sync.
- **Identity & access:** OIDC-based auth (self-hostable provider, e.g. Keycloak/Authentik, or a library-level implementation behind an interface), RBAC with roles `clinician`, `nurse_clerk`, `scheduler`, `quality_lead`, `admin`, `patient`, `caregiver`, `researcher_readonly`; attribute checks per facility; patient/caregiver access via consented, revocable links with short-lived tokens. Secrets only from environment/secret manager.
- **Consent & purpose limitation:** consent records (scope, purpose, granted-by, timestamp, expiry, revocation) are first-class; every read of patient data is checked against role *and* consent; research export requires explicit research consent.
- **Audit:** append-only, tamper-evident audit log (hash-chained) of every read/write/export/alert acknowledgement; queryable by the DPO role.
- **Data model v2** (supersedes the 4-table prototype): `Patient`, `Facility`, `Encounter`, `Diagnosis/Baseline` (versioned, with provenance), `Observation` (generic: analyte, value, unit, LOINC code, specimen date, lab/instrument id, method, reference range at source), `ObservationQuality` (QC flags, suspected error), `Symptom`/`PatientReportedOutcome`, `Medication/Treatment` episodes, `ImagingOrder/Result`, `Appointment`, `FollowUpTask`, `RiskAssessment` (with model version, input snapshot hash, uncertainty, abstention state), `Alert`, `AlertAcknowledgement` (who/when/disposition), `ConsentRecord`, `AuditEvent`, `Facility​Capability`, `RTMachineStatus`, `RTSlot`. Every clinical row has `created_at`, `source`, `entered_by`, `version`, and soft-delete only.
- **Interoperability:** HL7 FHIR R4 resources for Patient, Observation, Condition, Appointment, CarePlan, DiagnosticReport import/export; **LOINC** codes for analytes; **UCUM** units with a conversion library and explicit unit-mismatch errors (never silent coercion). SNOMED CT/ICD-10 coding where licences allow; otherwise ICD-10 only.
- **Offline sync:** local-first storage on clients (IndexedDB), conflict-free replication strategy documented in an ADR (CRDT or operation-log with deterministic merge), resumable uploads, end-to-end encrypted sync for patient-held records.
- **Persistence:** PostgreSQL 16+ in production, SQLite for local dev only; Alembic migrations with up/down tests; no schema change without a migration and a data-fixture test.
- **AC:** auth/RBAC/consent matrix test (every role × every endpoint × consent state) passes; audit chain verification command detects a tampered row in a test; FHIR round-trip tests for each supported resource; unit-conversion property tests (Hypothesis) show no silent coercion; migration up/down tested on a populated database.

### 6.1 M1 — Baseline Organ-Tropism Profiler
**Purpose:** estimate, with uncertainty, the *relative* propensity of distant spread to bone, liver, lung and brain (and "other/locoregional" where defined) given baseline pathology and context. Used to (a) weight which analytes/tests matter for this patient, (b) populate the Test Ladder, (c) inform families in plain language. **Not** a probability that metastasis will occur.
- **Inputs:** age, stage (with T/N/M if available), grade, ER/PR/HER2 (and Ki-67 if available), histology, laterality, treatments received, comorbidities (hypertension, renal history, hepatic disease, diabetes, HIV status where recorded), menopausal status.
- **Ground truth for training is the hard part.** The prototype trained on a vector the generator itself invented. That is circular (Section 15). Required replacement strategy, in order:
  1. **Literature/registry-calibrated priors:** SEER-derived site-of-metastasis proportions by subtype and stage (e.g., among patients with distant metastasis: bone 21.3%, lung 16.1%, liver 9.2%, brain 2.9% in a 2014–2023 SEER analysis of 200,558 patients [E12]; subtype-specific patterns such as HR+/HER2− bone-only predominance), used as an explicit Bayesian prior with documented sources and per-cell sample sizes.
  2. **Real-data model where data exist:** fit multinomial/multilabel site models on SEER (via SEER*Stat access — human action, Section 17.3) with proper cross-validation, calibration and subgroup reporting. SEER lacks serial labs and recurrence timing; it is valid for *site given metastasis*, not for timing.
  3. **Uncertainty:** report posterior intervals; when the cell sample size is small (e.g., rare combinations), widen and flag "low-evidence".
  4. **Ablate** XGBoost vs. regularised multinomial logistic regression vs. hierarchical Bayesian model vs. TabPFN-style prior-fitted nets; choose by calibrated log-loss, not by R².
- **Outputs:** `{organ: {p, ci_low, ci_high, evidence_level}}`, normalised over sites *conditional on metastasis*, plus a `provenance` block (which prior cells and model version).
- **AC:** held-out calibration (reliability diagram, ECE ≤ 0.05 on real/registry data; synthetic reported separately and labelled); ≥3 baselines compared; per-subtype/per-stage tables; leakage test (no feature derived from outcome); model card; the UI shows intervals and an evidence badge, never a bare percentage.
- **Kill:** if no model beats the literature-prior baseline on held-out registry log-loss by a statistically meaningful margin, ship the prior (it is still the correct, honest answer) and record an ADR.

### 6.2 M2 — Longitudinal Signal Engine
**Purpose:** convert a patient's irregular, multi-analyte history into a *calibrated, uncertainty-aware, time-aware* signal that recurrence-related change is under way, and (equally important) a calibrated statement of *how much we do not know*.
- **Reality check on analytes:** the prototype used five (ALT, AST, creatinine, CA 15-3, WBC). That is thin. The **analyte registry** (LOINC-keyed, extensible via config, not code) must cover at minimum: CA 15-3, CA 27-29, CEA, ALT, AST, ALP, GGT, total/direct bilirubin, albumin, total protein, LDH, calcium (corrected), phosphate, creatinine/eGFR, urea, haemoglobin, platelets, WBC with differential (neutrophil/lymphocyte ratio), ESR/CRP, INR; each with units, plausible physiological bounds, biological variation (CVi, CVg), analytical CV by method class, and organ associations (bone: ALP, Ca; liver: ALT/AST/GGT/bili/albumin/INR; kidney: creatinine/urea; marrow: Hb/plt/WBC; systemic: LDH/CRP). Missingness is *informative* in this population (tests are paid for out of pocket) and is modelled, not imputed away.
- **Symptoms/PROs as inputs:** abdominal swelling/ascites, early satiety, weight loss, bone pain (new/escalating), cough/dyspnoea, headache/neurological change, jaundice, fatigue/performance status (ECOG), appetite — structured, graded, time-stamped.
- **Label definition (critical, do not repeat the prototype's mistake):** a prediction target must be defined in terms of a *clinical event* with a *time horizon and a blinding window*, e.g., "distant recurrence documented within *H* months of the prediction time, using only data available at the prediction time". Horizon set `H ∈ {3, 6, 12}` months. Time-to-event formulation preferred (discrete-time hazard or neural survival) so censoring is handled correctly. The generator may define its latent event; the *features* may never include a variable derived from the latent event or an anomaly flag.
- **Model families to benchmark head-to-head (M11 harness), all with the same splits:**
  1. Clinical-rule baselines: single-threshold CA 15-3 > 30 U/mL; biomarker-velocity rules (the published velocity-threshold approach reported high apparent sensitivity in a matched case-control design — treat as optimistic [E2]); doubling-time rules.
  2. Classical: regularised Cox, discrete-time logistic hazard with engineered velocity/acceleration/variability features, gradient boosting on windowed features, **joint longitudinal–survival models** (the statistically principled gold-standard comparator).
  3. Deep irregular-time models: GRU-D (decay + masks), GRU-ODE-Bayes, Neural CDE, a continuous-time transformer, and the recent GRU-with-exponential-basis (GRUwE) which reports being competitive with far more complex architectures [E11]. **Do not assume depth wins.** The prior prototype's BiLSTM is a *comparator only*, and a bidirectional model is inappropriate for forecasting (it sees the future of the window); if a bidirectional encoder is used it may only run over past data.
  4. Self-supervised pre-training on public lab time series (e.g., MIMIC-IV lab trajectories restricted to cancer-coded stays, with the ICU caveat documented [E13]) followed by fine-tuning; keep only if it beats from-scratch on held-out data.
- **Calibration & uncertainty:** temperature/Platt/isotonic as appropriate; deep ensembles or MC-dropout for epistemic uncertainty; **conformal risk control** for alert thresholds (Section 8.6).
- **Output:** per-horizon risk with interval; "drivers" (Section 8.9); abstention state (`insufficient_data | out_of_distribution | low_confidence`); lead-time estimate relative to a rule-based baseline.
- **AC:** all families evaluated on identical leakage-free splits (patient-level, plus temporal and cross-generator splits for synthetic data); time-dependent AUROC/AUPRC, Brier, calibration slope/intercept, ECE, decision-curve net benefit, lead-time gained at a fixed false-alarm rate, alert burden per 100 patient-months, subgroup tables; ≥ 5 seeds with confidence intervals; ablations (remove velocity features, remove missingness mask, remove organ prior, remove symptoms); everything regenerates from one command.
- **Kill:** any deep model that does not beat the best classical model on calibrated net benefit with non-overlapping bootstrap CIs is **not** shipped as default; it may remain as an optional research model.

### 6.3 M3 — Plausibility Adjudicator *(Frontier; direct answer to F1)*
**Purpose:** when a result is surprising ("implausible"), compute whether it is more likely **real physiological change**, **analytical/pre-analytical error**, or **inconclusive**, and recommend the cheapest decisive next step *instead of dismissal*.
- **Method:** (i) *Reference Change Value* (RCV) from clinical chemistry: `RCV = √2 · Z · √(CVa² + CVi²)` (with log-normal variant for skewed analytes) to decide whether a change between consecutive results exceeds combined analytical and within-subject biological variation; (ii) *individual (personalised) reference intervals* built from the patient's own history (index of individuality; Bayesian updating), (iii) *delta-check* rules and multivariate coherence (e.g., ALT↑ with AST↑ and bilirubin↑ is coherent; an isolated implausible CA 15-3 with normal everything else is less so, but not dismissible), (iv) *inter-laboratory offset model* when the facility or method changed between draws, (v) *pre-analytical error priors* (haemolysis, mislabelled sample, wrong-patient) as explicit hypotheses with prior probabilities set in config and calibrated when audit data exist, (vi) Bayesian model comparison giving `P(real change)`, `P(error)`, `P(inconclusive)`.
- **Output:** a verdict with probabilities and a **single recommended action** (e.g., "repeat within 7–14 days at a different laboratory; if confirmed, escalate to imaging X"), plus a clinician-readable rationale and an optional patient-facing "second-look request" card (Section 6.8).
- **The rule that matters:** a result is **never** rendered "dismissed". It is `explained`, `needs_repeat`, or `escalate`. A dismissed-result pathway does not exist in the data model.
- **AC:** analytic validation against simulated ground-truth error injection (sensitivity/specificity for error vs real-change at specified RCV settings); property tests for RCV maths against published tables; calibration of the three-way posterior; documented prior sources for CVi/CVa (EFLM biological-variation database values, cited per analyte); clinician-readable output reviewed in a usability session script (Phase 7).
- **Kill:** if posterior calibration fails (ECE > 0.1 on simulated truth *and* on any real audit data obtained), fall back to RCV + delta-check rules alone and record an ADR.

### 6.4 M4 — Resource-Aware Test Ladder *(Frontier in LMIC context; answers F5)*
**Purpose:** given a suspected organ and a facility's *actual* capabilities and prices, recommend the most informative affordable test and the next rung if it is inconclusive. Example: suspected hepatic → abdominal ultrasound (cheap, available) → contrast CT/MRI (scarce); bone → plain film/ALP/Ca trend → bone scan/MRI; lung → chest X-ray → CT.
- **Inputs:** M1 organ posterior, M2/M3 outputs, symptoms, `FacilityCapability` (available modalities, typical turnaround, price band, distance/transport band, last verified date), patient affordability band (optional, consented).
- **Method:** expected-value-of-information ranking with published sensitivities/specificities per modality-organ pair (each cited in `docs/EVIDENCE.md`, with ranges, not point values), cost and delay penalties, and an explicit "no good option here: refer" outcome with referral candidates from the capability registry. No fabricated sensitivities: any pair without a source is marked `unsourced` and excluded from automatic ranking.
- **Capability registry:** curated and versioned; every row has a `source` and `verified_on` date; stale rows (> 12 months) are down-weighted and flagged; community/clinic updates go through moderation.
- **AC:** every recommendation links to its evidence rows; stale/unsourced handling tested; recommendations are stable under small input perturbations (metamorphic tests); a worked example for each organ at each facility tier is in the docs.

### 6.5 M5 — Provenance-Bound Explanation & Narrative Engine
**Purpose:** produce clinician- and family-readable explanations whose every factual statement is *traceable to a computed fact*.
- **Mechanism:** the engine first emits a **fact table** (`fact_id`, type, value, unit, window, source observation ids, model/version). Narrative text is generated from templates and, optionally, an LLM constrained to **only** reference `fact_id`s; a **verifier** rejects any sentence containing a number, organ, date or claim not present in the fact table, and any forbidden claim class (diagnosis, prognosis, treatment instruction, “you have/do not have cancer”). Rejected generations fall back to the template text. This verifier is a hard unit-tested component.
- **Attribution methods** (compare, validate with deletion/insertion faithfulness tests): integrated gradients, SHAP on the classical model, attention only as a *hint* (attention is not explanation), and **counterfactual statements** ("risk would fall below the alert level if ALP were 38% lower") checked by re-running the model.
- **Languages & registers:** clinician register (concise, quantitative), family register (plain language, reading grade ≤ 8, no unqualified percentages; uses frequency framing and verbal uncertainty tied to numeric bands), and translations (Section 10.4).
- **AC:** 100% of generated sentences pass the verifier on an adversarial test-suite (hallucination bait, number swaps, forbidden-claim prompts); faithfulness scores reported; readability scores asserted in tests; no LLM call is ever on the critical path of an alert (the alert must work with templates only).

### 6.6 M6 — Closed-Loop Follow-up Guardian *(answers F2)*
**Purpose:** no result, referral, repeat-test request or scheduled check-up is ever left without an acknowledged *disposition*.
- **Objects:** `FollowUpTask` with owner, due date, escalation ladder, and terminal states (`completed`, `declined_with_reason`, `transferred`, `cancelled_by_clinician`, `lost_to_follow_up_after_N_attempts`). Result acknowledgement is required for abnormal and “surprising” results; unacknowledged results escalate by time-boxed rules.
- **Channels:** in-app, SMS, WhatsApp Business API (where permitted), voice-call task list for clinic staff; patient-chosen language/time; delivery receipts recorded; opt-out honoured. All outbound messages are template-approved, contain no clinical detail in transit beyond a minimal “please contact your clinic”, and respect privacy on shared phones (generic sender text, optional PIN-gated detail).
- **Evidence basis:** text-message reminders raised re-attendance dramatically in a Kenyan RCT (67.1% vs 20.3%, OR ≈ 8) and are widely acceptable in African cohorts; WhatsApp-specific trial evidence for cancer follow-up was not found [E10] — so Vigil must **measure** its own effect (built-in A/B-capable reminder experiments with ethics approval).
- **AC:** state-machine tests for all transitions; simulated-clock tests for every escalation path; no task can disappear (database constraint + property test); outreach list export for clinics; delivery-failure fallbacks tested; load test for 10⁵ tasks.

### 6.7 M7 — Treatment Continuity & Radiotherapy Triage *(original "Option 2"; answers F3)*
**Purpose:** when capacity breaks (machine down, backlog), re-sequence patients to minimise expected harm *transparently and fairly*, and quantify the harm of delay so it is visible.
- **Harm model:** per-patient harm of delay as a function of delay length, subtype, stage, indication (adjuvant post-lumpectomy, post-mastectomy, palliative bone/brain, curative TNBC), prior treatment sequence (time since surgery/chemo), and fractionation options. Priors from the pooled evidence: post-lumpectomy local recurrence RR ≈ 1.08 per month of delay (95% CI 1.02–1.14), no demonstrated survival effect in that meta-analysis, and conflicting data about thresholds (no difference up to 8–12 weeks in some series; worse beyond ~3 months in a large registry analysis) [E8]. The model is **piecewise/threshold-capable with uncertainty**, indication-specific, and clearly labelled as evidence-limited; palliative indications (pain, cord compression, brain metastases) follow urgency rules from guidelines, not the adjuvant harm curve.
- **Optimiser:** mixed-integer / constraint programming (OR-Tools CP-SAT or MILP) over a rolling horizon: minimise total expected harm subject to machine-day capacity, fractionation constraints (contiguity, weekend rules, maximum interruption), physician-set hard priorities, **fairness constraints** (bounded waiting-time disparity across subgroups, no systematic disadvantage by facility referral source, insurance/payment status, sex, age band — payment status is never a model input for prioritisation), and stability (minimise reshuffling). Output includes *why* each patient moved (marginal harm contributions), and a "what if the machine stays down N more days" projection.
- **Hypofractionation awareness:** options such as shorter regimens are surfaced as *clinician-selectable levers* with their evidence level, never auto-applied.
- **Digital twin / department simulator (M13):** discrete-event simulation with machine failure processes (MTBF/MTTR configured from facility data), arrival processes, no-shows, and policy comparison (FCFS vs. harm-aware vs. clinician-heuristic) over many Monte-Carlo replications; outputs distribution of cumulative harm, wait-time disparities and re-shuffle counts. This is the evidence that the optimiser helps *before* anyone is affected.
- **Patient side:** rescheduling notices through M6 with reason and expected new date; a *delay ledger* per patient visible to the patient/caregiver ("your treatment has been delayed 18 days in total").
- **AC:** optimiser correctness tests against brute-force on small instances; fairness-constraint tests; property tests (capacity never exceeded, contiguity preserved); simulation study report (≥ 1,000 replications per policy) with CIs committed; explanation for every move; clinician override recorded and respected.
- **Kill:** if the harm-aware policy does not outperform FCFS in simulated expected harm *with clinically plausible parameter ranges* across a sensitivity analysis, retain it only as a decision aid that visualises the queue and delay ledger.

### 6.8 M8 — Family & Patient Companion (offline-first PWA)
**Purpose:** the caregiver-and-patient surface for understanding, tracking and advocating.
- **Features:** symptom diary with body-map and structured grades (voice input), appointment and medication calendar (reminders), plain-language “what this result means” with uncertainty and **“questions to ask your doctor”** cards, **Second-Look Request**: a one-page, clinician-readable summary (QR/print/share link) stating *the observed change, its size relative to the patient's own baseline, the Plausibility verdict, and the specific test being requested*, in the clinician register — the product-owner's original “help the family advocate” idea, made safe by M3/M5; document vault (photographs of lab reports with on-device OCR → structured observation drafts that a human confirms); export/import of the patient's own record (FHIR bundle, PDF); caregiver sharing with granular, revocable consent; “bad news mode” (patient chooses what they see and when, because terrifying probabilities can harm).
- **No raw risk percentages to families by default.** Families see calibrated *bands* with verbal descriptors and actions; clinicians can see numbers. Policy configurable per facility and per patient preference, with the default defined by the human-factors study (Phase 7).
- **AC:** works fully offline for core flows (airplane-mode e2e tests); installable PWA; Lighthouse PWA/accessibility/performance budgets (Section 9.7); WCAG 2.2 AA audit evidence; OCR draft accuracy reported on a synthetic/consented report set with human-confirm gate enforced in code; reading-grade tests.

### 6.9 M9 — Clinician Workstation
**Purpose:** triage-first interface: who needs attention now and why.
- **Views:** Triage Queue (sorted by *action urgency*, which combines risk, uncertainty, overdue loops and treatment delay — not risk alone); Patient Timeline (labs, symptoms, imaging, treatments, appointments, alerts on one time axis with analyte overlays and personal reference bands); Signal Panel (risk with interval, drivers, counterfactuals, abstention reasons); Adjudication Panel (M3); Test Ladder Panel (M4); Intake Drawers (keyboard-first, unit-safe, offline-capable); Alert Inbox with mandatory acknowledgement dispositions; Dossier Export (PDF/FHIR) with provenance; Admin/Audit views.
- **Alert design rules:** tiers defined by *conformal* guarantees (Section 8.6), alert burden budget per clinic session, snooze-with-reason, auto-merge of duplicate alerts, no red-banner unless the false-alarm budget is respected; every alert states what to do next.
- **Chart rules:** the **y = 0.75 line from the original PRD becomes configuration, not dogma**: thresholds come from the calibrated operating point chosen on validation data (Section 8.6) and are displayed with their meaning (“expected ≤ X false alerts per 100 patient-months at ≥ Y% sensitivity on validation data”). Synthetic-data provenance is always visible when applicable.
- **AC:** triage ordering property tests; Playwright e2e for J1–J7 (clinician side); axe-core zero serious violations; keyboard-only completion tests; performance budgets; visual regression snapshots.

### 6.10 M10 — Quality & Missed-Signal Audit *(Frontier utility for hospitals)*
**Purpose:** retrospective audit that answers “how many sustained drifts, surprising results and follow-ups fell through here?”
- Runs the M2/M3/M6 logic *retrospectively* over a facility's de-identified historical results; reports counts, time-to-action distributions, loss-to-follow-up rates, radiotherapy delay distributions, with confidence intervals and clear caveats (no individual accusations; aggregate, de-identified, role-restricted).
- **Value:** gives hospitals an evidence-based reason to adopt the rest, and gives us the first real-world data on dismissal frequency (a gap in the literature).
- **AC:** audit report generator tested on synthetic facilities with injected ground-truth missed signals (recall of injected signals reported); privacy tests (k-anonymity floor on any small cell); reproducible report command.

### 6.11 M11 — Evaluation, Benchmark & Governance backbone
**Purpose:** the machinery that makes every other claim believable.
- **Evaluation harness (`vigil-eval`):** versioned dataset cards, split definitions (patient-level, temporal, site-level, cross-generator), metric implementations with unit tests against known values, bootstrapped CIs, subgroup tables, decision-curve analysis, calibration plots, lead-time analysis, alert-burden analysis, ablation runner, seeds fixed, results written to `reports/` as JSON + rendered Markdown, and a CI job that fails if headline metrics regress beyond tolerance.
- **Experiment tracking & lineage:** MLflow (or DVC + git) with model registry; every artifact records dataset hash, code commit, config, seed, environment lock; **no pickle for model exchange** — use safetensors / ONNX / skops-secure formats and verified hashes (pickle deserialisation is an arbitrary-code-execution risk; the prototype committed `.pkl` files).
- **Model cards & dataset cards** (Mitchell et al. format, extended with intended use, out-of-scope use, subgroup performance, known failure modes, ethical considerations) per model/dataset.
- **Reporting standards:** TRIPOD+AI-conformant reports for development/validation, PROBAST+AI self-assessment, DECIDE-AI for early live evaluation, CONSORT-AI/SPIRIT-AI if a trial is ever run [E15].
- **Monitoring:** data-drift (PSI/KS), calibration drift, alert-rate drift, subgroup drift, label-delay-aware performance monitoring; **adaptive conformal inference** for coverage maintenance under shift with the explicit caveat that it does not rescue severe shift and retraining is then required [E16].
- **Change control:** predetermined change control plan (PCCP-style): what may change (retrain on new data within bounds), how it is validated, acceptance thresholds, rollback; shadow-mode deployment before promotion; signed change records.
- **AC:** one-command reproduction of the full benchmark; CI regression gate; model/dataset cards present for every shipped artifact; a pickle-scanning CI check.

### 6.12 M12 — Federated & Privacy-Preserving Learning *(Frontier; feasibility-gated)*
**Purpose:** let several hospitals improve models without exporting raw patient data.
- **Phase-gated approach:** (1) simulate federated training over synthetic multi-site partitions with realistic heterogeneity (site-specific analyser offsets, case-mix, missingness); (2) implement with **Flower** (or equivalent) + secure aggregation + DP-SGD (Opacus) with privacy accounting; (3) evaluate utility loss vs. centralised and vs. local-only training; (4) pilot with real partners only after governance approval.
- **Kill:** if federated + DP cannot reach within a pre-registered tolerance (e.g., ≤ 3 percentage points of calibrated net benefit) of centralised training on the multi-site simulation, retain federated *evaluation* only (sites evaluate shipped models locally and share aggregate metrics).
- **AC:** reproducible simulation report; privacy-budget ledger; no raw-data egress test (network-policy test in the pilot environment).

### 6.13 M13 — Simulation Laboratory
**Purpose:** scientifically honest synthetic data, since real longitudinal oncology labs are scarce and restricted [E13].
- **Mechanistic cohort simulator (`vigil-sim`):** generates patients from *latent disease processes* (subtype-specific recurrence hazard, site-specific seeding, tumour-marker secretion kinetics with realistic shedding and clearance, organ-damage effects on enzymes, therapy effects, comorbidity effects, inter-individual and inter-lab variability, analytic noise, outliers, sample mix-ups, missingness driven by cost and access, irregular visit patterns, loss to follow-up, treatment gaps). Parameters are **calibrated to published targets** (documented in `docs/EVIDENCE.md`): e.g., CA 15-3 elevated before diagnosis in ~41% of recurrences with lead ≈ 4.2 ± 2.3 months in one 1,023-patient cohort; ~54–64% sensitivity with 99% specificity once locoregional relapses are excluded; sensitivity highest in liver metastases and lowest in locoregional relapse [E1]; ctDNA lead-time distributions [E3]; stage mix and subtype mix from Nigerian series [E7]. Calibration targets are *tests*: the generator must reproduce them within tolerance.
- **Multiple generators with different assumptions** (G1 smooth-kinetics, G2 step-change/shedding, G3 heavy-tailed noise with inter-lab shifts) to enable **cross-generator validation** — a model that scores well only on the generator that made its training data has learned the generator, not biology.
- **Sim-to-real discipline:** every synthetic result is labelled; a “sim-to-real gap” section is mandatory in every report; no performance claim for clinical use is ever drawn from synthetic data.
- **AC:** calibration-target tests pass; distributional checks versus published summaries; deterministic given a seed; documented in a dataset card; ≥ 3 generators; the old `is_anomaly` flag never appears in feature construction (static analysis test).

---

## 7. Data strategy

### 7.1 The honest data situation
- Real longitudinal oncology laboratory data with recurrence labels are scarce, mostly restricted, and almost absent for sub-Saharan Africa [E13]. Public registries (SEER) carry stage, subtype, site of metastasis and survival but **not** serial labs or recurrence dates. METABRIC and TCGA-BRCA carry genomics and survival/recurrence-type events with relative dates but not serial routine labs; TCGA event dates are expressed as days from diagnosis [E13]. Project Data Sphere offers free, application-based access to de-identified comparator-arm trial data (breast trials included; **lab content varies by study and must be verified in each data dictionary**) [E13]. I-SPY2 imaging/outcomes are on TCIA, with clinical/lab tables behind a data-security application [E13]. MIMIC-IV offers dense lab series but for ICU stays; a cancer cohort must be built from diagnosis codes and the ICU bias documented [E13].
- Therefore the data plan is **tiered** and each tier is labelled in every report:

| Tier | Source | Used for | Claim it can support |
|---|---|---|---|
| T-S | Mechanistic synthetic (M13) | Software correctness, plumbing, stress tests, method comparison under *known* truth, sensitivity analyses | "The method recovers a known signal under stated assumptions". **Never** clinical performance |
| T-P | Public registries/trials: SEER, METABRIC, TCGA-BRCA, Project Data Sphere breast studies, MIMIC-IV (cancer-coded) | M1 priors/models; method pre-training; cross-checks of kinetics; plausibility priors | Calibrated site priors; generic method validity on real (non-target) populations |
| T-R | Retrospective de-identified cohort from a partner hospital (e.g., a Nigerian teaching hospital) | Real validation of M2/M3/M6/M10; recalibration | Retrospective performance in the target setting, with CIs |
| T-Q | Prospective **silent-mode** (alerts not shown to clinicians) | Prospective validation, alert-burden measurement | Prospective calibration/lead time |
| T-L | Live pilot with clinician use (DECIDE-AI style) | Safety, usability, clinical utility signals | Early-stage clinical evaluation |

### 7.2 Acquisition tasks (executor prepares everything; human-only steps in 17.3)
1. **Data-access dossier** (`docs/data/ACCESS.md`): for each public source, the exact steps, forms, licence/terms, expected turnaround, and what was verified. The executor drafts applications and agreements; the product owner submits/signs them.
2. **Partner-hospital package** (`docs/clinical/PARTNERSHIP/`): protocol for a retrospective chart-review study, data dictionary and minimal dataset, de-identification specification, data-use agreement template, ethics application draft aligned with Nigerian health-research ethics requirements (NHREC/institutional IRB; verify current requirements), NDPA DPIA draft [E14], and a one-page “what we offer the hospital” (Missed-Signal Audit, M10).
3. **Ingestion framework:** every source gets a loader with schema validation (pandera/Pydantic), unit/LOINC mapping, provenance hash, and a **dataset card**; loaders never mutate raw data; raw data live outside git (DVC/object storage) with checksums in git.

### 7.3 Data quality and validation
- Great Expectations / pandera suites per dataset; physiological bounds from the analyte registry; duplicate/time-order checks; unit consistency; explicit missingness reports; label audit (who defined the event, how, when).
- **Leakage controls (mandatory tests):** patient-level splitting; temporal splitting; no feature computed with future information; no outcome-derived features; scaler/encoder fit only on training folds; a *shuffled-label canary* (performance must collapse to chance); a *feature-importance sanity check* (no single suspicious feature explaining > 90% of performance without justification).
- **De-identification:** Safe-Harbor-style removal of direct identifiers, date-shifting per patient (preserving intervals), small-cell suppression, and a re-identification risk assessment before any dataset leaves a facility.

### 7.4 Synthetic data governance
Every synthetic row carries `synthetic=true` and `generator_id`; APIs and UI show a persistent badge when a patient or cohort is synthetic; demo seeding endpoints exist only in non-production profiles and are unreachable in production by configuration tests.

---

## 8. Machine-learning & statistical specification

### 8.1 Problem formulations
- **P-A (site propensity | metastasis):** multi-class/probabilistic over {bone, liver, lung, brain, other}, from baseline features. Evaluated by log-loss, calibration, and subgroup performance.
- **P-B (event-risk over horizons):** time-to-event (discrete-time hazard) with horizons H ∈ {3,6,12} months; landmark prediction at each new observation; right-censoring handled; competing risk (death without recurrence) handled by cause-specific or Fine–Gray style formulation.
- **P-C (change adjudication):** three-way posterior {real change, error, inconclusive} per surprising observation (M3).
- **P-D (harm of delay):** per-patient expected harm function (M7).
- **P-E (test recommendation):** ranking by expected value of information under cost and delay (M4).

### 8.2 Splits (all reported)
Patient-level k-fold (k≥5) with repeated seeds; temporal hold-out (train earlier cohorts, test later); **site hold-out** (train on facilities A, test on B, with a synthetic site-shift simulator until real sites exist); **cross-generator hold-out** for synthetic data; subgroup-stratified reporting.

### 8.3 Metrics (primary → secondary)
- **Primary (decision-relevant):** net benefit by decision-curve analysis across a clinically sensible threshold range; **lead time gained** versus the best rule-based baseline at a fixed false-alarm rate; **alert burden** per 100 patient-months at the chosen operating point.
- **Discrimination:** time-dependent AUROC/AUPRC at each horizon (AUPRC essential because recurrence is the minority event).
- **Calibration:** calibration slope/intercept, ECE (adaptive bins), Brier/IPCW-Brier, reliability diagrams with CIs. Discrimination without calibration is not acceptable for risk communication.
- **Uncertainty quality:** coverage of intervals, selective-prediction curves (performance vs. abstention rate), conformal coverage.
- **Equity:** all of the above per subgroup (age band, subtype, stage, comorbidity, facility tier, data-completeness quartile); report the worst-group result next to the mean; a **max-gap rule**: a release is blocked if any pre-specified subgroup has calibration slope outside [0.7,1.3] or AUPRC below 70% of the overall AUPRC without a documented, reviewed justification.
- **Never report accuracy as a headline**; never report “ROC-AUC = 1.000” as a success (it signals a degenerate task or leakage: treat as a defect that triggers a leakage investigation).

### 8.4 Baselines (always present in every comparison)
(1) no-skill/prevalence; (2) single-threshold marker rule; (3) velocity/doubling-time rule; (4) regularised Cox/discrete-time logistic on engineered features; (5) gradient-boosted trees on windowed features; (6) joint model. A deep model is shown only next to these.

### 8.5 Training hygiene
Fixed seeds; deterministic algorithms where possible; hyper-parameter search with nested CV or a held-out tuning split (never on the test split); early stopping on a validation split distinct from test; class-imbalance handled by loss weighting/focal loss *and* verified not to damage calibration (recalibrate after); mixed precision off for reproducibility unless justified; all runs logged; **no manual cherry-picking of seeds**.

### 8.6 Alerting as controlled risk (not a magic 0.75)
- Define an **alert policy** as a function of (risk, uncertainty, data sufficiency). Choose thresholds by **conformal risk control / learn-then-test**: guarantee, under exchangeability on a calibration set, that the expected false-alarm rate (or false-discovery proportion) stays below a stated budget `α`, and report empirical sensitivity at that operating point with CIs.
- Provide **tiers**: `watch` (information only), `review` (clinician review within a stated window), `urgent` (same-day review). Each tier has a documented α and expected burden. Thresholds are *configuration versioned with the model*, not constants in code.
- **Adaptive conformal inference** to track coverage under drift (with an automatic “re-validate/retrain” trigger when coverage deviates beyond tolerance for a sustained window) [E16].
- The PRD's original **0.75 line** is retained only as a *default for the synthetic demo profile* and is replaced by the calibrated operating point in any real-data profile. A unit test fails if `0.75` appears as a literal outside configuration/test fixtures.

### 8.7 Abstention
Return `insufficient_data` when fewer than the minimum validated observations/analytes exist in the lookback window; `out_of_distribution` when input is far from training support (density/Mahalanobis/ensemble disagreement, calibrated on held-out data); `low_confidence` when the conformal set is not decisive. Abstention is surfaced as a first-class state in API and UI and counted in monitoring (an abstention rate that rises sharply is a drift signal).

### 8.8 Robustness and safety testing
Metamorphic tests (unit scaling, permuting irrelevant order, adding a duplicate observation); adversarial data-entry errors (unit mix-ups, decimal shifts, swapped analytes) — the system must reject or flag, not silently score; perturbation stability of rankings; fuzzing of API inputs; extreme-value tests; missingness stress tests (drop 20/40/60% of observations); simulated lab-change events.

### 8.9 Explanation provenance
Implemented as in M5: fact table → constrained narrative → verifier. Additional rules: any quantity displayed to a user is computed from stored observations at request time and carries `as_of` and `model_version`; “drivers” are computed from the *deployed* model with a faithfulness test; counterfactuals are verified by re-scoring.

### 8.10 Experiment log
Each experiment has `experiments/EXP-####/` with hypothesis, config, dataset-card links, results JSON, plots, conclusion, and decision (keep/drop/investigate). The log is the evidence for any elimination under Section 13.

---

## 9. System architecture

### 9.1 Target repository layout (monorepo; Phase 0 migrates to this)
```
vigil/
├── AGENTS.md  GEMINI.md  README.md  LICENSE  SECURITY.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md  CHANGELOG.md  CITATION.cff  CODEOWNERS(.github)
├── .agent/                      # executor skills & rules (curated; see repo-standards "working notes" principle)
├── .github/                     # workflows, templates, dependabot, rulesets docs
├── apps/
│   ├── api/                     # FastAPI service (clean architecture: domain / application / infrastructure / interfaces)
│   ├── web/                     # Next.js: clinician workstation + patient/caregiver PWA (shared design system package)
│   └── worker/                  # background jobs: reminders, drift checks, report builds, sync
├── packages/
│   ├── vigil-core/              # shared domain types, analyte registry, unit/LOINC library, FHIR mappers (pure Python)
│   ├── vigil-ml/                # models, features, calibration, conformal, explanation, inference runtime
│   ├── vigil-sim/               # mechanistic cohort simulators + department digital twin
│   ├── vigil-eval/              # evaluation harness, metrics, reports, drift monitors
│   ├── vigil-opt/               # RT scheduling optimiser + fairness constraints
│   ├── ui/                      # design system (accessible components, tokens, i18n)
│   └── contracts/               # OpenAPI spec + generated TypeScript client + JSON Schemas (single source of API truth)
├── data/                        # dataset cards, loaders' configs, DVC pointers (no raw data in git)
├── experiments/                 # EXP-#### records
├── reports/                     # generated evaluation/simulation reports (CI-reproduced)
├── docs/                        # MASTER_PLAN.md, EVIDENCE.md, PROGRESS.md, adr/, design/, runbooks/, clinical/, data/, proposals/, threat-model/, diataxis (tutorials/how-to/reference/explanation)
├── infra/                       # Docker, compose, Helm/Kustomize, Terraform (optional), observability stack
├── scripts/                     # dev tooling, verify-phase gates
└── tests/                       # cross-package e2e, load, security, accessibility, contract tests
```
Tooling baseline (record deviations as ADRs): Python 3.12 + `uv` workspaces, `ruff` (lint+format), `mypy --strict` (or `pyright` strict) on core packages, `pytest` + `hypothesis` + `pytest-cov` + `pytest-randomly`; TypeScript strict, `eslint`, `prettier`, `vitest`, `playwright`, `axe-core`; `pre-commit`; `commitlint` (Conventional Commits); `release-please` or `semantic-release`; `Makefile`/`just` as a uniform entry point (`make setup|lint|test|e2e|bench|docs|verify-phase`).

### 9.2 Service architecture
- **API (apps/api):** FastAPI, async SQLAlchemy 2, Pydantic v2, Alembic; hexagonal layering (domain has no framework imports; enforced by `import-linter`); versioned (`/api/v1`, `/api/v2` strategy ADR); OpenAPI is the contract (`packages/contracts`), consumer-driven contract tests; idempotency keys on mutations; pagination, filtering, ETags; problem+json errors; request IDs; structured JSON logs.
- **Inference runtime:** models loaded from a signed registry; **no pickle**; ONNX/safetensors/skops; versioned model + calibrator + threshold config bundles; inference is a pure function `(patient_snapshot, as_of) → RiskAssessment` with a recorded input hash, making every assessment reproducible; CPU-only budget: p95 < 300 ms per assessment on a 2-vCPU machine.
- **Worker:** queue (Redis + arq/Celery or Postgres-based queue; ADR) for reminders, drift checks, scheduled re-scoring, report generation; idempotent, retried, observable.
- **Web (apps/web):** Next.js App Router, React Server Components where useful; PWA with service worker (Workbox), IndexedDB local-first store, background sync; i18n via ICU message format; design system package with Storybook; state via TanStack Query + a small local-first store; no secrets in client.
- **Real-time:** server-sent events (or WebSocket) for triage queue updates with polling fallback.
- **Deployment profiles:** `local` (SQLite, no auth for dev only, synthetic data allowed), `staging` (Postgres, auth on, synthetic only), `production` (Postgres, auth/consent/audit on, synthetic endpoints disabled, secrets mandatory, config-validation refuses to boot otherwise). Docker images (distroless/slim, non-root, read-only FS), docker-compose for one-machine hospital installs, Kustomize/Helm for clusters, **air-gapped/on-prem install guide** because many facilities will not use cloud.
- **Cloud-optional:** nothing may require a specific cloud vendor; Gemini/LLM use (M5) is optional and behind an interface with a local-model fallback and a full off-switch.

### 9.3 Security architecture (STRIDE threat model in `docs/threat-model/`, reviewed each phase)
TLS everywhere; field-level encryption for direct identifiers; encryption at rest; key rotation runbook; secure session handling; CSRF/XSS/SSRF/SQLi/path-traversal tests; rate limiting; strict CORS (**no `"*"`**, which the prototype shipped); security headers/CSP; dependency pinning with hashes; SBOM (CycloneDX) per release; Sigstore/cosign signing; SLSA provenance goal ≥ L2 (L3 if feasible); secret scanning (gitleaks + GitHub secret scanning); SAST (CodeQL, Bandit, Semgrep); container scanning (Trivy); DAST (OWASP ZAP baseline) in CI; OpenSSF Scorecard ≥ 8/10; no hard-coded absolute paths or usernames (the prototype's default DB URL embedded `/Users/gsanni/...`).

### 9.4 Observability and operations
OpenTelemetry traces/metrics/logs; Prometheus + Grafana dashboards (golden signals + domain metrics: alert rate, abstention rate, reminder delivery rate, queue latency, drift stats); SLOs defined (e.g., API availability 99.5% monthly for clinic hours; triage queue freshness ≤ 5 s; reminder dispatch ≤ 5 min from due time) with burn-rate alerts; runbooks for every alert (`docs/runbooks/`); backup/restore drills with RPO/RTO documented and **tested**; incident process and postmortem template in use.

### 9.5 Performance and scale budgets (tested in CI nightly)
10⁵ patients, 10⁷ observations on a single Postgres instance with documented indexes; triage queue p95 < 400 ms; patient timeline p95 < 600 ms for 5-year history; web initial JS ≤ 180 KB gz on the patient PWA entry route; Time-to-Interactive ≤ 4 s on a throttled “slow 4G, mid-range Android” profile; offline cold-start ≤ 2 s from cache.

### 9.6 Interoperability and data standards
FHIR R4 REST facade for read/export; SMART-on-FHIR launch as a stretch goal behind a feature flag; HL7 v2 ORU lab-result ingestion adapter (common in hospital LIS); CSV/Excel import wizard with schema inference and strict validation (because many sites only have spreadsheets); DICOM *reference* (metadata/links) only — Vigil does not store images in v1.

### 9.7 Quality budgets (CI-enforced)
Back-end line+branch coverage ≥ 90% on `vigil-core`, `vigil-opt`, `vigil-eval` metric code and the explanation verifier; ≥ 80% elsewhere — **coverage is a signal, not the goal** (mutation testing with `mutmut`/`cosmic-ray` on critical modules must kill ≥ 80% of mutants); Lighthouse: Accessibility = 100, PWA pass, Performance ≥ 90 on the patient PWA; axe-core: zero serious/critical; bundle-size budgets; flaky-test quarantine policy (a flaky test is a bug with an owner).

---

## 10. UX, accessibility, content and localisation

1. **Design principles:** triage first; one primary action per screen; show uncertainty visually (intervals, abstention states) rather than hide it; never colour alone; calm tone — families may be reading in distress; defaults safe.
2. **Accessibility:** WCAG 2.2 AA minimum (target AAA for text contrast in patient views); full keyboard operation; screen-reader labelled charts with data-table alternatives; reduced-motion; scalable text to 200%; touch targets ≥ 44 px; tested with real assistive tech in Phase 7.
3. **Low-literacy & voice:** icon+text labels, audio read-aloud for key explanations, voice input for symptom diary (on-device speech APIs where available, with graceful degradation).
4. **Languages:** English (en-NG), Nigerian Pidgin, Yoruba, Hausa, Igbo at launch scope for patient-facing flows; clinician UI English first, extensible. Translations are produced with a **review workflow requiring native-speaker clinician/community validation** (machine translation may draft; humans approve; unapproved strings fall back to English with a visible marker). Medical terminology glossary per language kept in `packages/ui/i18n/glossary`.
5. **Alert & message content design:** a content style guide in `docs/design/CONTENT.md` (verbal uncertainty scale mapped to numeric bands, forbidden phrases, “what to do next” pattern, bad-news mode rules).
6. **Human-factors programme:** formative usability tests with clinicians and caregivers (script and consent in `docs/clinical/USABILITY/`); alert-fatigue simulation; error-prevention review of every data-entry control (units, decimal keypads, range warnings); findings tracked as defects.

---

## 11. Safety, regulatory posture, privacy and ethics

### 11.1 Claims policy (binding on code, UI, docs, commits, reports, marketing)
- Allowed: “decision support”, “signal”, “estimated risk with uncertainty (validated on: …)”, “for clinician review”, “research prototype” (until the maturity ladder in Section 18 says otherwise).
- Forbidden until supported by committed evidence *of the specific claim*: “detects metastasis”, “predicts cancer”, “diagnoses”, “clinically validated”, “FDA/NAFDAC approved/cleared”, “saves lives”, “enterprise-grade/production-ready/frontier-grade/state-of-the-art/zero compromises”, any accuracy figure from synthetic data presented without the word **synthetic** adjacent to it.
- Mandatory notice (`docs/DISCLAIMER.md`, shown in the UI footer and on every export): *Vigil is a research prototype and decision-support aid. It is not a medical device, does not diagnose or treat any condition, and must not replace the judgement of a qualified clinician. Outputs may be wrong. If you are worried about your health, contact your doctor or hospital.* Patient-facing screens add an urgent-symptom instruction (“If you have severe pain, trouble breathing, confusion, a sudden swelling or bleeding, go to the nearest emergency service”).
- A CI check scans the repo for forbidden phrases and for ungrounded numeric claims in README/docs (allow-list for quoted sources).

### 11.2 Hazard analysis (FMEA-style; keep as `docs/safety/HAZARD-LOG.md`, updated every phase; each row needs a verification link)
| ID | Hazard | Harm | Mitigations (must be implemented and tested) |
|---|---|---|---|
| H1 | False reassurance (low score read as “fine”) | Delayed care — the exact original harm | Never show “low risk = safe”; wording “no signal detected *in the data available*”; abstention; reminders keep running; clinician override; sensitivity reported with CI; surveillance schedule never auto-lengthened |
| H2 | False alarm | Anxiety, cost, unnecessary imaging | Alert tiers with α-budgets; confirm-by-repeat pathway (M3); family bands not numbers; alert burden monitoring |
| H3 | Wrong-patient or mis-entered data | Wrong alerts | Two-identifier checks; duplicate detection; double-entry for critical analytes optional; audit; correction workflow with versioning |
| H4 | Unit/decimal/analyte mix-up | Large spurious change | UCUM-strict ingestion; range plausibility; delta checks; explicit confirm for out-of-bound values; never silent coercion |
| H5 | Model drift / dataset shift | Silent performance loss | Monitoring, conformal coverage tracking, shadow mode, rollback, scheduled re-validation |
| H6 | Data breach | Privacy harm, stigma | Encryption, least privilege, audit, breach runbook, data minimisation, on-prem option, penetration tests |
| H7 | Automation bias | Clinician defers to score | Show basis and uncertainty; require disposition + free-text reason for dismissals; training material; measure override rates |
| H8 | Inequitable performance | Worse care for subgroups | Subgroup gates (8.3), site hold-out, reporting, re-weighting/recalibration per subgroup where justified |
| H9 | Reminder privacy leak on shared phone | Unwanted disclosure | Generic message text, PIN-gated detail, per-patient channel preference, number verification |
| H10 | RT optimiser inequity/error | Unfair delay | Fairness constraints, simulation evidence, explanation per move, clinician override, audit of moves |
| H11 | LLM hallucination | False statements | Verifier (M5), templates fallback, LLM off by default in clinical mode |
| H12 | Stale test-ladder data | Futile referral | `verified_on`, staleness flags, feedback loop |
| H13 | Outage during clinic | Lost care | Offline-first; degraded modes; paper fallback export; SLO/runbooks |
| H14 | Family misreads risk | Panic or complacency | Bad-news mode, bands + verbal scale, co-design testing, “talk to your doctor” hand-over |
| H15 | Synthetic data mistaken for real | Misleading claims | `synthetic` badge, API flag, claims-policy CI |
| H16 | Over-trust in evidence-limited harm model (M7) | Mis-prioritisation | Evidence-level labels, ranges, sensitivity analysis, never auto-apply |

### 11.3 Regulatory posture (verify current texts; flagged as such in `docs/regulatory/`)
- **Intended use v1:** clinician-facing decision support and care-coordination tool with transparent basis, for retrospective/silent-mode research and supervised pilots. Patient-facing functions are limited to information, record-keeping, reminders and a request-for-review summary — no diagnostic claims.
- **United States (reference framework):** FDA's revised clinical decision support software guidance (published January 2026; one secondary source also reports a later revision — **verify on fda.gov**) keeps four non-device criteria, including that the clinician can independently review the basis of recommendations and that the software does not analyse medical images/signals or patterns from a signal acquisition system [E17]. Vigil's M2 analyses *patterns in sequences of laboratory results*, which needs a legal reading against criterion 1; do not assume non-device status. The FDA PCCP guidance for AI-enabled device functions is the template for M11's change control [E17].
- **Nigeria:** NAFDAC regulates medical devices; a SaMD registration guideline is reported as effective from 1 July 2024 but has not been verified against NAFDAC's own publication, and academic work argues there is no AI-specific framework yet [E18]. The Nigeria Data Protection Act 2023 treats health data as sensitive personal data; processing needs a lawful basis (typically consent for this use), a data protection impact assessment where high-risk (NDPA s.28), security safeguards, and attention to cross-border transfer and breach notification (verify timelines) [E14]. Ethics approval from an institutional/national health research ethics committee is required for any real-data study.
- **Other:** WHO guidance on AI ethics/governance for health informs the governance design (human oversight, transparency, automation-bias mitigation, stakeholder engagement) [E19]; EU MDR/AI Act apply only if distributed in the EU.
- **Deliverable (executor drafts; qualified humans review):** `docs/regulatory/INTENDED-USE.md`, `REGULATORY-PATHWAY-MEMO.md`, `DPIA.md`, `RISK-MANAGEMENT-FILE.md` (ISO 14971-style structure), `SOFTWARE-LIFECYCLE-PLAN.md` (IEC 62304-style structure), `CLINICAL-EVALUATION-PLAN.md`, `PCCP.md`. These are *prepared for* legal/regulatory/clinical review; the executor never asserts compliance.

### 11.4 Ethics
Consent that is informed, specific and revocable; dignity in language (no “victim/battle” rhetoric in the product); community and clinician co-design; benefit-sharing with partner hospitals (they receive the Missed-Signal Audit and software free); open publication of negative results; a standing ethics review checklist per phase; special handling of bereaved-caregiver data and “memorial” features: none shipped without explicit consent and design review.

---

## 12. Engineering standards (apply `.agent/skills/repo-standards` fully)

- **Target:** repo-standards audit rubric tiers **T0–T5 all scored ≥ 2 by end of Phase 0 and ≥ 3 (“enforced by automation”) by end of Phase 8**, project type = *service + libraries + frontend*. The audit report is committed at each phase (`docs/audits/REPO-AUDIT-P#.md`) with the rubric scores and evidence.
- **Branching/PRs:** trunk-based; protected `main`; short-lived branches `type/short-description`; every change via PR (even solo — the PR is the evidence record); Conventional Commits; PRs ≤ ~400 lines of diff where feasible, one concern per PR, tests included, docs updated in the same PR; PR template filled honestly; squash-merge with meaningful titles. *Branch protection / rulesets require admin rights: the executor writes the exact `gh api` commands in `docs/ops/GITHUB-SETTINGS.md`; the owner applies them (17.3).*
- **Testing pyramid:** unit (fast, pure) → property-based (Hypothesis) → integration (real Postgres in CI via service containers) → contract (OpenAPI) → e2e (Playwright incl. offline) → non-functional (load with k6/Locust, security ZAP, a11y axe, resilience/chaos in compose) → ML-specific (leakage canaries, metamorphic, calibration regression, benchmark regression). Tests must be able to fail; mutation testing on critical modules; no network in unit tests; deterministic time via an injected clock.
- **CI/CD gates (GitHub Actions, actions pinned to full SHAs, least-privilege `permissions`, OIDC for any cloud access):** lint/format/type → unit/property → integration → build → e2e/a11y → security (CodeQL, Semgrep, Bandit, gitleaks, Trivy, dependency review, license check) → ML regression gate → docs build + link check → SBOM + provenance on release. All required checks block merge.
- **Docs (Diataxis):** tutorials, how-tos, reference (generated from code/OpenAPI), explanation (this plan, ADRs). Every public function documented; docs build in CI (MkDocs-Material or Docusaurus; ADR). README is a front door (what/why/quickstart/status/limits), not a brochure.
- **ADRs (MADR):** required for: monorepo layout, language/toolchain versions, auth provider, queue choice, offline sync strategy, model formats and registry, each module's model selection (with experiment links), LLM usage policy, license, i18n approach, deployment profiles, any plan deviation. ADRs are immutable once accepted; supersede instead of editing.
- **Licensing & provenance:** Apache-2.0 for code, CC BY 4.0 for docs, separate data licences; `NOTICE` and third-party license inventory auto-generated; contributor DCO or CLA decision recorded.
- **Dependency policy:** pinned/locked; Dependabot/Renovate + automerge for patch-level after green CI; no abandoned packages (check recency/maintainers); version claims in README must match lockfiles (a CI check compares).
- **Working notes are not product:** scratch plans/handoffs go in `docs/` (curated) or a gitignored folder. The root holds only the front-door files listed in 9.1.

---

## 13. Feasibility & elimination protocol (“try before you cut”)

The owner's instruction: *pursue the possible and the apparently impossible; remove something only if it was actually tried and shown infeasible.* Operationalised:

1. **Pre-register** before running: hypothesis, success metric, dataset/split, comparison baselines, minimum effect, compute budget. Commit it (`experiments/EXP-####/PREREG.md`).
2. **Serious attempts:** at least **three** distinct, competent attempts (different formulations/hyper-parameter regimes/data treatments, at least one from a *different angle*, e.g., a simpler model, a better feature, a different loss, more realistic data) before “infeasible” may be written. Each attempt is logged, including failures, with seeds and configs.
3. **Diagnose before concluding:** failure triage checklist — data leakage? label noise? train/test mismatch? insufficient signal in simulator (i.e., my generator didn't encode the effect)? bug? under-training? mis-calibration? Document which were ruled out and how.
4. **Infeasible vs hard vs blocked:** *Hard* = continue. *Blocked* = external dependency (list it, do all else). *Infeasible* = evidence from step 2–3 shows the pre-registered criterion cannot be met under the stated constraints.
5. **Elimination record** (`docs/adr/` + `experiments/…/CONCLUSION.md`): what was tried, evidence, what *is* shipped instead (the **fallback ladder** below), and what would change our mind (conditions to retry, e.g., “revisit when real partner data arrive”).
6. **Fallback ladders are part of the design, not deferrals.** Every frontier element has a named fallback that still delivers value (Section 6 “Kill” entries). Falling back requires steps 1–5.
7. **Boundary-pushing ideas:** anyone (including the executor) may propose a new frontier idea in `docs/proposals/` using the proposal template (hypothesis, why it could matter to this population, evaluation, kill criterion, risk). The overseer decides inclusion. Ideas already in scope: M3, M4, M5-verifier, M6, M7 digital twin + fairness, M10, M12, cross-generator validation, conformal alert budgets, informative-missingness modelling, mechanistic multi-generator simulation, joint longitudinal-survival comparators, self-supervised lab pre-training, on-device OCR→structured data, offline CRDT sync, bad-news-mode UX, second-look request, caregiver advocacy dossier. Candidate extensions the executor should *investigate and either build or eliminate by protocol*: ctDNA/ imaging-report ingestion with NLP (as additional modality), symptom-only triage for facilities with no labs, wearable/vitals trend ingestion, causal analysis of treatment-delay effects with target-trial emulation on partner data, transfer learning between breast and other cancers' lab dynamics, active-learning loop for clinician feedback, uncertainty-aware conversational interface for caregivers constrained by the M5 verifier, geospatial referral routing (travel time to RT centres), and cost-effectiveness modelling of the Test Ladder.

---

## 14. Roadmap: phases, work packages, exit gates

> **Phase discipline:** phases are sequential; within a phase, work packages (WP) may interleave. A phase closes only when **every exit-gate item** is satisfied *and* the phase report (Section 16) is committed. After a phase closes, the executor stops and waits for the overseer's review verdict in `docs/PROGRESS.md` (`ACCEPTED`, `ACCEPTED-WITH-CONDITIONS`, `REJECTED` + reasons) before starting the next, **unless the verdict file already authorises the next phase**. Phase scope is large by design; do not shrink it, do not split it into permission-seeking chunks, and do not stop mid-phase to report progress.

### Phase 0 — Truth reset & professional foundation
**Objective:** the repository becomes honest, safe, reproducible and standards-grade before any new science is added.
- WP0.1 **Rename & de-Sentinel:** package/app/dir/UI/docs/CI names → Vigil; remove machine-specific paths (e.g., `/Users/gsanni/...` in `config.py` and `implementation_plan.md`); update README badges to *real, verifiable* ones only.
- WP0.2 **Restructure** to the Section 9.1 monorepo with history preserved (`git mv`), removing the empty `src/sentinel_backend` stub and dead code; keep the existing prototype working in a clearly labelled `legacy/` or tagged state **only if needed for reference**, otherwise delete after porting (record in ADR).
- WP0.3 **Remediate every Section 15 finding** that is not scientific (security, config, CORS, auth scaffolding, demo-endpoint gating, pickle removal from the *runtime path*, literal thresholds). Scientific findings are *quarantined*: prototype models are marked `DEPRECATED-INVALID-LABELS`, removed from the default runtime path, and replaced with an explicit “model unavailable (research)” state until Phase 3 provides valid models; UI states “synthetic demo data”.
- WP0.4 **Apply repo-standards in full:** LICENSE, README (front door), CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CODEOWNERS, issue/PR templates, CITATION.cff, CHANGELOG, `docs/` skeleton (Diataxis) and ADR-0001…, `.editorconfig`, `.gitignore`, pre-commit, commitlint, Makefile, devcontainer, Docker/compose, CI workflows (Section 12), Dependabot/Renovate, Scorecard workflow, release automation, SBOM, `docs/ops/GITHUB-SETTINGS.md` with ruleset commands. Run the repo-standards **Audit** and commit `docs/audits/REPO-AUDIT-P0.md`.
- WP0.5 **Safety & claims scaffolding:** `docs/DISCLAIMER.md`, hazard log v0, claims-policy CI check, synthetic badge component and API flag, forbidden-phrase scanner.
- WP0.6 **Verification tooling:** `scripts/verify_phase.py` (checks required artifacts exist per phase, CI green on `main`, no forbidden phrases, no TODO/stubs outside allow-list, coverage/metric thresholds), `make verify-phase PHASE=0`.
- WP0.7 **Test the existing behaviour** well enough to refactor safely (characterisation tests), then raise to the Section 9.7 budgets for the retained code.
- **Exit gate:** CI green on `main` with all Section 12 gates; repo-standards audit scores ≥ 2 on all items and ≥ 3 on T0–T2; zero secrets/hazards; README claims all verifiable; `make verify-phase PHASE=0` passes; Phase-0 report committed.

### Phase 1 — Simulation Laboratory & data foundation
- WP1.1 `vigil-core`: analyte registry (≥ 20 analytes, LOINC/UCUM, biological variation with citations), unit conversion library, plausibility bounds, FHIR mappers; property tests.
- WP1.2 `vigil-sim`: ≥ 3 mechanistic generators with calibration-target tests (Section 6.13); latent-event labelling; informative missingness; inter-lab offsets; error injection (for M3); symptom/PRO generation; Nigerian-context priors (stage mix, subtype mix, missingness/cost) cited from `docs/EVIDENCE.md`; deterministic seeds; dataset cards; throughput benchmark (≥ 10⁵ patients generated in minutes).
- WP1.3 Ingestion framework and loaders for SEER-derived tables (schema + loader contract; actual restricted data are human-acquired), METABRIC & TCGA-BRCA clinical files, Project Data Sphere study packages, MIMIC-IV cancer-cohort builder; each with dataset card and validation suite. Where data are not yet obtained, the loader is developed against the **public data dictionaries** and a fixture generated from them, and the report states exactly which real-data runs are pending (this is a blocker-bounded state, not a stub).
- WP1.4 Leakage test-suite (shuffled-label canary, future-leak detector, outcome-derived-feature static check, scaler-fit checks) as a reusable library with its own tests.
- WP1.5 `docs/data/ACCESS.md` and `docs/clinical/PARTNERSHIP/` packages (Section 7.2).
- **Exit gate:** calibration-target tests pass; cross-generator datasets produced and versioned; leakage suite catches deliberately leaky fixtures; dataset cards complete; all new code meets Section 9.7 budgets; report committed.

### Phase 2 — Evaluation backbone & classical science core
- WP2.1 `vigil-eval` harness (metrics with reference-value tests, splits, bootstrap, subgroup, DCA, lead-time, alert-burden, ablation runner, report renderer, regression gate).
- WP2.2 M2 classical stack: rule baselines, Cox/discrete-time hazard, gradient boosting, joint longitudinal–survival comparator; engineered velocity/acceleration/variability/missingness features; horizon formulation; calibration.
- WP2.3 M1: literature/registry priors, hierarchical Bayesian & multinomial & boosted comparators; calibration; evidence badges; model cards.
- WP2.4 First **honest benchmark report** on T-S data (cross-generator) with explicit “synthetic” labelling and sim-to-real section; experiment records EXP-0001…
- **Exit gate:** one-command benchmark reproduces committed reports; metric implementations verified; baselines present; model/dataset cards; no ROC-AUC≈1.0 results unexplained; report committed.

### Phase 3 — Advanced modelling, calibration, uncertainty, abstention
- WP3.1 Deep irregular-time families (GRU-D, GRU-ODE-Bayes, Neural CDE, continuous-time transformer, GRUwE), forward-only encoders, ensembles, self-supervised pre-training on MIMIC-IV-derived series (if access is granted; else on simulator-derived unlabeled series with the limitation stated).
- WP3.2 Conformal risk control, adaptive conformal, abstention (8.7), OOD detection, calibrated alert tiers (8.6).
- WP3.3 Exhaustive ablations and subgroup studies; failure-mode atlas; stress tests (missingness, shift, noise, unit errors).
- WP3.4 **Model selection by pre-registered criteria** → ADR; ship the winner per Section 13; export to ONNX/safetensors with parity tests; inference runtime in `vigil-ml` meeting p95 budget; model registry + signed bundles.
- WP3.5 M12 feasibility study on multi-site simulation (federated + DP) per 6.12 with conclusion by protocol.
- **Exit gate:** selected model(s) beat the best classical baseline on calibrated net benefit with non-overlapping CIs *or* the classical winner ships with the elimination record; calibration/subgroup gates (8.3) satisfied or documented as release-blocking; alert policy chosen with α-budgets; runtime parity/latency tests green; report committed.

### Phase 4 — Plausibility, explanation, test ladder
- WP4.1 M3 full implementation and validation on simulated ground truth with error injection; RCV tables with cited CVi/CVa; individual reference intervals; inter-lab offsets; three-way posterior calibration.
- WP4.2 M5 fact-table → narrative → verifier; templates in all planned languages (machine-drafted, flagged unreviewed); adversarial suite; faithfulness evaluation of attribution methods.
- WP4.3 M4 evidence base: curated sources for modality–organ sensitivity/specificity ranges, capability registry schema & seed from public information (flagged unverified), ranking engine, metamorphic tests.
- **Exit gate:** M3/M4/M5 acceptance criteria met; verifier 100% on adversarial suite; evidence rows each cited; report committed.

### Phase 5 — Platform backend v2 (M0, M6 backend)
- WP5.1 Data model v2 with Alembic migrations; FHIR R4 mappers/REST; HL7 v2 ORU adapter; CSV/Excel import wizard backend.
- WP5.2 Auth (OIDC), RBAC, consent enforcement, hash-chained audit, field-level encryption, key rotation tooling.
- WP5.3 Follow-up Guardian engine (state machines, escalation, channels: SMS/WhatsApp/email adapters with provider abstraction, sandbox providers, delivery receipts), worker, scheduler, outreach exports.
- WP5.4 Inference service integration, triage-queue service (action-urgency ordering), alert service with acknowledgement dispositions, SSE.
- WP5.5 Offline sync service; contracts package (OpenAPI → TS client), contract tests; load/perf tests to Section 9.5; observability stack; runbooks; backup/restore drill evidence.
- **Exit gate:** RBAC×consent matrix tests; audit-tamper test; contract tests; perf budgets met; chaos/resilience tests; threat model v1; ZAP baseline clean; report committed.

### Phase 6 — Clinician workstation & Family/Patient Companion (M8, M9)
- WP6.1 Design system (`packages/ui`) with Storybook, tokens, dark/light, RTL-ready, i18n infrastructure; accessibility baseline.
- WP6.2 Clinician workstation (all M9 views), keyboard-first intake, offline-capable.
- WP6.3 Companion PWA (all M8 features including OCR draft pipeline with mandatory human confirmation, Second-Look Request, bad-news mode, symptom diary with voice, caregiver sharing).
- WP6.4 Localisation: en-NG, Pidgin, Yoruba, Hausa, Igbo string sets with review-state tracking; glossary.
- WP6.5 Playwright e2e for J1–J3, J5–J7 incl. offline; Lighthouse/axe gates; visual regression; screenshots committed to `docs/design/screens/`.
- **Exit gate:** Section 9.7 UX budgets met; WCAG 2.2 AA automated evidence plus a manual-audit checklist completed; offline e2e passes; report committed.

### Phase 7 — Treatment continuity, RT triage, quality audit (M7, M10, M13-twin)
- WP7.1 Harm model with evidence levels and uncertainty; optimiser (CP-SAT/MILP) with fairness and stability; explanation per move; scheduler UI.
- WP7.2 Department digital twin; policy comparison study (≥ 1,000 replications/policy, sensitivity analysis over harm parameters); conclusion by Section 13.
- WP7.3 Delay ledger, patient notifications integration (M6), audit trail.
- WP7.4 Missed-Signal Audit generator (M10) and validation on injected-truth facilities; privacy small-cell controls.
- **Exit gate:** optimiser correctness/property tests; simulation report committed; fairness tests; J4 and J7 e2e green; report committed.

### Phase 8 — Safety, security, governance, clinical-readiness package
- WP8.1 Complete hazard log with verification links; STRIDE threat model v2; penetration-style test suite (automated) and remediation; SBOM/provenance/signing; Scorecard ≥ 8.
- WP8.2 Regulatory & clinical document set (Section 11.3), DPIA, PCCP, clinical evaluation plan, **pre-registration** of clinical validation (`docs/clinical/PREREGISTRATION.md`) with decision thresholds and statistical analysis plan, DECIDE-AI-style live-evaluation protocol, silent-mode protocol.
- WP8.3 Human-factors study materials and, where participants are not required, heuristic evaluation and cognitive walkthroughs with documented findings.
- WP8.4 On-prem installation guide + automated install test; disaster-recovery drill; load/soak tests; documentation completeness audit; final repo-standards audit scoring ≥ 3 across T0–T4 and ≥ 2 on T5.
- WP8.5 Release candidate `v1.0.0-rc.1` with changelog, signed artifacts, reproducibility statement.
- **Exit gate:** all hazards verified or explicitly accepted by owner; all docs present; RC reproducible; report committed.

### Phase 9 — Real-world validation & deployment (human-dependent; executor prepares and then executes as access arrives)
- WP9.1 Execute data-access applications' follow-ups (drafts from P1) and run T-P analyses as data arrive (METABRIC/TCGA/PDS/MIMIC/SEER).
- WP9.2 Partner retrospective study (T-R): ingest, validate, evaluate against the pre-registered plan, recalibrate, write TRIPOD+AI report; Missed-Signal Audit for the partner.
- WP9.3 Silent-mode prospective evaluation (T-Q) tooling and monitoring dashboards.
- WP9.4 Live pilot support (T-L): training materials, support runbooks, feedback capture, safety monitoring, stop rules.
- WP9.5 Federated pilot if M12 feasibility passed and governance approved.
- **Exit gate:** defined in Section 18 (levels L3–L5); each requires human partners and approvals.

---

## 15. Audit of the existing prototype (state as of commit `fa48736`, 2026-10-14)

Verified by reading the code and running the endpoint tests (2 pass). These are **defects**, not opinions; Phase 0/1/3 must resolve them and the phase reports must reference each ID.

| ID | Finding | Evidence | Resolution phase |
|---|---|---|---|
| A1 | **Circular training label.** Model B's label is the generator's own `is_anomaly` flag on the last lab (`ml/train_lstm.py`, label construction), so it learns the generator, not recurrence | `label = 1.0 if last_lab.get("is_anomaly", False) else 0.0` | P1 (new labels), P3 |
| A2 | **Headline metrics are meaningless.** Val ROC-AUC 1.000 indicates a trivially separable synthetic task/leakage; “R² = 0.7884” for Model A is regression onto a vector the generator invented | README “Trained Artifact” lines | P0 (remove claims), P2 |
| A3 | **Bidirectional LSTM used for forecasting** (sees the future of the window) | `ml/models.py` | P3 |
| A4 | **Hard-coded personal path** as default DB URL | `config.py` (`/Users/gsanni/.gemini/...`); also `implementation_plan.md` | P0 |
| A5 | **CORS allows `"*"`** | `config.py` | P0 |
| A6 | **No authentication/authorisation**; open data-seeding endpoint (`POST /analytics/seed-demo-cohort`) | `api/endpoints/*` | P0 (gate), P5 (real auth) |
| A7 | **Magic number** `0.75` duplicated in code (`inference.py`) and config; thresholds not calibrated | `ml/inference.py` | P0, P3 |
| A8 | **Pickled model artifacts committed** (`baseline_model.pkl`, `feature_scalers.pkl`) with no lineage; unsafe deserialisation | `ml/artifacts/` | P0 (remove from runtime), P3 |
| A9 | **Thin evaluation:** two endpoint tests + one script; no ML/unit/property/failure-path tests; E2E is a script, not a test | `tests/` | P0, throughout |
| A10 | **Zero governance/standards:** no LICENSE, CI, CODEOWNERS, SECURITY, CONTRIBUTING, ADRs, CHANGELOG, templates | `git ls-files` | P0 |
| A11 | **Puffery and unverifiable badges:** “Production Grade”, “Enterprise CDSS”, “Frontier-Grade… zero compromises”, version badges not tied to lockfile | README/plan | P0 |
| A12 | **No disclaimer or synthetic-data labelling** anywhere in code/UI/docs | grep | P0 |
| A13 | **Five analytes, no units/LOINC, no missingness model, no symptoms** | `ml/synthetic_generator.py`, schemas | P1 |
| A14 | **Stub/duplicate package** `src/sentinel_backend/__init__.py` beside `sentinel/` | file list | P0 |
| A15 | **Triage ordered by risk only**, ignoring uncertainty, overdue loops, delay | `patients.py` triage | P5/P6 |
| A16 | **README run instructions are machine-specific** (Homebrew libomp path) | README quickstart | P0 |
| A17 | **“Completion” claimed after one pass** | commit message `feat: complete Sentinel…` | process: Section 0.4, Section 16 |

---

## 16. Reporting protocol (so the overseer can review cheaply and reliably)

1. At phase end, commit `docs/progress/PHASE-N-REPORT.md` containing, in this order: (a) **verdict requested** (“Request acceptance of Phase N”); (b) **exit-gate table** — every gate item, status (`MET`/`NOT MET`/`BLOCKED`), and a *link to committed evidence*; (c) **commands run** with trimmed real output (test summaries, coverage, benchmark metric tables), plus the exact commit SHA; (d) **claims ledger** — every quantitative or qualitative claim made in this phase's docs/UI/README with the evidence file that supports it; (e) **deviations & ADRs** (anything differing from this plan); (f) **failures, dead ends and eliminations** (with experiment IDs); (g) **blockers** requiring human action, with drafted artifacts' paths; (h) **known limitations** (be generous); (i) **defect/finding closure** (Section 15 IDs resolved with commit refs); (j) **self-audit checklist** from `complete-solution` answered line by line.
2. Update `docs/PROGRESS.md` (the ledger): phase status table, last verified SHA, open blockers, pending human actions, plan-version in force. **Do not edit the verdict column; only the overseer does.**
3. Commit messages and PR descriptions follow Conventional Commits; no “complete/done” language unless the gate is met.
4. When a gate is `NOT MET`, say so first and say why; partial credit is fine, disguised partial credit is not.
5. Reports must be short on narrative and rich in evidence. A reviewer should be able to accept or reject from the report plus spot-checks of the linked artifacts.

---

## 17. Governance, change control and human-only actions

### 17.1 Roles
Product owner (Gideon): final authority on mission, ethics, partners, licences, anything outward-facing. Overseer (Claude): owns this plan, reviews reports, issues verdicts, amends the plan. Executor (Gemini/Antigravity): builds, tests, documents, reports, proposes.

### 17.2 Plan versioning
This file has a version header; changes are made only by the overseer (or by the product owner), recorded in `docs/PLAN-CHANGELOG.md`. The executor never edits this file; it files proposals.

### 17.3 Human-only actions (the executor must prepare drafts/commands and list these in `docs/PROGRESS.md` under “Pending human actions”)
Apply GitHub rulesets/branch protection and enable repository security features requiring admin; submit data-access applications (SEER, Project Data Sphere, PhysioNet/MIMIC credentialing, METABRIC/TCGA terms where applicable) and sign data-use agreements; contact hospitals and ethics committees; obtain legal/regulatory review; recruit clinician/caregiver participants; native-speaker translation validation; WhatsApp Business/SMS provider onboarding and sender verification; domain, hosting, credential and secret provisioning; confirm licence choice; any press/publication/outward communication; any deletion of data or history rewriting.

### 17.4 Proposals
`docs/proposals/PROP-####-title.md` (template provided in Phase 0): problem, evidence, proposal, alternatives, evaluation, kill criterion, impact on plan. Proposals do not block work.

### 17.5 Risk register (top risks; maintained in `docs/risk/RISK-REGISTER.md`)
| ID | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R1 | Real data never obtained → no real validation | M | H | Parallel multi-source acquisition; partner package; silent-mode design; honest labelling so synthetic-only is still valuable as software/method |
| R2 | Synthetic-to-real gap invalidates methods | H | H | Multi-generator, calibration targets, cross-generator tests, early real-data cross-checks (P-tier) |
| R3 | Guideline stance (serial markers not recommended) limits clinical acceptance | H | M | Position around adjudication/loop-closure/resource use; evidence generation; do not oversell |
| R4 | Executor over-claims or declares completion early | H | H | Section 0.4, 16; verify-phase gates; overseer review; claims-policy CI |
| R5 | Alert fatigue/automation bias | M | H | α-budgets, tiering, dispositions, human-factors work |
| R6 | Privacy/legal non-compliance | M | H | DPIA, on-prem, minimisation, counsel review |
| R7 | Offline/low-bandwidth complexity underestimated | M | M | Early spikes in P0/P5, offline e2e tests |
| R8 | Harm model evidence is weak (M7) | H | M | Evidence labels, ranges, sensitivity analysis, decision-aid fallback |
| R9 | Translation errors in medical content | M | H | Mandatory human validation, fallback to English with marker |
| R10 | Maintenance burden / bus factor (solo owner) | H | M | Docs, ADRs, automation, open-source, simple deploy |
| R11 | Dependency/supply-chain compromise | L | H | Pinning, SBOM, provenance, minimal deps |
| R12 | Emotional load on the owner | M | M | Overseer reviews carry the load; pace is unhurried; nothing ships without the owner's comfort |

---

## 18. Definition of success

### 18.1 Maturity ladder (what “finished” can honestly mean)
| Level | Name | Meaning | Requires |
|---|---|---|---|
| **L0** | Honest prototype | What existed at `fa48736` *after* Phase 0 relabelling | Phase 0 |
| **L1** | **Software-complete research platform (Vigil v1.0-rc)** | All modules implemented to their acceptance criteria; all tests/gates green; evaluated on synthetic + public data with honest labels; full safety/regulatory document set prepared | Phases 0–8 accepted |
| **L2** | Publicly benchmarked | Reproducible open benchmark and preprint-quality report (TRIPOD+AI) on T-S/T-P tiers; external reproduction by someone other than the builders | L1 + external reproduction |
| **L3** | **Retrospectively validated** in the target setting | T-R results on a partner hospital cohort per the pre-registered plan; Missed-Signal Audit delivered | L2 + partner data + ethics approval |
| **L4** | Prospectively validated (silent mode) | T-Q calibration and lead-time per pre-registration, alert burden within budget, subgroup gates met | L3 + governance |
| **L5** | Clinically evaluated pilot | DECIDE-AI-style early live evaluation with clinicians/families; safety record; usability evidence; decision on wider rollout/regulatory submission | L4 + approvals |

**Gemini's mandate covers L0 → L1 completely and prepares everything for L2–L5.** L3–L5 depend on people and permissions outside the codebase; the product is *not* “successfully complete” in the owner's sense until L3 at minimum, and the plan must keep that visible.

### 18.2 L1 “software-complete” checklist (all required)
1. Every module M0–M13 meets its **AC** with committed evidence; every “Kill” either not triggered or resolved by protocol with an ADR.
2. Every journey J1–J8 has a passing automated e2e.
3. All Section 15 findings closed with references.
4. CI gates (Section 12) green on `main`; Scorecard ≥ 8; repo-standards audit ≥ 3 on T0–T4, ≥ 2 on T5.
5. Reproducibility: `make reproduce` regenerates all benchmark/simulation reports from a clean checkout with fixed seeds, matching committed reports within stated tolerances.
6. Performance, accessibility, offline and security budgets met (Sections 9.5, 9.7, 9.3).
7. Documentation complete (Diataxis), including install-on-prem, operations, API reference, model/dataset cards, hazard log, regulatory set, pre-registration.
8. The claims-policy CI passes and the claims ledger shows no unsupported claim.
9. The owner has reviewed the product in a walkthrough and signed the L1 acceptance in `docs/PROGRESS.md`.

### 18.3 Outcome targets (pre-registered, not promised)
Quantitative targets for lead time gained, false-alarm budget, sensitivity at the operating point, calibration and subgroup parity are **set in Phase 3 from simulation and finalised in Phase 8 with clinician input**, then frozen in `docs/clinical/PREREGISTRATION.md` *before* any real-data evaluation. Engineering targets are fixed now (Sections 9.5, 9.7). A frozen target missed on real data is reported as missed.

### 18.4 What the owner should be able to say at L3+
“The system told us, with honest uncertainty, when to look again; it never let a surprising result be waved away without being checked; it kept every follow-up from being forgotten; it showed families what was happening in words they could use; and when the machine broke, it made the delay visible and fair.”

---

## 19. Glossary
**CDSS** clinical decision support system · **RCV** reference change value · **CVa/CVi/CVg** analytical, within-subject, between-subject coefficient of variation · **LOINC/UCUM/FHIR/SNOMED** health-data coding, unit and exchange standards · **DCA** decision-curve analysis · **ECE** expected calibration error · **PCCP** predetermined change control plan · **TRIPOD+AI / PROBAST+AI / DECIDE-AI / CONSORT-AI** reporting and appraisal guidelines for AI prediction/decision-support studies · **NDPA/NDPC** Nigeria Data Protection Act 2023 / Commission · **NHREC** Nigerian national health research ethics body · **MRD/ctDNA** minimal residual disease / circulating tumour DNA · **RT** radiotherapy · **LINAC** linear accelerator · **ACI** adaptive conformal inference · **DP** differential privacy · **CRDT** conflict-free replicated data type.

*End of Master Plan v1.0.*
