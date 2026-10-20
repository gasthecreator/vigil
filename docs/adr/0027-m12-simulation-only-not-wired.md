# ADR 0027: M12 is in-process FedAvg + DP-SGD, evaluated on synthetic sites, and is not wired

## Status
Accepted as an engineering decision. `DRAFT-UNREVIEWED` clinically (nothing here is a clinical or legal privacy claim).

## Context
The earlier S10 (`scripts/run_benchmarks.py::run_study_s10` / `render_s10_markdown`) returned literal per-site AUCs and printed "H1 CONFIRMED … Approve M12 Federated Training Architecture" with no client training, no accountant, and no withheld bytes. It is retracted (`reports/ml/RETRACTED/S10_MULTISITE_SYNTHETIC_TRIAL/`). MASTER_PLAN §6.12 and ML_PROGRAM S10 asked for a simulated federated/DP utility study with a 3 pp kill, and for a pilot only after governance.

## Decision
1. **Retract the S10 renderer.** `run_study_s10` and `render_s10_markdown` raise and point at `experiments/EXP-M12-001/`.
2. **Implement FedAvg and DP-SGD in-process** (`vigil_ml/m12.py`): n-weighted iterative averaging, pairwise masks that cancel in the n-weighted sum, per-example clip and Gaussian noise, moments accountant tested on the E27 numerical example. No Flower process, no Opacus dependency (stated in the PREREG).
3. **Pre-register and run** `experiments/EXP-M12-001/` (PREREG committed alone; one frozen run). Kill metric: IPCW AUC drop of FedAvg+DP vs central, 3 pp, Bonferroni.
4. **Accept the result as a simulation claim only.** H3 met; H2 not met; B4 remains stronger; headline ε̂ is large at the registered σ. The module is not wired into ingestion, scoring, or any route. A federated training pilot is a human action (H-116).

## Alternatives considered
- Add Flower and Opacus: rejected in the PREREG. A network stack would make the study non-deterministic across machines; Opacus pins a second autodiff stack. The algorithm is FedAvg; the transport is a function call.
- Tune R, E, σ or C until every hypothesis passed: rejected. Those values were fixed in the PREREG; the frozen run is single-use.
- Wire D because H3 met: rejected. PREREG section 6: even if H3 holds, this is only a simulation claim on this MLP. B4 is stronger. ε̂ ≈ 46 at δ = 1/910 is not a useful privacy budget.

## Consequences
- Model card `docs/model_cards/MODEL-CARD-M12.md` (and the copy under `docs/models/`) describes the simulation, not a product.
- STUBS S-006 records what was built and what remains unbuilt (real data, Flower, Opacus, a pilot, a legal opinion).
- Old S10 literals must not be cited.

## Q-7 audit addendum (2026-10-19)

The original engineering decision remains a record of what was implemented, not current evidence that the registered study is reproducible. Q-7 found that EXP-M12-001 has no entry in the canonical frozen-access log and that its output predates the corrected early-censor label contract. Its results remain preserved but are historical only; see `experiments/EXP-M12-001/PROVENANCE-AND-CONTRACT-AUDIT.md`. The module remains unwired. A replacement study requires new preregistration and seeds.
