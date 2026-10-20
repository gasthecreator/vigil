---
id: PROP-CORE-ML-M3-ABSTENTION
title: Add explicit abstention when M3 lacks a prior measurement
author: Q-7 executor
date: 2026-10-20
status: UNDER REVIEW
plan_version_impact: MASTER_PLAN §6.6; P4 contract
---

# PROP-CORE-ML-M3-ABSTENTION: Add explicit abstention when M3 lacks a prior measurement

## 1. Problem Statement

M3's implementation set its personalized baseline to the current measurement when the history was empty. That made the observation compare equal to itself and could produce a high `p_stable`. The P4 contract defines only three adjudication actions and does not specify this input boundary.

## 2. Evidence Base

- Source audit: `packages/vigil-ml/vigil_ml/m3.py::adjudicate` used `log(new_value)` and set `n_hist = 1` for empty history.
- Serving audit: API ingestion passed an unfiltered history, including observations collected after backfilled current results.
- UI audit: `M3AdjudicationPanel` supplied fallback probabilities 0.05/0.02/0.93 and `PatientTimeline` manufactured a ±0.05 interval when the stored result supplied neither.
- S7 simulator recurrence performance remains near chance: manifest-rise AUROC 0.4961 and all-post AUROC 0.4910. This proposal does not change those results or claim clinical validity.

## 3. Proposed Change

Extend M3's output contract with `action="abstain"`, `abstention=true`, null probabilities, and an explicit reason when there is no earlier valid observation or the model has no clinical validation. Reject malformed/non-finite model inputs and reject history entries that are not temporally prior. Serving code must exclude future observations, suppress M3/K2 outputs for non-synthetic records outside silent shadow mode, persist null scores only with an abstention flag, and display no fabricated probability or interval. Patient/caregiver copy must say that no comparison is available and is subject to clinical review.

## 4. Considered Alternatives

- **Use the current result as baseline:** rejected because this creates self-confirming evidence and false stability.
- **Return `needs_repeat`:** rejected because absence of a comparator is not evidence of a specimen/laboratory error and would create a false repeat task.
- **Reject the observation:** rejected because it prevents recording a valid measurement when the model cannot adjudicate it.

## 5. Evaluation & Verification Criteria

- Unit tests prove no-history abstention, null probabilities, and validation of malformed/future inputs.
- API tests prove first-observation storage, explicit abstention, and correct patient explainer routing.
- Migration tests prove null score requires abstention and downgrade refuses data loss.
- UI tests/build prove unavailable outputs are shown without synthetic defaults.
- Existing overseer P4 tests remain unchanged; P4's action contract needs overseer disposition before this extension is accepted.
- Clinical reviewer must review the new patient/caregiver wording before release.

## 6. Kill / Rollback Criterion

Reject this extension if the overseer requires a different representation for “no baseline,” or if migration/API behavior cannot preserve existing scores and represent abstention without converting it to a numeric value. Revert the extension and keep the upstream observation intake blocked until a contract-compliant abstention path is approved.

## 7. Impact on Master Plan

No edit to `docs/MASTER_PLAN.md` is proposed. The P4 acceptance contract and model interface need overseer review; this proposal is not approval to change the frozen acceptance tests.
