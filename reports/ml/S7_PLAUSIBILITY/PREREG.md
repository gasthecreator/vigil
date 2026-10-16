# Study S7 Pre-Registration: Plausibility Adjudication Under Pre-Analytical Error Injection

**Study ID:** S7_PLAUSIBILITY  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-16  
**Governing Documents:** `docs/MASTER_PLAN.md` §6.3, §14 WP4.1; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` RR7, RR14; `docs/EVIDENCE.md` E9  

---

## 1. Study Objective & Clinical Rationale
In serial oncology surveillance, surprising biomarker jumps are frequently dismissed by clinicians as "lab error", delaying confirmation of real recurrence until extensive clinical progression. Conversely, genuine pre-analytical errors (hemolysis, dilution, data entry slips, mix-ups) cause immense patient anxiety and unnecessary costly imaging.

**Core Research Question:** Can the Model M3 Plausibility Adjudicator (`vigil_ml.m3.adjudicate`) reliably discriminate between true biological recurrence, pre-analytical gross laboratory error, and biological within-subject variation across serial longitudinal monitoring, while strictly enforcing the clinical safety policy that **no result is ever dismissed** (only `explained`, `needs_repeat`, or `escalate`)?

---

## 2. Pre-Registered Hypotheses & Programmatic Criteria

- **H1 (Discrimination of Real Recurrence vs Stable Baseline):**
  - Evaluated on cohorts with simulated ground truth.
  - Criterion: Area Under the Receiver Operating Characteristic Curve (AUROC) for `p_real` distinguishing true recurrence from stable trajectories $\ge 0.85$, with 1,000-sample bootstrap 95% confidence interval reported.
  - Programmatic Verdict: `CONFIRMED` if lower bound of 95% bootstrap CI $\ge 0.80$ and point estimate $\ge 0.85$, else `PARTIAL` or `REFUTED`.

- **H2 (Discrimination of Gross Pre-Analytical Error):**
  - Criterion: AUROC for `p_error` distinguishing gross error from all other states (stable + real change) $\ge 0.80$, with 1,000-sample bootstrap 95% CI.
  - Programmatic Verdict: `CONFIRMED` if point estimate $\ge 0.80$, else `NOT MET`.

- **H3 (Posterior Calibration & Brier Skill):**
  - Criterion: Expected Calibration Error (ECE) $\le 0.06$ on contract model cases, and Brier score $\le 0.85 \times \text{Brier}_{\text{prior}}$.
  - On `vigil-sim` simulated cohorts with non-standard noise and kinetics, evaluate empirical calibration and state sim-to-real / sim-to-contract gaps honestly.

- **H4 (Zero-Dismissal Safety Policy):**
  - Criterion: 100% compliance across all evaluated cases:
    - Action `explained` requires $p_{\text{stable}} \ge 0.90$.
    - Action `escalate` requires $p_{\text{real}} \ge 0.60$.
    - If $p_{\text{error}} \ge 0.30$, action is strictly `needs_repeat` (never `explained`, never `escalate`).

---

## 3. Data Generating Mechanisms & Sim-to-Contract Gap Analysis
1. **Contract In-Silico Cohort ($N=3,000$ cases):**
   - Generated per `docs/ml/M3-M5-CONTRACT.md`:
   - Baseline $L \sim \exp(\mathcal{N}(\ln 18.0, 0.3^2))$.
   - History: 3–7 visits with log-normal noise $\sigma = \sqrt{CV_a^2 + CV_i^2}$.
   - True states: $P(\text{error}) = 0.03$, $P(\text{real}) = 0.20$, $P(\text{stable}) = 0.77$.
   - Real change factor $f \sim \text{LogUniform}(1.4, 3.0)$.
   - Error modes (equal probability 1/3): population redrawn $\exp(\mathcal{N}(\ln 18.0, 0.6^2))$, $\times 10$ decimal shift, $\div 10$ decimal shift.
   - Lab change: Multiplicative offset $\exp(\mathcal{N}(0, 0.10^2))$.
2. **Project Simulator (`vigil-sim`) Cohort (Seed 42, $N=500$ patients):**
   - Longitudinal biomarker kinetics with continuous tumor seeding, shedding, clearance, and injected pre-analytical error events.
   - Contrast analysis: Documents exact mathematical divergences between `vigil-sim` ODE/noise distributions and the closed-form log-normal mixture in M3.

---

## 4. Endpoints & Statistical Reporting
- AUROC, ECE, Brier score, and policy action compliance.
- 1,000-sample bootstrap 95% confidence intervals over patients/cases (RR14).
- Programmatic generation of verdict text from computed statistics (RR7).
