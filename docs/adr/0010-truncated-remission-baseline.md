---
status: accepted
date: 2026-10-17
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0010. Truncated Remission Baseline for Adjuvant Surveillance Cohorts in `vigil-sim`

## Context and Problem Statement
Vigil is designed for post-surgical adjuvant monitoring of breast cancer patients who have completed definitive primary treatment (surgery, adjuvant chemotherapy, and radiation) and are undergoing routine longitudinal surveillance for recurrence.

By definition, patients entering an adjuvant surveillance cohort must be in clinical and biochemical remission—exhibiting No Evidence of Disease (NED) at the baseline of post-treatment monitoring (Molina et al. 1995, PMID 7600742).

In unselected general populations, inter-individual biological variation ($\text{CV}_g$) for serum CA 15-3 is reported at $62.9\%$ ($\sigma_g \approx 0.63$, Westgard compilation of Ricós 1999; Evidence E9). If a synthetic cohort generator samples patient baseline analyte levels from an unconditioned log-normal distribution with $\sigma_g = 0.629$ and standard reference midpoints:
$$\log y_0 \sim \mathcal{N}\left(\log \mu_{\text{ref}} - \frac{1}{2}\sigma_g^2, \sigma_g^2\right)$$
over 8–10% of disease-free patients are sampled with day-0 baseline CA 15-3 concentrations exceeding the landmark clinical cutoff of 30.0 U/mL.

This creates an artificial simulator artifact where patients entering "remission monitoring" immediately trigger recurrence alarms before tumor regrowth has occurred, collapsing observation-level specificity in remission to ~90–92%. In contrast, empirical clinical data in postoperative NED cohorts demonstrate that false-positive elevations above 30 U/mL occur in less than 1.5% of visits (observation-level specificity $\ge 98.5\%$; Molina et al. 1995, Evidence E1).

## Decision Drivers
1. **Clinical Fidelity to Adjuvant Remission:** A surveillance cohort simulator must reflect patients who achieved post-surgical remission; patients with active, un-resected gross disease (>30 U/mL) do not enter adjuvant remission surveillance.
2. **Calibration Integrity (Evidence E1):** Observation specificity in remission must match published landmark findings ($\ge 98\%$ per-observation specificity in NED).
3. **Transparency and Governance:** Any modification to shared simulation kinetics must be explicitly governed by an architectural decision record, disclosed in pull requests, and reflected in updated downstream study benchmarks and synthetic data manifests.

## Considered Options
- **Option 1: Unconditioned General Population $\sigma_g$ ($0.629$)**  
  *Pros:* Directly uses the raw table value from Ricós 1999.  
  *Cons:* Grossly distorts adjuvant surveillance cohorts; yields ~10% false-positive rate on day 0 in disease-free patients; fails Molina 1995 calibration targets (`packages/vigil-sim/tests/test_calibration.py`).
- **Option 2: Rejection Sampling on Adjuvant Eligibility**  
  *Pros:* Retains the shape of the upper tail up to 30 U/mL.  
  *Cons:* Slow generation loops; creates an abrupt cliff at the reference high without physical justification.
- **Option 3: Conditioned Remission Distribution with Truncation (Selected)**  
  *Pros:*
  - Caps between-subject dispersion for disease-free remission at $\sigma_{g,\text{NED}} \le 0.22$, matching empirical dispersion in postoperative disease-free cohorts (Molina et al. 1995).
  - Enforces an upper baseline clamp at $0.95 \times \text{reference\_high}$ ($28.5$ U/mL for CA 15-3), ensuring all cohort entrants meet biochemical NED inclusion criteria.
  - Reproduces published observation specificity ($\ge 98\%$) and conditional lead times ($126 \pm 69$ days).
  - Hermetic and deterministic across all seeds and generators.

## Decision Outcome
Chosen option: **Option 3: Conditioned Remission Distribution with Truncation**.

### Specification in `vigil_sim.generators.BaseCohortGenerator`:
```python
# Baseline analyte levels conditioned to the disease-free remission distribution (NED)
base_levels: Dict[str, float] = {}
for code, analyte in ANALYTE_REGISTRY.items():
    ref_mid = 0.5 * (analyte.plausibility.reference_low + analyte.plausibility.reference_high)
    sigma_g = min(0.22, analyte.biological_variation.cv_g / 100.0)
    val = ref_mid * math.exp(float(self.rng.normal(-0.5 * sigma_g**2, sigma_g)))
    base_levels[code] = max(
        analyte.plausibility.reference_low * 0.8,
        min(analyte.plausibility.reference_high * 0.95, val),
    )
```

### Consequences and Downstream Artifact Governance:
1. `data/synthetic/` cohorts (`cohort_g1_smooth`, `cohort_g2_burst`, `cohort_g3_noise`) regenerated with updated sha256 checksums recorded in `data/synthetic/manifest.json`.
2. Downstream benchmarks and studies (S1, S3, S9, VigilBench, S2, S7, and K1 world test) re-executed on the updated generator baseline and their exact deltas documented in `docs/progress/PHASE-5B-REPORT.md`.
