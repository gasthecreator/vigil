# Reality Rules — what counts as real in this repository

> Binding. Added in plan v1.2 after the Phase 3 review found fabricated results (hard-coded study numbers, no-op `fit`, "validation" that never touched the model, classes that exist only in docstrings). Enforced by `scripts/reality_audit.py` (CI) and by overseer review.

## The only outcomes that are unacceptable
**A fabricated or stubbed result presented as real.** `NOT MET`, `BLOCKED`, `PARTIAL`, "I could not make this work", and "this model lost to the baseline" are always acceptable and are never penalised. Declaring something `MET` that the code does not do invalidates the entire phase report.

## Rules
- **RR1 Results are computed.** A number in a report, results JSON, model card or PR text must be produced by code that ran on data (simulated or real) and the models under evaluation. No typed-in AUCs, costs, delays, p-values, parameter counts presented as measured, or "realistic trajectories". A different random seed must change the numbers.
- **RR2 `fit` learns.** `fit()` must change model state from data (parameters, trees, weights, posterior). A deliberately stateless rule must say `# reality: stateless` and must not be described as "trained".
- **RR3 Validation exercises the implementation.** SBC, parameter recovery, identifiability, coverage, validity-under-null and calibration checks must run the *actual* inference code on simulator output with ground truth known. A self-contained toy that simulates its own noise is not validation.
- **RR4 No phantom features.** Every class/route named in a docstring, model card, ADR or report exists, is imported by something that is tested, and is exercised by at least one test that can fail.
- **RR5 Models are not formulas in disguise.** A class presented as a trained or mechanistic model must compute its output through its own learned/mechanistic machinery. Hand-set coefficients that mirror the simulator's generating process are *leakage of the generator* and must be labelled as such, never as a model.
- **RR6 Ensembles call their members.** An ensemble must run the real component models; copying their formulas into the ensemble is forbidden. Ensemble weights must be learned on a validation split and the split recorded.
- **RR7 "CONFIRMED" is earned.** Hypothesis verdicts in reports are produced by code comparing results to the pre-registered criteria; prose is generated from that comparison.
- **RR8 Placeholders are registered.** Anything not yet real is listed in `docs/STUBS.md` with owner, reason and plan, and the corresponding exit-gate item is `NOT MET`.
- **RR9 Lead-time and detection claims need a fixed false-alarm rate.** A lead time without a stated false-alarm/alert-rate constraint is meaningless (an "alert on everyone" rule has maximal lead time).
- **RR10 Honest failure is a deliverable.** If a model loses to a baseline, the report says so, with the three §13 attempts, and the baseline ships.

## Enforcement
`python scripts/reality_audit.py` fails CI on: hard-coded float results inside study/benchmark functions (RR1), no-op `fit` (RR2), validation methods that never touch `self` (RR3), phantom classes named in module docstrings (RR4). Passing it is necessary, not sufficient; the overseer still reviews behaviour.
