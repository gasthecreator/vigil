---
status: accepted
date: 2026-10-20
decision-makers: Q-7 executor
consulted: Overseer review pending; clinical wording review pending
informed: Contributors
---

# 0052. M3 abstains without a prior measurement

## Context

M3 previously treated the current observation as its own baseline when history was empty, producing a meaningless zero-change comparison. The API also passed future observations into backfilled assessments, and the UI supplied hard-coded probabilities and an unregistered interval when outputs were missing.

## Decision

Return an explicit `abstain` action with null probabilities when no earlier measurement exists or a visible record is non-synthetic while the model lacks clinical validation. Require finite valid model inputs, filter API history strictly before the current specimen time, suppress M3/K2 inference on non-synthetic visible records, persist abstention with a null score, and render missing outputs as unavailable. Do not mutate the overseer-owned P4 acceptance suite; request its action-contract extension through `PROP-CORE-ML-M3-ABSTENTION.md`.

## Consequences

First observations remain recordable without implying stability or generating a false repeat-specimen action. The new action is implemented but still awaits overseer contract disposition, and the plain-language abstention copy awaits clinical review. S7 remains negative for simulator recurrence discrimination and is not affected by this safety repair.
