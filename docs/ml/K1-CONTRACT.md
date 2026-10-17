# K1 acceptance contract (overseer-authored; Gemini must not edit `tests/acceptance_k1/`)

K1 is accepted only when the overseer-authored tests in `tests/acceptance_k1/` pass **without modification**, run as:

    VIGIL_ACCEPTANCE=1 uv run pytest tests/acceptance_k1 -v

Purpose: the builder must not grade its own work. These tests define "real" at the behavioural level (what comes out of the inference code), not at the level of your function names.

## Required public API (module `vigil_ml.k1`; override with env `VIGIL_K1_MODULE` only for harness self-tests)

```python
@dataclass(frozen=True)
class K1Params:
    doubling_time_days: float  # tumour doubling time
    shedding_ca153: float  # marker shedding rate per unit burden
    clearance_ca153: float  # marker clearance rate
    onset_day: float  # recurrence seeding day (>0)


PARAM_NAMES: tuple[str, ...]  # exactly the four field names above (extra names allowed, tested too)


def sample_prior(rng: np.random.Generator) -> K1Params: ...


class K1Observations:  # whatever you need, but must expose:
    days: np.ndarray  # visit days (increasing)
    values: dict[str, np.ndarray]  # analyte -> observed values (NaN = not measured)


def simulate_patient(
    params: K1Params, schedule_days: Sequence[float], rng: np.random.Generator
) -> K1Observations:
    """Forward-simulate observed analytes with measurement noise using the SAME dynamics the
    inference routes assume (the model's own ODE + observation model)."""


ROUTES: dict[str, Callable[[K1Observations, np.random.Generator, int], dict[str, np.ndarray]]]
# route(obs, rng, n_draws) -> {param_name: np.ndarray of n_draws posterior samples}
# Required keys: "amortized", "ukf", "nuts", "npe"   (particle filter optional)
#   amortized : the trained recognition network (no per-patient optimisation at inference)
#   ukf       : unscented/particle filter posterior from sequential filtering over the visits
#   nuts      : reference gold-standard MCMC (PyMC / NumPyro NUTS) on the same likelihood
#   npe       : neural posterior estimation / simulation-based inference (sbi or equivalent)


def risk_from_posterior(samples: dict[str, np.ndarray], horizon_days: float) -> float:
    ...
    # recurrence probability within horizon, derived ONLY from posterior samples via the dynamics
```

`HybridKineticModelK1.predict_risk(X)` must be computed through `risk_from_posterior(...)` applied to the amortised route; it must not contain a head trained directly on the recurrence label.

## Honest gaps
A route you cannot complete must not be named in code, docs or reports. List it in `docs/STUBS.md` with the exact token `K1-ROUTE:<name>` in its row; the corresponding acceptance test is then reported as `xfail` (visible in the output) and the gate item is `NOT MET`. Anything else that fails is a failure.

## What the tests check
1. **Routes exist** (or are registered stubs).
2. **Recovery with posterior-derived intervals:** over 40 simulated patients per route, 90% intervals computed *from the route's samples* cover the true doubling time 75–97% of the time; correlation of posterior mean with truth ≥ 0.6.
3. **SBC through each route:** ≥ 60 prior draws (30 for `nuts`), rank statistics of the true parameter within the route's own posterior are uniform (KS p > 0.01) for every parameter in `PARAM_NAMES`.
4. **Routes agree:** on 5 patients, the `nuts` posterior mean of doubling time is within 30% of the `amortized` and `npe` means (and each within the other's 95% interval).
5. **Risk is posterior-derived and monotone:** `risk_from_posterior` increases when posterior doubling-time samples are shortened (others fixed) and when the horizon is lengthened.
6. **No label head:** the K1 model has no parameter or attribute whose name contains `risk_logit` or `label_head`.
7. **Identifiability is computed:** `HybridKineticModelK1().identifiability_analysis()` returns `eigenvalues` over all `PARAM_NAMES` (length == number of parameters) and `non_identifiable` equals exactly the parameters implicated by eigenvalue ratio < 1e-6 (computed, not typed).

## Contract v2 (added after the first K1 acceptance pass found loopholes)
Added in `tests/acceptance_k1/test_k1_contract_v2.py`, run with `VIGIL_ACCEPTANCE=1 VIGIL_CONTRACT_V2=1` (CI must set both once K1 is fixed) (same rules: do not edit; `K1-…` stub tokens in `docs/STUBS.md` give a visible `xfail` and a `NOT MET` gate):
8. **Routes are genuinely distinct.** `ROUTES["amortized"]` must be a trained recognition network and must not call or alias the `npe` route (not the same callable; source must not reference `npe`/`_route_npe`; same-seed draws must differ).
9. **Training is real (`K1-TRAIN`).** `train_amortized(n_sims: int, seed: int, shuffle_pairs: bool = False) -> {"train_loss": list, "val_loss": list}` must exist; loss histories come from actual optimisation (validation loss falls by ≥ 0.2 from the first epoch; with `shuffle_pairs=True` — parameters shuffled relative to their simulated observations — the improvement is < 0.05; same seed reproduces the history exactly, a different seed does not). Loss curves must never be generated by a formula.
10. **No pickled artefacts.** No `.pt/.pth/.pkl/.pickle` files under `packages/`; no `weights_only=False` or `pickle` in K1 source. Use safetensors / ONNX / retrain-on-load with a fixed seed.
11. **K1 works on the project's simulator (`K1-WORLD`).** For 300 patients from `vigil_sim` G1 (seed 5), landmark day 365: feed each patient's observed CA 15-3 series up to day 365 through `ROUTES["amortized"]`, compute `risk_from_posterior(samples, 730.0)`, and require ROC-AUC ≥ max(0.55, AUC of the plain last-observed-CA-15-3 rule on the same patients − 0.02) for recurrence in (365, 730] (patients recurring earlier or lost earlier are excluded). Passing the earlier tests only shows the model recovers parameters in its *own* world; this shows it is useful in ours. Failing honestly means registering `K1-WORLD`.


### Errata (overseer, 2026-10-16)
The v2 world test (item 11) originally read the marker values from `observed_ca_15_3`, which in `vigil-sim` is a **boolean 'was measured' flag**; the values are in `ca_15_3`. The test was fixed to use `ca_15_3` for rows where `observed_ca_15_3` is true. The earlier 'feasibility' figure (reference AUC ≈ 0.53) was computed from the flag and was wrong. This was the overseer's error. A builder who believes an acceptance test is wrong must file `docs/proposals/` and continue; working around a test is not allowed.
