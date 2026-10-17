# Phase 3B acceptance contract — K2 (sequential detection) and K8 (conformal control)

Overseer-authored. `tests/acceptance_3b/` must not be edited by the builder (the overseer will diff it). Run with
`VIGIL_ACCEPT_3B=1 uv run pytest tests/acceptance_3b -v`. Modules default to `vigil_ml.k2` and `vigil_ml.k8`
(override with `VIGIL_K2_MODULE` / `VIGIL_K8_MODULE` for harness self-tests only). These tests are **behavioural**: they
simulate data in the test itself and check the statistical guarantee, so they cannot be satisfied by describing a method.
Honest gaps: register `K2-VALIDITY`, `K2-POWER`, `K8-CRC`, `K8-OOD`, `K8-ACI` tokens in `docs/STUBS.md`
(visible `xfail`, gate `NOT MET`).

## K2 — `vigil_ml.k2`
```python
class SequentialDetector:
    def __init__(self, alpha_pt: float = 0.05, sigma_log: float = 0.12, burn_in: int = 3): ...
    def update(self, day: float, value: float | None) -> bool   # True once an alert has been raised (latched); None = not measured
    @property
    def alert(self) -> bool: ...
    @property
    def log_e(self) -> float: ...        # current log e-value (anytime-valid evidence against "no change")
```
`sigma_log` is the assumed population within-subject SD of log(marker). The detector must not need the true generating
parameters, must handle irregular spacing and missing values, and must monitor indefinitely.
1. **Patient-level validity (`K2-VALIDITY`):** for 1,500 simulated no-recurrence patients × 20 visits (irregular, baseline level varies by patient), false-alarm
   proportion ≤ α_pt + 0.02 in each scenario: Gaussian σ=0.10; Gaussian σ=0.12; heavy-tailed (Student-t5, sd 0.10); AR(1) ρ=0.3 (σ=0.10).
2. **Anytime validity:** the same rate with 60 visits per patient (≤ α_pt + 0.02) — a per-visit threshold fails this.
3. **Missing data:** with 30% of values `None`, no exception and rate ≤ α_pt + 0.02.
4. **Latching:** `alert` never reverts to False.
5. **Power (`K2-POWER`):** exponential growth after onset at visit 6, doubling time 90 days, σ=0.10, 20 visits: alert for ≥ 75% of patients, median delay ≤ 240 days after onset; doubling time 60 days: ≥ 85%. (An always-quiet detector must fail.)

## K8 — `vigil_ml.k8`
```python
class ConformalRiskController:
    def __init__(self, alpha: float): ...
    def fit(
        self, scores: np.ndarray, labels: np.ndarray
    ) -> "ConformalRiskController": ...  # calibration set
    def decide(self, scores: np.ndarray) -> np.ndarray: ...  # True = alert


class OODGate:
    def fit(self, X: np.ndarray) -> "OODGate": ...
    def is_ood(self, X: np.ndarray) -> np.ndarray: ...


class AdaptiveConformal:
    def __init__(self, alpha: float, gamma: float = 0.005): ...
    def update(self, covered: bool) -> None: ...
    @property
    def alpha_t(self) -> float: ...
```
6. **Conformal risk control (`K8-CRC`):** over 300 repetitions (calibration n=800, prevalence 0.2, positives ~N(1.2,1), negatives ~N(0,1); test n=4,000), mean false-negative rate ≤ α + 0.015 for α ∈ {0.1, 0.2}, **and** mean false-positive rate ≤ the oracle FPR at FNR=α plus 0.10 (not trivially alerting everyone).
7. **OOD gate (`K8-OOD`):** fit on 2,000 N(0,I₆) samples: ≤ 8% of fresh in-distribution samples flagged; ≥ 90% of samples shifted by +4 SD in three dimensions flagged.
8. **Adaptive conformal (`K8-ACI`):** in a 5,000-step stream whose error scale drifts from 1 to 2, the long-run miscoverage over steps 1,000–5,000 is within α ± 0.03, while a non-adaptive set (the test shows this) misses by more than 0.05.
