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

## 3. What was measured (synthetic data only; `experiments/EXP-M12-001/results.json`, `CONCLUSION.md`)
- Pre-registered H3 (FedAvg+DP within 3 pp of central on pooled IPCW AUC) was **met** (drop −0.0506; Bonferroni interval [−0.0994, −0.0034]).
- H2 (FedAvg without DP within 3 pp of central) was **not met** (drop 0.0617; Bonferroni [0.0067, 0.1179]).
- B4 (gradient boosting, pooled, not federated) had mean pooled AUC 0.8277 against 0.7108 (D), 0.6602 (C) and 0.5985 (F).
- Mean headline ε̂ at δ = 1/910 was 45.959 (loose). Canary with σ = 100 had mean pooled AUC 0.5237 (not VOID).
- The kill rule did not fire. Nothing is wired. A pilot is not justified by these numbers (H-116).

## 4. Limits
Synthetic data; one MLP; F/D take more local epochs than C by design; one-row-per-patient DP; in-process aggregation; no membership inference; no real multi-site data. Site names are labels for the sampling design.

## 5. What this card replaces
The retracted S10 report claimed federated parity and an "Approve M12 Federated Training Architecture" decision from hard-coded site AUCs. Those numbers are withdrawn (`reports/ml/RETRACTED/README.md`) and must not be cited.
