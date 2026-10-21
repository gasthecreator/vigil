# Quality rerun audit — 2026-10

## Scope and standard

This rerun inspected the ML/statistical core and the evidence paths that claim model validity: K2/S2, K7/S8-K7, K8/runtime, the registered negative K4/K5/K6/M12 studies, relevant model cards and the CI/reproduction entry points. It checked whether committed claims are produced by the current code and whether public methods fail safely when required calibration is absent. It did not treat earlier “closed” ledger rows as proof.

The reported synthetic results were not optimized. S2's test seed has already been examined, so rerunning or changing thresholds on that cohort would be post-hoc tuning. Low performance in the preregistered experiments is not itself a defect: K1, K4, K5, K6 and M12 retain their documented negative or partial outcomes unless a separately preregistered, independent study supplies contrary evidence.

## Findings

### Critical: S2 does not establish the K2 false-alarm guarantee

The legacy [`sequential_k2.py`](../../packages/vigil-ml/vigil_ml/sequential_k2.py) clips log-likelihood increments and cumulative e-values. Those operations do not establish a nonnegative test supermartingale, so Ville's inequality does not justify its reported bound. Its `null_5_severe_mnar_missingness` scenario never drops observations. The benchmark runner [`run_benchmarks.py`](../../scripts/run_benchmarks.py) previously invoked this implementation and overwrote the S2 report/results.

The current [`k2.py`](../../packages/vigil-ml/vigil_ml/k2.py) uses increments of the form `exp(lambda*z - lambda^2/2)`. Such an increment is an e-process factor only when the standardized null residual is conditionally centered and has the required conditional sub-Gaussian moment bound. Its recursive residual is centered only unconditionally under an i.i.d. fixed-mean model; given past observations, its conditional mean is generally nonzero. `sigma_log` is estimated from a finite synthetic calibration cohort; this is not evidence that it upper-bounds the true conditional scale. The current class therefore cannot claim an unconditional patient-level guarantee from its implementation and empirical stress tests alone.

The K2 risk-score adapter also used a fixed `0.15` action cutoff without a calibrated policy source. The cutoff is now an explicit argument; the adapter has no product call sites and no clinical action threshold has been validated.

There is a second provenance problem: [`run_study_s2.py`](../../scripts/run_study_s2.py) states that it grid-searches calibration operating points, but hard-codes `alpha_pt=0.25`, static threshold `40.0`, and calibration FAR `0.0094`. The checked-in S2 report/results have the legacy schema and cannot be attributed to this runner. The existing test cohort (seed 42) is already examined, so the operating-point or performance claims cannot be repaired by rerunning it.

**Action:** S2 is retracted, the legacy writer is disabled, the misleading legacy module and CI canary language are corrected, and S-018 records the unearned guarantee. A new result requires an amended preregistration, computed calibration values, stated distributional/scale assumptions, and a fresh independent test cohort.

### High: K8 runtime previously emitted uncalibrated outputs

[`ConformalRiskControllerK8.calibrate()`](../../packages/vigil-ml/vigil_ml/conformal_k8.py) used NumPy's interpolated quantile and clamped its threshold to `0.05`; neither operation implements the registered finite-sample rank rule. More seriously, [`VigilProductionRuntime`](../../packages/vigil-ml/vigil_ml/runtime.py) created a randomly initialized model by default and never calibrated the controller. It could therefore emit a risk estimate labeled as calibrated without trained weights or a calibration cohort. The controller's positive-score rank calibration also selects an alert threshold; it does not calibrate predicted probabilities or validate the score's clinical meaning. In addition, OOD and high-uncertainty abstentions previously retained the numeric input score.

**Action:** K8 now uses the finite-sample positive-score rank, including the conservative all-alert cutoff when the rank is zero. Every abstention returns no numeric score or score range, and successful predictions are labeled as model scores with a heuristic range, not calibrated probabilities or a conformal interval. This does not validate the runtime model; S-019 registers it as research-only pending a trained artifact, justified calibration, and independent evaluation.

