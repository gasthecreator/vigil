# EXP-M12-001 conclusion (SYNTHETIC): H3 met on this MLP; M12 is not wired and is not a privacy claim

> **Q-7 audit status:** The generated results below are preserved historical output, but are provenance-incomplete and stale under the corrected censoring contract. The frozen access is missing from `data/audit/frozen_test_access.jsonl`; unknown early-censor labels were not handled by this runner. Do not use H1–H4 or the reported epsilon as current model-selection evidence. See [`PROVENANCE-AND-CONTRACT-AUDIT.md`](PROVENANCE-AND-CONTRACT-AUDIT.md). The original study output is not rewritten.

**Decision.** The pre-registered kill criterion H3 (FedAvg + DP-SGD stays within 3 percentage points of centralised training on pooled IPCW AUC) was **met**. The kill rule therefore does **not** fire. Under `PREREG.md` section 6 that is still only a **simulation claim on this model and this partition**: `vigil_ml/m12.py` stays research code; it is not wired into any pipeline, not a pilot, and not a legal privacy determination (NDPA/GDPR/HIPAA). (ε, δ)-DP is a bound on a mechanism. Flower was not run; Opacus was not added.

All numbers below are copied from `results.json` / `REPORT.md`, which `run.py --frozen` wrote (10 frozen replications, one run). Synthetic data only.

## Strongest baseline first
Pooled IPCW ROC-AUC at 365 days, mean over 10 frozen replications (`REPORT.md`):

| Arm | Mean pooled AUC |
|---|---|
| B4 gradient boosting (descriptive ceiling, not federated, not DP) | 0.8277 |
| D FedAvg + DP-SGD | 0.7108 |
| C central MLP (4 epochs) | 0.6602 |
| F FedAvg without DP | 0.5985 |

B4 remains the strongest of the four numbers. The study question was whether *this* MLP loses more than 3 pp when trained federated and with DP, relative to training it centrally — not whether it beats B4.

## Hypotheses (as computed in `REPORT.md`)
- **H1 (local silos, descriptive).** **Not met.** G_CE mean 0.1096, 95% interval [0.0621, 0.1597]; the lower bound is not > 0.10.
- **H2 (FedAvg without DP within 3 pp of central).** **Not met.** D_F mean 0.0617, Bonferroni interval [0.0067, 0.1179]. Both the point and the upper bound exceed 0.03.
- **H3 (FedAvg + DP-SGD within 3 pp of central) — the kill.** **Met.** D_D mean −0.0506, Bonferroni interval [−0.0994, −0.0034]. The drop is negative: D's mean pooled AUC (0.7108) is higher than C's (0.6602). The registered rule asks only that the drop's point and Bonferroni upper bound are ≤ 0.03.
- **H4 (NB@0.10 drop, descriptive).** **Not met.** Dnb_D mean 0.1187, 95% interval [0.1035, 0.1348]. Better AUC did not produce better net benefit at the study threshold 0.10.
- **Canary.** Mean pooled AUC of paradigm D with σ = 100: 0.5237. **VOID:** False (threshold 0.60).
- **Kill rule fires:** False. Fallback (federated evaluation only) is not invoked by the rule. It is still what would ship as a *product* behaviour if anyone asked: a site can score a shipped model locally. Nothing is wired.

## Privacy ledger (not a clearance)
Mean headline ε̂ (max over the five sites, δ = 1/910): 45.959. Noise multiplier σ = 1.0, clip C = 1.0, as registered. That is a **loose** (ε, δ) bound after the registered number of DP-SGD steps. It is not evidence that records are protected in a hospital, and it is not an NDPA/GDPR determination.

## Why D can beat C without that being a success story
The registered design gives C **4** epochs on the pooled landmarks and gives F/D **20 rounds × 2 local epochs**. D therefore takes more noisy steps than C takes clean ones. H2 shows that extra FedAvg steps without DP did **not** help (F is 6 pp behind C). D's higher AUC than C is the registered comparison, not a post-hoc longer run of C. It is not a reason to prefer DP-SGD over B4 (0.8277 vs 0.7108), and it is not a reason to start a federated training pilot.

## Diagnosis (MASTER_PLAN §13.3)
| Item | Finding |
|---|---|
| Leakage | Not found. `m12.py` does not import the simulator; `latent_*` scrambling does not change X, y or trained weights (`test_causality_latent_columns_do_not_change_weights`); the canary with σ = 100 has mean pooled AUC 0.5237; the server function never sees unmasked client arrays (`test_secure_aggregation_masks_and_server_blindness`). |
| Bug in FedAvg / DP-SGD / accountant | Tested for, none found: FedAvg identity, n-weighted mask cancellation, clip of a norm-10 gradient to C = 1, accountant on the E27 example ε = 1.259 in [1.15, 1.40], planted signal, toy canary (`packages/vigil-ml/tests/test_m12.py`). |
| Train/test mismatch | Not claimed. Test landmarks are a fresh `generate_cohort`. |
| Under-training of C | Likely part of why D > C: see above. Not changed after seeing the result. |
| Label noise | Simulator labels are observed recurrence within 365 days at a landmark visit. |

## What ships instead
Research code in `vigil_ml/m12.py` and this study. **No federated training in any product path.** If a later real-data study is ever run, federated *evaluation* (share aggregate metrics, not weights) is the conservative default. A training pilot is a human action (H-116) and is not justified by this file.

## What this is not
- Not evidence that federated+DP training is clinically useful, safe, or private in the legal sense.
- Not evidence that the 3 pp kill is the right product bar: B4, which is not federated, is far ahead of every MLP arm.
- Not a finding of infeasibility: MASTER_PLAN §13.2 requires three distinct serious attempts before that word. One MLP, one partition, one (σ, C, R, E) was tried.
- Not evidence about real hospitals or patients.

## What would change the decision
Real multi-site laboratory series under a data-use agreement; a model that is actually a candidate for shipping (B4/K3), federated without giving F/D ten times the local epochs of C; a noise multiplier that yields a small ε at this δ; membership-inference tests on real records. Each would need its own pre-registration.

## Everything changed after the pre-registration (the complete list)
_None._ No amendments. The engine, runner and tests were committed after the PREREG (commit `96610c7`), by design. Development replications 0, 1, 2 were run once (`dev_results.json`) and not used to change R, E, σ, C, learning rate, architecture, site table, τ, threshold 0.10, or the hypotheses. The frozen run was executed once.

## Disclosures
- In-process FedAvg is the registered "Flower or equivalent": there is no gRPC server.
- DP-SGD is implemented in this repository, not via Opacus.
- Secure aggregation is pairwise masks with n-weighted cancellation so the server's n-weighted mean equals the n-weighted mean of the unmasked weights.
- The 0.10 net-benefit threshold is a study threshold, not a clinical cut-off.
- Site names ("rural mission", …) are labels for the sampling design, not real facilities.
