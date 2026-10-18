# ADR 0021: Partner evaluation toolkit, its dependencies, and the candidate model it evaluates

## Status
Accepted as an engineering decision for the DRAFT pre-registration. The deviation in decision 3 must be accepted or rejected by the clinical lead and the statistician when `docs/clinical/PREREGISTRATION.md` is frozen; until then no real-data result can be produced (`scripts/check_prereg_freeze.py`).

## Context
Phase 9 needs a retrospective-partner path: ingest a hospital extraction, refuse identifiers, report every rejected row, and run the pre-registered evaluation. Three facts shaped it:
- The extraction format (`docs/clinical/PARTNERSHIP/DATA-DICTIONARY.md`) had no index date although the pre-registration defines one (completion of primary treatment), and no field for whether restaging imaging was done, which the mandatory verification-bias analysis needs.
- `docs/clinical/PREREGISTRATION.md` section 3 says "recalibrate, never retrain from scratch without an ADR", but there is no clinically trained Vigil model to recalibrate: `vigil_ml.runtime` loads an untrained latency surrogate (`SurrogateInferenceNet`), and every performance figure in the repository is synthetic.
- A first version counted alert episodes. The synthetic dry run showed that this rewards "alert always on" (one alert per patient). It was replaced by counting every alert.

## Decision
1. **New code lives in an existing shared package and in scripts.** `packages/contracts/contracts/partner/` (ingestion, rejection reports, on-site HL7 conversion) now depends on `vigil-core` (analyte registry, units, HL7 parser) and `openpyxl`. No existing module of `contracts`, `vigil-core`, `vigil-ml` or `vigil-eval` was changed; the downstream suites were re-run (see the Tier 1 report). The analysis (`scripts/partner_analysis.py`) *calls* `WindowedFeatureExtractor`, the B1-B4 baselines and `vigil_eval` metrics instead of re-implementing them.
2. **Two columns were added to the data dictionary:** `patients.index_day` (required) and `clinical_outcomes.restaging_imaging_done` (optional; without it the verification-bias analysis is reported as "not run").
3. **The candidate is `GradientBoostingBaseline` fitted from scratch on the partner's development split**, recalibrated on out-of-fold predictions. This departs from "recalibrate, never retrain" because there is nothing to recalibrate. It is stated in `docs/clinical/ANALYSIS-SPEC.md` section 3 and carried by the report. A Vigil-specific model (K1-K3) can replace the candidate when one has been trained and has its own pre-registered validation.
4. **Analysis definitions are frozen with the pre-registration.** The freeze record must carry `analysis_spec_sha256`; `check_prereg_freeze.py` fails on a mismatch. A confirmatory hypothesis is reported as met only if the 95 % CI criterion holds and the Holm-adjusted bootstrap p-value is below 0.05.
5. **Guards that are server-side style invariants of the CLI, tested:** real-data runs require the frozen pre-registration and a partition key from the environment; `--synthetic-dry-run` requires a `SYNTHETIC` marker written by a generator (an accident guard, not tamper protection); the test split is logged on opening and a second opening is refused unless acknowledged as a protocol deviation; a rejection rate above PR-07 stops the analysis.

## Consequences
- Competing-risk handling (death from another cause) is censoring, not cumulative incidence. Reported as an open deviation in the analysis spec.
- No claim about real-world performance follows from anything here. The dry run (`reports/clinical/dry_run/`) checks plumbing and null behaviour on invented data.
- Reversal cost is low: the new modules are additive.
