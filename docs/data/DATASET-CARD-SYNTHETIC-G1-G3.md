# Dataset Card: Vigil Simulation Laboratory Synthetic Cohorts (Tiers G1–G3)

**Dataset Identifier:** `DATASET-SYNTHETIC-G1-G3`  
**Dataset Version:** 1.0.0  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §6.13, §14 WP1.2, WP2.4; `docs/ML_PROGRAM.md` §9  
**Data Tier:** `[SYNTHETIC-T-S]` (Synthetic Simulation Laboratory)  

---

## 1. Dataset Description and Purpose
The Vigil Simulation Laboratory generates physiologically grounded, longitudinal synthetic cohorts to benchmark surveillance algorithms without risking patient privacy, premature clinical exposure, or data leakage.

### Intended Use
- Methodological validation: parameter recovery, identifiability, and simulation-based calibration (SBC).
- Algorithmic stress-testing: sensitivity to longitudinal visit sparsity, partial verification bias, and inter-laboratory analyzer calibration offsets.
- Cross-generator robustness testing (Study S9: train on G1+G2, test on G3).

---

## 2. Structural Composition of Generators
The laboratory comprises three structurally distinct mechanistic generators:

| Generator ID | Mathematical Structure | Biological Phenomenon | Noise & Observation Model |
|---|---|---|---|
| **G1 (legacy smooth burden curve)** | Sampled exponential growth passed through a saturation transform, assigned to a recurrence compartment; no ODE integration or marker clearance | Marker and organ-analyte increments are direct functions of current synthetic burden; chemotherapy affects selected lab values but not tumor growth | Gaussian intra-individual biological variation and a configured visit process |
| **G2 (legacy finite burst stress process)** | Samples a small fixed range of burst counts and times; persistent step burden plus a marker increment inside a fixed recent-burst window | Burst increments do not decay through a clearance model; not a Poisson jump-diffusion process | Gaussian intra-individual biological variation and generator-specific missingness |
| **G3 (heavy-tailed noise stress process)** | Linear recurrence-signal ramp near a configured lead window; Student-t measurement noise and sampled pre-analytical error injection | Signal and artifact magnitudes use configured synthetic assumptions; this is not an independent recurrence biology model | Facility offsets and informative missingness under the selected profile |

---

## 3. Synthetic Baseline Profiles (Not Population Estimates)
Population assumptions are stored in versioned JSON under `packages/vigil-sim/vigil_sim/config/` and are generated as synthetic stress-test inputs. They are not calibrated estimates for Nigeria or another population. The former Nigerian subtype and stage claims were removed because their evidence mapping did not support those derived distributions (`docs/EVIDENCE.md` E7/E12 downgrade notes).

- Default compatibility profile: `legacy_synthetic_v0`; retains the old assumed age, stage, subtype, recurrence, site, and competing-event distributions for reproducibility. It is explicitly marked as unsourced and not clinically calibrated.
- `balanced_synthetic_v1`: equal stage, subtype, and recurrence-site probabilities and a bounded uniform age distribution. This neutral profile is used by `EXP-CORE-ML-001` and is not intended to mimic case mix.
- `balanced_synthetic_core_v3`: adds explicit facility-effect, verification, assay-missingness, baseline-symptom, financial-friction, and visit-interval assumptions. These values were formerly implicit generator defaults. It is intended for newly preregistered core-engine work; existing study profiles and outputs remain historical and unchanged.
- Financial-friction and visit-process values are simulator assumptions. They are not population-calibrated and must not be read as evidence about care access.

The current G1/G2 labels overstate their biological fidelity. They do not meet the M13/ML Program specifications for marker clearance kinetics and a stochastic shot-noise process. All results that depend on these generators are simulator-conditional stress results, not evidence from a validated mechanistic simulator. A corrected simulator requires a new preregistration and regenerated studies; historical outputs remain preserved. The simulator's current historical results are also not automatically reproducible from these profile files because the implementation and censor-aware label contract have changed. See ADR-0035 and the per-study status in the progress ledger.

---

## 4. Ground-Truth Latent Exports and Verification Mechanism
Each generated patient trajectory records:
1. **Observable Data:** Standardized laboratory panels (CA 15-3, CEA, ALT, AST, ALP, GGT, Bilirubin, Creatinine, Calcium, WBC), symptom severity scores (Grade 0–4), and imaging flags.
2. **Latent Ground-Truth State (`LatentCompartmentState`):** Synthetic compartment-burden values and model-generated marker quantities. They are exact simulator state variables, not measured biological quantities or calibrated tumor-cell masses.
3. **Partial Verification Stress Mechanism (ML_PROGRAM §4.2):** Imaging probability varies with configured symptom and marker thresholds. This is an explicit synthetic mechanism for testing verification-bias methods; it is not calibrated to or claimed to reproduce a clinical imaging policy.

---

## 5. Ethical, Legal, and Integrity Guarantees
- **Zero Real Patient Data:** Synthesized entirely from differential equations and stochastic mathematical processes.
- **Anti-Leakage Protection:** Features extracted via `vigil-ml` never include future measurements, generator anomaly flags, or outcome labels.
- **Mandatory Synthetic Labeling:** Every exported dataset, report, and UI component carries explicit `[SYNTHETIC]` metadata badges.
