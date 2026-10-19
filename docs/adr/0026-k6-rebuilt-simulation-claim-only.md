# ADR 0026: K6 is rebuilt as a tested planner, the old S6 is retracted, and any claim is a simulation claim only

## Status
Accepted as an engineering decision. `DRAFT-UNREVIEWED` clinically (nothing here is a clinical claim).

## Context
The earlier K6 (`vigil_ml/active_sensing_k6.py`) never simulated a patient: `recommend_next_action` was a hand-written `if` ladder on a risk number (thresholds 0.10, 0.15, 0.45 and fixed intervals 14, 45 and 180 days) with "expected information gain" typed as 0.12, 0.48, 0.85 and 0.25. Study S6 returned literal dictionaries (visits 20.0 vs 11.2, costs $400 vs $204, delays 42.1 vs 47.6) and printed "H1 CONFIRMED". The K6 model card repeated those figures. `docs/ML_PROGRAM.md` §3.6 asks for a comparison of adaptive schedules against fixed, heuristic and risk-triggered schedules at equal budget, labelled as simulation.

## Decision
1. **Retract old S6** (already under `reports/ml/RETRACTED/S6_ACTIVE_SENSING/`; banners added). `run_study_s6` raises and points to `experiments/EXP-K6-001/run.py`. The hard-coded renderer is deleted. The model card is rewritten without the retracted numbers.
2. **Build K6 as a planner** (`vigil_ml/k6.py`, `k6_engine.py`) plus a dense-world surveillance layer (`vigil_sim/surveillance.py`): a calibrated multi-horizon hazard, a finite-horizon cost-of-delay objective (PREREG amendment 1), a shared alert-and-imaging rule, and a frontier comparison at equal assumed cost. Export is XGBoost JSON plus isotonic knots (no pickle), with a round-trip test. **Not built:** nested-Monte-Carlo expected information gain on K1, reinforcement learning.
3. **Pre-register and run** `experiments/EXP-K6-001/` (PREREG committed alone; frozen run 1 superseded after a panel-table defect; frozen run 2 is the decision).
4. **Accept the result**: H1 and H2 met in this simulator (2.3 and 0.8 days); H3 not met; the PREREG already says that even then K6 is a suggestion with reasons shown and only a simulation claim (`experiments/EXP-K6-001/CONCLUSION.md`). The module stays as research code at maturity L0 and is wired to nothing. E25 (markers not recommended in asymptomatic patients) is not overruled.

## Alternatives considered
- Keep the old module and fix its study: rejected; the old method never ran a policy against a patient.
- Tune until H3 passes, or add a minimum effect size to H1 after seeing 2.3 days: rejected; the frozen run is single-use and the rule is the one pre-registered.
- Ship risk-triggered suggestions only: that is the fallback if H1 holds and H2 fails. H2 met on G1; it fails on G3 (descriptive). The selected sentence is the stricter one already in the PREREG.

## Consequences
- `docs/models/MODEL-CARD-K6.md` and `docs/model_cards/MODEL-CARD-K6.md` are rewritten without the retracted dollar figures.
- STUBS S-005 states K6's status exactly (planner and study built; simulation H1/H2 met, H3 not met; not wired; not a clinical claim; EIG/RL not built).
- No API route, no ensemble term, no "next visit" suggestion is added in this change.
- Not decided here: whether a different objective, a real-data study, or a detection rule without the symptom clause would change the 2.3-day margin. `CONCLUSION.md` lists what would change the decision.
