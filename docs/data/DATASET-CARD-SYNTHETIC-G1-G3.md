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
| **G1 (Smooth Kinetics)** | Compartmental differential equations with Gompertzian saturation | Steady, continuous biomarker shedding and first-order clearance kinetics | Gaussian intra-individual biological variation ($CV_i$) + routine surveillance schedule |
| **G2 (Burst Shedding)** | Stochastic jump-diffusion / Poisson shot-noise process | Episodic necrotic bursts, micro-metastatic shedding surges, and rapid progression | Mixed Gaussian-Poisson shedding + irregular visit intervals |
| **G3 (Heavy-Tailed Noise)** | Student-t ($\nu = 3$) error distribution with pre-analytical artifact injection | In vitro haemolysis (AST/LDH spikes), IV fluid dilution (25–40% drop), and analyzer offsets | Multi-facility analyzer bias ($\pm 12\%$) + informative MNAR missingness |

---

## 3. Synthetic Baseline Profiles (Not Population Estimates)
Population assumptions are stored in versioned JSON under `packages/vigil-sim/vigil_sim/config/` and are generated as synthetic stress-test inputs. They are not calibrated estimates for Nigeria or another population. The former Nigerian subtype and stage claims were removed because their evidence mapping did not support those derived distributions (`docs/EVIDENCE.md` E7/E12 downgrade notes).

- Default compatibility profile: `legacy_synthetic_v0`; retains the old assumed age, stage, subtype, recurrence, site, and competing-event distributions for reproducibility. It is explicitly marked as unsourced and not clinically calibrated.
- `balanced_synthetic_v1`: equal stage, subtype, and recurrence-site probabilities and a bounded uniform age distribution. This neutral profile is used by `EXP-CORE-ML-001` and is not intended to mimic case mix.
- Financial-friction and visit-process values remain simulator assumptions. They are not population-calibrated and must not be read as evidence about care access.

The simulator's current historical results are not automatically reproducible from these profile files because the implementation and censor-aware label contract have changed. See ADR-0035 and the per-study status in the progress ledger.

---

## 4. Ground-Truth Latent Exports and Verification Mechanism
Each generated patient trajectory records:
1. **Observable Data:** Standardized laboratory panels (CA 15-3, CEA, ALT, AST, ALP, GGT, Bilirubin, Creatinine, Calcium, WBC), symptom severity scores (Grade 0–4), and imaging flags.
2. **Latent Ground-Truth State (`LatentCompartmentState`):** Exact physical tumor cell burden in locoregional, bone, liver, lung, and brain compartments, true recurrence onset day, and true circulating marker concentrations.
3. **Partial Verification Mechanism (ML_PROGRAM §4.2):** Imaging is triggered selectively based on symptom severity and biomarker thresholds ($P(\text{Image} \mid \text{CA 15-3}, \text{Symptoms})$), faithfully reproducing clinical partial verification bias.

---

## 5. Ethical, Legal, and Integrity Guarantees
- **Zero Real Patient Data:** Synthesized entirely from differential equations and stochastic mathematical processes.
- **Anti-Leakage Protection:** Features extracted via `vigil-ml` never include future measurements, generator anomaly flags, or outcome labels.
- **Mandatory Synthetic Labeling:** Every exported dataset, report, and UI component carries explicit `[SYNTHETIC]` metadata badges.
