# M4 Resource-Aware Test Ladder: contract (written before any M4 code)

> **Status: DRAFT-UNREVIEWED.** Pre-specification for `docs/MASTER_PLAN.md` section 6.4 and stub S-011 (`docs/STUBS.md`). This file is committed before the module, the registry and the tests, so that the behaviours below cannot be fitted to the code. It describes what the engine must do; it makes no claim that any recommendation is clinically correct. No study is run in this tier, so there is no PREREG for a study; the properties below are tested as properties.

## 1. Question M4 answers
Given a suspected organ and the *actual* capabilities of one facility, which imaging or laboratory tests are worth doing at all, in what order of escalation, and what is still unknown after each result. M4 supports a clinician's decision. It never diagnoses, never says "no metastasis", and never says a negative result is reassuring.

## 2. Inputs
| Input | Meaning | Rule |
|---|---|---|
| `organ` | one of bone, liver, lung, brain | other values are refused |
| `prior` | probability that the organ is involved, with an optional interval `[lo, hi]` and a provenance string | caller-supplied. `prior_from_m1()` multiplies M1's site distribution by a caller-supplied probability of any metastasis; M1's site shares come from a sample of patients who already have a metastasis, so the product is an approximation and says so |
| `facility` | a `FacilityCapability` row set: per modality `available`, `turnaround_days`, `price_band` (1 lowest to 4 highest), `distance_band` (1 nearest to 4), `source`, `verified_on` | rows without `verified_on`, or older than 365 days at `as_of`, are **stale** |
| `affordability_band` | optional, patient-consented: highest price band the patient can pay | tests above it are excluded with the reason |
| `as_of` | date used for staleness | explicit, never the wall clock inside the engine |

## 3. Evidence rows
A `TestEvidence` row is one (organ, modality) pair with a list of sources. Each source records a pooled sensitivity and specificity, an optional 95 % interval or reported range, the source id in `docs/EVIDENCE.md`, and the population studied. Rules:
1. Every number in a row is copied from a dossier in `docs/evidence/` and a test checks that it appears there.
2. The interval used by the engine is computed, not typed: for each source the reported interval (or reported range) is used if there is one, otherwise `point +/- 0.10` (an **assumed widening**, flagged on every output that depends on it, because a source without an interval does not tell us how uncertain it is); the row interval is the hull over sources, clipped to [0, 1].
3. A pair without a source is stored with status `unsourced` and is **excluded from ranking**. This includes, in this tier: plain radiograph and ALP/calcium trend for bone, every brain modality, and every modality for which no accuracy source was retrieved.
4. A source whose population differs from the Vigil population (for example colorectal rather than breast primary) is kept and the difference is printed with every recommendation that uses it.

## 4. Quantities
- Information gain `IG(prior, se, sp)`: expected reduction in binary entropy (bits) from observing the test result. It is concave in the prior and, when `se + sp >= 1`, non-decreasing in `se` and `sp`. Interval: minimum over the two prior endpoints at the lower `se`, `sp`; maximum over the prior interval at the upper `se`, `sp`.
- A row whose lower corner has `se + sp < 1` is `non_informative` and excluded.
- **Residual probability after a negative result** `P(involved | negative)` and **after a positive result** `P(involved | positive)`, each as an interval. They are always reported. Output carries `negative_result_excludes_involvement = false` for every recommendation.

## 5. Ladder construction (no free numeric weights)
Cost and delay are not turned into a score, because no evidence in the repository fixes an exchange rate between bits, price bands and days. Instead:
1. Eligible tests: sourced, informative, available at the facility, within the affordability band.
2. A test A **dominates** B if A is no worse than B on price band, turnaround days and the lower bound of IG, and strictly better on at least one. A *stale* row can never dominate a fresh row (its price and availability are not confirmed).
3. The ladder is the non-dominated set ordered by price band, then turnaround, then (descending) IG lower bound. Rung 1 is the recommendation; later rungs are the escalation if the earlier result is inconclusive or negative with a residual probability the clinician is not willing to accept.
4. If nothing is eligible at this facility the outcome is `refer`: other facilities in the registry with an eligible test, ordered by distance band then price band. If none exists anywhere the outcome is `no_sourced_option`, which is not a statement that the patient is well.
5. Stale or unverified availability rows are returned with `availability_confidence != "fresh"` and the instruction to confirm availability before relying on them.

## 6. Properties that must hold (each has a named test)
| ID | Property |
|---|---|
| P1 | Evidence-first: no recommendation without evidence ids; every id exists in `docs/EVIDENCE.md` and is not `BLOCKED`. |
| P2 | Unsourced pairs never appear in a ladder; adding an unsourced row changes nothing. |
| P3 | Raising a test's sensitivity (both ends) never lowers its IG bounds. |
| P4 | Row order of the inputs does not change the output. |
| P5 | Small perturbations of the prior (0.01) leave the ladder unchanged for every seeded worked example; for random registries a perturbation of 1e-6 changes a ladder only when two compared IG lower bounds lie within 1e-4 of each other. |
| P6 | A stale row cannot remove a fresh row from the ladder. |
| P7 | A negative-result residual is always present, lies in [0, 1], and its upper bound is greater than zero whenever the sensitivity upper bound is below 1 and the prior upper bound is above 0. |
| P8 | The output never contains the words "ruled out", "excluded", "safe", "normal", "no cancer" or "negative means"; and `negative_result_excludes_involvement` is false. |
| P9 | Assumed-widening is flagged on every output that depends on it. |
| P10 | The engine reads no clock and no random source: identical inputs give identical outputs. |
| P11 | Over HTTP: clinician and admin only; unauthenticated callers refused; the route has a policy-table entry. |

## 7. Not in scope (stated so it is not mistaken for a gap hidden)
Treatment advice; cost-effectiveness; radiation exposure; patient preference; test-ordering automation; any claim that following the ladder improves outcomes (that is a hypothesis for silent-mode and pilot tiers). The registry of facility capabilities ships only **illustrative tier templates** flagged unverified, because the repository has no verified facility data and none may be invented.
