# Tier 2a report: M4 resource-aware test ladder

> Status: SUBMITTED FOR REVIEW. Verdict, maturity and every overseer column are untouched. Maturity stays L0. `DRAFT-UNREVIEWED`.

## What was built
| Item | Where |
|---|---|
| Contract, committed before any M4 code or registry | `docs/ml/M4-CONTRACT.md` (commit `f3f5778`) |
| Evidence E20 (liver), E21 (bone, two sources), E22 (lung) with excerpts audited by `scripts/audit_excerpts.py` | `docs/EVIDENCE.md`, `docs/evidence/excerpts/E20*`, `E21a*`, `E21b*`, `E22*` |
| Evidence registry and illustrative facility templates | `packages/vigil-ml/vigil_ml/registry/` |
| Pure engine | `packages/vigil-ml/vigil_ml/m4_ladder.py` |
| Route (clinician/admin; refused in silent mode) | `POST /api/v1/test-ladder/recommend`, `GET /api/v1/test-ladder/facilities` (`apps/api/vigil_api/api/endpoints/test_escalation.py`, policy entries in `route_policy.py`, OpenAPI regenerated) |
| Properties P1 to P11 and the maths they rely on | `packages/vigil-ml/tests/test_m4_ladder.py` (37 tests), `apps/api/tests/test_m4_ladder_route.py` |
| Worked examples, written only by their script | `docs/ml/M4-WORKED-EXAMPLES.md` via `scripts/m4_worked_examples.py` (a test fails if the file drifts from the script) |
| Hazard H26 (OPEN), stub S-011, hand-over items H-111 and H-112 | `docs/safety/HAZARD_LOG.md`, `docs/STUBS.md`, `docs/HANDOVER.md` |

No study is run in this tier, so there is no PREREG; the behaviours were fixed in the contract and are tested as properties.

## What this is not
It is not validated. There is no outcome, usability or pilot evidence that following the ladder helps anyone. The accuracy figures are abstract-level, from populations that are not the Vigil population (liver: gastrointestinal primaries, 2002; bone: pooled point estimates from 2011 meta-analyses, one of them breast-specific; lung: one head-and-neck cohort whose reference standard is the CT itself). The facilities are placeholders. The ranking does not model coverage, radiation, contrast risk or patient preference.

## Findings and deviations (all of them)
1. **Chest radiography is not shown informative.** With the E22 sources the lower corner has sensitivity 0.20 and specificity 0.78 (the 0.78 comes from the assumed widening of 0.10 on the point 0.88), so sensitivity + specificity is 0.98, below the contract's threshold of 1. A lung ladder at a facility with only a chest radiograph therefore returns `refer`. The result depends on the assumed widening (see the sensitivity table in the worked examples: informative at 0.05, not at 0.10). The rule was written in the contract before the registry existed and was not changed.
2. **Brain, bone plain radiograph and bone ALP/calcium trend are unsourced** and never ranked; for brain the engine returns `no_sourced_option`. This is a statement about the registry, not the patient.
3. **E22 is partly unverifiable by the audit script.** The abstract numbers (49, 89, 97.3, 97.2) are machine-verified. The 88 percent specificity in the Results and the literature range (20 to 50 percent, 90 to 98 percent) were read from the PMC page on 2026-10-18 and are kept outside any quotation. The paper contradicts itself by one point (88 and 89).
4. **Bone CT has a single source** (all cancers); the breast-cancer meta-analysis did not analyse CT. Bone sources E21a and E21b share an author group and search window, so they are not independent.
5. **Information-gain upper bounds are wide** because intervals reach 1.0 (a logical bound, not a result). The ladder ranks on the lower bound.
6. **Engine ranks CT above bone scintigraphy for bone in the illustrative templates.** That follows from the registered numbers and the placeholder price and turnaround values; it is not a clinical statement, and the model has no notion of whole-skeleton coverage (stated in the worked examples).
7. **Naming deviations from the contract text:** the contract's `affordability_band` input is `max_price_band` in the code; the lung CT modality is named `ct` (as for liver and bone) rather than `chest_ct`. Behaviour is as specified.
8. **Silent mode:** the recommendation route is declared `blocked` (HTTP 409) because its response is a model output; the registry listing is not. This is a design choice recorded in `route_policy.py`, not something the contract fixed.
9. **Process incident, disclosed.** The contract commit had landed on a local review branch and my first evidence commit on an unrelated local branch (`fix-next15`), and that commit did not contain the four excerpt files although `docs/EVIDENCE.md` linked to them. I moved both commits onto `feat/tier2-m4-ladder` (cherry-pick), restored the local `fix-next15` pointer to its pushed commit, re-fetched the four PubMed abstracts and the PMC page, rewrote the excerpts, and re-ran `scripts/audit_excerpts.py` and `scripts/check_evidence.py` (both pass) before committing them in `fe2e7ef`. Nothing was pushed from the wrong branch.
10. **Test strength.** Five deliberate mutations of the engine were made while writing the tests (ignoring staleness, wrong residual corner, informativeness always true, unsourced rows ranked, wrong gain lower-bound corner). The first version of the staleness test did not catch its mutation (the stale row did not actually dominate); it was rewritten and then failed under the mutation. The engine file was restored from a copy after each mutation.

## Files changed outside this tier's scope
`tests/security/test_route_policy_full_matrix.py` (a valid body for the new route, in a file I own), `tests/security/test_penetration_suite.py` (two rows added to `OPENAPI_RBAC_POLICY` for the new routes, because that suite fails on any route without a row; no existing row changed, and the rows agree with the declared policy so the PROP-0004 difference set is unchanged), `apps/api/vigil_api/schemas/v2.py`, `apps/api/vigil_api/api/router.py`, `apps/api/vigil_api/route_policy.py` (additions only), `docs/api/openapi.json` (regenerated), ledger row T2a (my own). `tests/acceptance_*`: untouched.
