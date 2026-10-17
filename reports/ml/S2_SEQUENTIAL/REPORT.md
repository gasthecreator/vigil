# Study S2 Report: Anytime-Valid Sequential Detection Under Repeated Looks

> **Notice:** All analyses performed on **SYNTHETIC TIER G1** data (`vigil-sim` and acceptance stress suite). Results establish statistical properties and method trade-offs, not clinical efficacy.

**Study ID:** S2_SEQUENTIAL<br>
**Protocol Version:** 1.2 (Matched False-Alarm Rate Protocol)<br>
**Execution Timestamp:** 2026-10-16 21:21:30 UTC<br>
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)

---

## 1. Executive Summary & Programmatic Hypothesis Verdicts

Verdicts generated strictly by code from computed bootstrap confidence intervals (RR7, RR14):

- **H1 (Matched-FAR Sensitivity Comparison):**  
  REFUTED (Expected Power Cost): At a matched null false-alarm rate of 0.52%, Model K2 pays an empirical power cost of -11.34 percentage points [95% CI: -15.46 pp, -7.22 pp] relative to static thresholding (K2 sensitivity: 41.6%, Static sensitivity: 52.9%) on this simulator.
- **H2 (Supermartingale Validity Guarantee):**  
  CONFIRMED: Model K2 mathematically bounds patient-level false alarm rate across all 6 stress scenarios (maximum empirical FAR = 0.0213 <= 0.0700 threshold).
- **H3 (Power and Detection Delay under True Kinetic Doubling):**  
  CONFIRMED: Under true kinetic progression streams, K2 achieves 100.0% power on rapid doubling (Td=60d, median delay 96.2d) and 100.0% power on moderate doubling (Td=90d, median delay 117.8d <= 240d).

---

## 2. Honest Finding: The Cost of an Anytime Guarantee on `vigil-sim`

On the project's simulator (`vigil-sim`), healthy biomarker trajectories are tightly regulated around baseline (~18 U/mL). Consequently, a simple static threshold rule ($CA 15-3 \ge 30.0$ U/mL) experiences a very low null false-alarm rate (0.52%) and alerts immediately once a rising trajectory crosses the cutoff.

Model K2 (`SequentialDetector`), by contrast, computes a sequential mixture e-process. Because it mathematically guarantees bounded false-alarm rates under arbitrary monitoring horizons, autocorrelation, and heavy-tailed noise, it requires cumulative evidence over multiple consecutive looks to cross $1/\alpha_{pt}$. At a **matched false-alarm rate (0.52%)**, K2 achieves **41.6% sensitivity** vs **52.9% for the static threshold**, with a median detection delay of **101.4 days** vs **80.0 days**.

**Conclusion:** K2 delivers a provable patient-level false-alarm guarantee under repeated looks, and on this simulator it pays for that guarantee with an empirical power cost (-11.3 pp sensitivity).

---

## 3. Matched-FAR Benchmark on `vigil-sim`

Noise parameter $\sigma_{\log} = 0.059$ was estimated on an independent calibration cohort (seed 999, $N=500$ nulls) disjoint from the evaluation cohort (seed 42, $N=500$).

| Method | Matched Null FAR [95% CI] | Sensitivity [95% CI] | Sensitivity $\Delta$ vs Static [95% CI] | Median Delay | Mean Delay |
|---|---|---|---|---|---|
| `M_Static (Threshold >= 30.0 U/mL)` | 0.0052 [0.0000, 0.0156] | 0.5292 [0.4708, 0.5876] | Ref | 79.5d | 98.0d |
| `K2_Sequential (alpha_pt = 0.15)` | 0.0052 [0.0000, 0.0156] | 0.4158 [0.3608, 0.4742] | -0.1134 [-0.1546, -0.0722] | 101.6d | 127.5d |

---

## 4. Full Parameter Sweep on `vigil-sim`

| Method | Parameter | Null FAR | Sensitivity | Median Delay (Days) |
|---|---|---|---|---|
| `K2_Sequential` | 0.01 | 0.0000 | 0.4124 | 100.7d |
| `K2_Sequential` | 0.02 | 0.0000 | 0.4124 | 100.7d |
| `K2_Sequential` | 0.05 | 0.0000 | 0.4124 | 100.7d |
| `K2_Sequential` | 0.1 | 0.0000 | 0.4158 | 101.6d |
| `K2_Sequential` | 0.15 | 0.0052 | 0.4158 | 101.6d |
| `K2_Sequential` | 0.2 | 0.0208 | 0.4158 | 101.6d |
| `M_Static` | 22.0 | 0.0469 | 0.5430 | 77.0d |
| `M_Static` | 24.0 | 0.0156 | 0.5430 | 77.9d |
| `M_Static` | 26.0 | 0.0156 | 0.5361 | 77.0d |
| `M_Static` | 28.0 | 0.0052 | 0.5292 | 77.0d |
| `M_Static` | 30.0 | 0.0052 | 0.5292 | 79.5d |
| `M_Static` | 32.0 | 0.0000 | 0.5258 | 80.3d |

---

## 5. Acceptance Stress Suite Performance

| Scenario | N Visits / Setup | Empirical FAR / Metric | Target Bound | Verdict |
|---|---|---|---|---|
| `gauss10` | 20 visits, Gaussian $\sigma=0.10$ | 0.0033 | $\le 0.0700$ | PASS |
| `gauss12` | 20 visits, Gaussian $\sigma=0.12$ | 0.0153 | $\le 0.0700$ | PASS |
| `heavy` | 20 visits, Student-$t_5$ noise | 0.0087 | $\le 0.0700$ | PASS |
| `ar1` | 20 visits, Autoregressive $\rho=0.3$ | 0.0213 | $\le 0.0700$ | PASS |
| `anytime_60_visits` | 60 visits long horizon | 0.0060 | $\le 0.0700$ | PASS |
| `missing_30_percent` | 20 visits, 30% missingness | 0.0037 | $\le 0.0700$ | PASS |
| `power_doubling_90d` | $T_d = 90$d, moderate doubling | Sens: 100.0%, Delay: 117.8d | Sens $\ge 75\%$, Delay $\le 240$d | PASS |
| `power_doubling_60d` | $T_d = 60$d, rapid doubling | Sens: 100.0%, Delay: 96.2d | Sens $\ge 85\%$ | PASS |

---

## 6. Execution Traceability
- Execution Script: [`scripts/run_study_s2.py`](../../scripts/run_study_s2.py)
- Results JSON: [`results.json`](./results.json)
- Disjoint Calibration Cohort: `vigil-sim` Seed 999 ($N=500$)
- Test Cohort: `vigil-sim` Seed 42 ($N=500$)
- Stress Cohort: 1,500 synthetic sequences (Acceptance Contract seeds 1–6)
