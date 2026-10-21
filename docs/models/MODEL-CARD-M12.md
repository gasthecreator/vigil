# Model Card: Module M12 — federated averaging and DP-SGD (research module)

**Model identifier:** `MODEL-M12-FEDAVG-DPSGD`
**Version:** 1.0.0-research
**Maturity:** L0. Research code. **Not wired into ingestion, scoring or any API route.** `DRAFT-UNREVIEWED`.
**Governing documents:** `docs/ML_PROGRAM.md` S10; `docs/MASTER_PLAN.md` §6.12; `docs/adr/0027-m12-simulation-only-not-wired.md`; `experiments/EXP-M12-001/`.

## 1. What it is
An in-process FederatedAveraging loop and a DP-SGD step with a moments accountant, used to train a small MLP (Linear → ReLU → Linear) on synthetic multi-site landmarks. Implementation: `packages/vigil-ml/vigil_ml/m12.py`.
Clients send masked weight arrays and the integers n_k. The server returns the n-weighted mean. Pairwise masks cancel in the n-weighted sum. DP-SGD clips each example's gradient to C = 1.0 and adds Gaussian noise with multiplier σ = 1.0 (study values). Privacy unit: one landmark row = one patient.
This is not Flower, not Opacus, not secure hardware, and not a legal privacy mechanism.

## 2. Intended use
Research on synthetic data, to measure the utility cost of federated and DP training of *this* MLP against training it centrally. **Not for clinical use.** No claim of clinical validity, regulatory clearance, or NDPA/GDPR compliance.

## 3. Historical generated output (synthetic only; not current evidence)
> Q-7 audit status: the frozen output is preserved but provenance-incomplete and stale under the corrected censoring contract. Its H1–H4 results and privacy ledger must not support current model selection or a privacy claim. See `experiments/EXP-M12-001/PROVENANCE-AND-CONTRACT-AUDIT.md`.

The generated `REPORT.md` records H3 as met, H2 as not met, B4 above the MLP arms, headline ε̂ 45.959, and a canary AUC of 0.5237. These are preserved report contents only; the provenance and censoring defects mean they are not verified study findings. No kill-rule decision or privacy conclusion follows from them. The module remains unwired and the pilot is not justified (H-116).

## 4. Limits
Synthetic data; one MLP; F/D take more local epochs than C by design; one-row-per-patient DP; in-process aggregation; no membership inference; no real multi-site data. Site names are labels for the sampling design.

## 5. What this card replaces
The retracted S10 report claimed federated parity and an "Approve M12 Federated Training Architecture" decision from hard-coded site AUCs. Those numbers are withdrawn (`reports/ml/RETRACTED/README.md`) and must not be cited.
