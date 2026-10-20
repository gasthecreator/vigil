---
status: accepted
date: 2026-10-20
decision-makers: Codex (Executor)
consulted: None
informed: Contributors
---

# 0050. Fail closed on the invalid historical K8 ensemble

## Context

`ProductionEnsembleK8` was an explicitly weighted sum of four hardcoded logistic formulas. It did not call trained K1, K3, K4, or B4 members, and both its training scores and prediction values were derived from fixed scales and defaults. Although the source labels it deprecated and S-016 records that it is not an ensemble, its public `fit` and `predict_risk` methods still returned plausible-looking results.

## Decision

Keep `ProductionEnsembleK8` as an import-compatible name, but make `fit` and `predict_risk` fail closed. The real K8 conformal controller remains separate. Do not alter frozen benchmark artifacts; they remain historical and do not become valid ensemble evidence.

## Consequences

No caller can obtain scores from the invalid formula through the legacy class. A future ensemble requires trained members, registered stacking/calibration, and its own preregistered evaluation; this quarantine does not implement one.