### High: K7 balance and protective-effect sensitivity diagnostics were wrong at edge cases

[`compute_smd()`](../../packages/vigil-ml/vigil_ml/causal_k7.py) returned zero when one treatment arm was empty or had zero total weight, falsely indicating perfect balance. `compute_e_value()` used the lower confidence limit for protective risk ratios, which is farther from the null than the upper limit and overstates the CI E-value. The S8-K7 committed results use harmful effects and are not changed by this edge-case correction.

**Action:** Invalid/empty SMD inputs now raise `ValueError`; E-value CI calculations now use the confidence limit nearest RR=1. Callers and regression tests were updated.

### Known unresolved: K8 “production ensemble” is a hand-written score

The code in [`conformal_k8.py`](../../packages/vigil-ml/vigil_ml/conformal_k8.py) named `ProductionEnsembleK8` combines fixed logistic formulas; it does not call K1/K3/K4/B4 or fit stacking weights. S-016 already records this, and the S9 report warns that its row is not ensemble evidence. K4 also failed its preregistered criteria, so retaining K4 as an ensemble member would be unjustified. The score remains a compatibility stub and must not be used or described as a production ensemble.

## Remediations in this change

- Retracted S2 report/results and disabled the legacy S2 benchmark writer; the Phase 2 benchmark no longer runs or republishes it.
- Removed the obsolete clipped detector from the ML canary and Phase 3 test suite; tests now exercise canonical K2 without claiming that an empirical canary proves validity.
- Replaced K7's misleading empty-arm balance result and corrected protective-effect E-value interval handling.
- Replaced K8's interpolated/clamped calibration threshold with its finite-sample rank rule; abstentions omit numeric scores, and outputs no longer claim probability calibration or conformal intervals.
- Updated the stub registry to distinguish built code from guarantees and deployment claims that remain unearned.
- Regenerated `docs/diataxis/model-cards.md` after the docs-site freshness gate caught the changed K2 model-card title.
- The first Lighthouse CI attempt failed before collecting metrics because Chrome did not publish a debugging port. The CI step now supplies the Chromium executable installed by Playwright; the rerun completed the Lighthouse budgets.

## Checks and limits

Passed locally: Ruff on changed Python files; Python byte-compilation; focused K7/K8 behavior smoke checks; `check_claims.py`; `reality_audit.py --require-stub-registry`; `check_docs_links.py`; `check_i18n_review_state.py`; generated docs-index freshness; `generate_status.py --check`; and `git diff --check`.

Blocked locally: focused pytest collection fails because `pandas` is unavailable; hazard verification cannot load `fastapi`; API-reference freshness cannot import the API app; `uv sync --all-packages` cannot download `mako` because package-index DNS/network access is unavailable. Evidence DOI validation is similarly blocked by network resolution. These local limitations are distinct from the latest remote checks, which all passed on commit `ffe79a6`: CI run [#213](https://github.com/gasthecreator/vigil/actions/runs/39298594098), quality gates [#46](https://github.com/gasthecreator/vigil/actions/runs/39298594072), CodeQL [#101](https://github.com/gasthecreator/vigil/actions/runs/39298594029), and Postgres/images [#53](https://github.com/gasthecreator/vigil/actions/runs/39298594016). The S2 seed-42 study was intentionally not rerun.

The first claims-policy run also scanned a pre-existing generated `site/` directory and reported historical quoted claims. The checker now excludes that generated output; rerunning against repository sources passes.

This is a targeted core audit based on the named modules, study artifacts, ledgers and current CI wiring. It is not a clinical validation, a full line-by-line audit of every app route, or evidence that unreviewed model components are defect-free.

## Human actions still pending

PR5's translation gate remains correctly unresolved until native-speaking clinician/community reviewers complete H-118. H-117 still needs clinician review of the OCR confirmation workflow and consented real laboratory reports. H-305 still requires the repository owner to enable GitHub dependency graph/dependency review. None of these human actions can be replaced by model-generated confidence scores.
