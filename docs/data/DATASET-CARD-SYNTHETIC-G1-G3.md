# Dataset Card: Vigil Simulation Laboratory Synthetic Cohorts (Tiers G1–G3)

**Dataset Identifier:** `DATASET-SYNTHETIC-G1-G3`  
**Dataset Version:** 1.0.0  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §6.13, §14 WP1.2, WP2.4; `docs/ML_PROGRAM.md` §9  
**Data Tier:** `[SYNTHETIC-T-S]` (Synthetic Simulation Laboratory)  

---

## 1. Dataset Description and Purpose
The Vigil Simulation Laboratory generates longitudinal synthetic stress cohorts to exercise surveillance algorithms without exposing patient records. Their equations and parameters are software assumptions, not validated biological models or population estimates.

### Intended Use
- Methodological validation: parameter recovery, identifiability, and simulation-based calibration (SBC).
- Algorithmic stress-testing: sensitivity to longitudinal visit sparsity, partial verification bias, and inter-laboratory analyzer calibration offsets.
- Cross-generator robustness testing (Study S9: train on G1+G2, test on G3).

---

## 2. Structural Composition of Generators
The laboratory comprises three structurally distinct mechanistic generators:

| Generator ID | Mathematical Structure | Biological Phenomenon | Noise & Observation Model |
|---|---|---|---|
| **G1 legacy profiles** | Sampled exponential growth passed through a saturation transform, assigned to a recurrence compartment; no ODE integration or marker clearance | Marker and organ-analyte increments are direct functions of current synthetic burden; chemotherapy affects selected lab values but not tumor growth | Gaussian intra-individual biological variation and a configured visit process |
| **G1 `balanced_synthetic_core_v4`** | Saturating synthetic burden with configured first-order marker secretion/clearance ODE propagated on a fixed time grid | Marker state follows `dC/dt = qB - kC`; coefficients are synthetic assumptions and not biologically estimated | Gaussian intra-individual biological variation and configured visit process |
| **G2 legacy profiles** | Samples a small fixed range of burst counts and times; persistent step burden plus a marker increment inside a fixed recent-burst window | Burst increments do not decay through a clearance model; not a Poisson jump-diffusion process | Gaussian intra-individual biological variation, profile-enabled facility offset/scale effects, and generator-specific missingness |
| **G2 `balanced_synthetic_core_v4`** | Homogeneous Poisson event process before recurrence, positive configured amplitudes, and exponential marker-clearance kernels | Events increase synthetic compartment burden and transiently contribute to markers; rate and amplitudes are uncalibrated | Patient-scoped event-time/amplitude streams, Gaussian intra-individual variation, facility effects, and configured missingness |
| **G3 (heavy-tailed noise stress process)** | Linear recurrence-signal ramp near a configured lead window; Student-t measurement noise and sampled pre-analytical error injection | In `balanced_synthetic_core_v3` and v4, signal saturates at its declared full-signal burden. Historical profiles retain the previous post-recurrence extrapolation for replay and that behavior is not endorsed. This is not an independent recurrence biology model | Facility offset/scale effects and informative missingness under the selected profile |

---

## 3. Synthetic Baseline Profiles (Not Population Estimates)
Population assumptions are stored in versioned JSON under `packages/vigil-sim/vigil_sim/config/` and are generated as synthetic stress-test inputs. They are not calibrated estimates for Nigeria or another population. The former Nigerian subtype and stage claims were removed because their evidence mapping did not support those derived distributions (`docs/EVIDENCE.md` E7/E12 downgrade notes).

- Default compatibility profile: `legacy_synthetic_v0`; retains the old assumed age, stage, subtype, recurrence, site, competing-event, and verification distributions for reproducibility. The former verification code defaults are now explicit in the JSON profile; this moves their source provenance into versioned configuration without changing the seeded generation behavior. The assumptions remain unsourced from clinical data and uncalibrated.
- `balanced_synthetic_v1`: equal stage, subtype, and recurrence-site probabilities and a bounded uniform age distribution. Its verification behavior is explicitly configured from the legacy source defaults, not from clinical imaging-policy evidence. This neutral profile is used by `EXP-CORE-ML-001` and is not intended to mimic case mix.
- `balanced_synthetic_core_v3`: explicitly declares facility effects, verification, assay missingness, baseline symptoms, financial friction, visit intervals, and the G1/G2/G3 mechanism values used by the source. The mechanism values are transcribed from legacy code, not literature-calibrated. They must not be used for model selection without a preregistered sensitivity study. Existing study profiles and outputs remain historical and unchanged. See ADR-0040.
- `balanced_synthetic_core_v4`: retains the explicit population/observation settings and replaces G1/G2's legacy marker equations with configured clearance ODE and Poisson shot-noise mechanisms. EXP-CORE-ML-011 passed its one-time synthetic mechanism checks (independent RK4 transition error, Poisson event counts and conditional event-time distribution). New kinetic coefficients remain uncalibrated stress assumptions; this result does not establish biology or prediction performance. Model-selection use requires separate preregistered sensitivity and calibration work.
- Financial-friction and visit-process values are simulator assumptions. They are not population-calibrated and must not be read as evidence about care access.
- Baseline symptom probabilities and latent-burden-to-grade mappings are explicit in each profile. Their values were migrated from prior source logic to preserve seeded behavior; they are synthetic stress assumptions and do not model clinical symptom prevalence, symptom measurement, or severity.
- Facility-effect count, offset spread, scale range, and assignment mode are explicit. Legacy/v1 preserve per-patient effects; core-v3/core-v4/K3 use shared facility/analyte effects. These settings are synthetic measurement-system stress assumptions, not estimates of real laboratory variation.

Legacy G1/G2 profiles do not meet the M13/ML Program specifications for marker clearance kinetics and stochastic shot noise. V4 implements these mathematical forms but does not establish biological validity. All results that depend on these generators are simulator-conditional stress results, not evidence from a validated mechanistic simulator. Historical outputs remain preserved and cannot be relabeled as v4 results. The simulator's current historical results are also not automatically reproducible from these profile files because implementation and censor-aware label contracts have changed. See ADR-0035 and the per-study status in the progress ledger.

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
