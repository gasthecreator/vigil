# Study M10: Missed-Signal Quality Audit Engine Evaluation

**Study Identifier:** M10
**Module:** M10 (Missed-Signal Quality Audit Engine)
**Pre-Registration:** [docs/studies/PREREG-M10.md](file:///docs/studies/PREREG-M10.md)
**Governance ADR:** [docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md](file:///docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md)
**Date:** 2026-10-17T19:10:00Z
**Execution Time:** 0.07s

---

## 1. Executive Summary & Quality Audit Overview

Vigil Module M10 provides retrospective surveillance quality auditing across cancer patient cohorts. All evaluations strictly observe the neutral descriptive register (*"signal present, action not recorded"*) and enforce a $k \ge 5$ small-cell suppression floor to prevent deductive re-identification under the Nigeria Data Protection Act (NDPA 2023).

### Cohort Alpha: Injected Ground Truth Results (N = 1003)
- **Total Surveillance Signals Detected:** 403
- **Action Recorded Within 30 Days:** 250
- **Signal Present, Action Not Recorded:** 153
- **Overall Unaddressed Signal Rate:** **37.97%** (95% Bootstrap CI: [33.25%, 42.93%])
- **Audit Engine Sensitivity:** **100.00%** (150/150 injected missed signals identified)
- **Audit Engine Specificity:** **100.00%** (600/600 stable controls correctly unflagged)

---

## 2. Privacy & Small-Cell Suppression Diagnostics ($k \ge 5$)

In compliance with ADR 0016, strata with $1 \le n < 5$ are masked as `"<5"` and associated rates are withheld:

| Stratum Type | Stratum Name | Total Signals | Action Not Recorded Count | Action Not Recorded Rate | Privacy Status |
|---|---|---|---|---|---|
| Subgroup | `urban_referral` | 212 | 84 | 39.62% | **REPORTED (n>=5)** |
| Subgroup | `rural_public` | 188 | 66 | 35.11% | **REPORTED (n>=5)** |
| Subgroup | `isolated_island_clinic` | <5 | <5 | — | **SUPPRESSED (<5)** |
| Subtype | `curative_tnbc` | 123 | 50 | 40.65% | **REPORTED (n>=5)** |
| Subtype | `adjuvant_post_mastectomy` | 135 | 49 | 36.30% | **REPORTED (n>=5)** |
| Subtype | `adjuvant_post_lumpectomy` | 142 | 51 | 35.92% | **REPORTED (n>=5)** |
| Subtype | `rare_inflammatory_carcinoma` | <5 | <5 | — | **SUPPRESSED (<5)** |
| Stage | `stage_3` | 126 | 45 | 35.71% | **REPORTED (n>=5)** |
| Stage | `stage_2` | 152 | 62 | 40.79% | **REPORTED (n>=5)** |
| Stage | `stage_1` | 122 | 43 | 35.25% | **REPORTED (n>=5)** |
| Stage | `stage_4_oligometastatic` | <5 | <5 | — | **SUPPRESSED (<5)** |

- **Suppressed Small Cells Count:** 3
- **Small-Cell Privacy Leaks ($1 \le n < 5$ exposed):** **0** (Zero tolerance).

---

## 3. Biological Noise & Non-Cancer Perturbation Stress (Cohort Beta)
- **Sample Size:** 500 null non-cancer trajectories with physiological biomarker variability (transient spikes, lab shifts).
- **False Positive Alarms:** 0
- **False Positive Rate:** **0.00%** ($\le 2.0\%$).

---

## 4. Pre-Registered Hypotheses Evaluation

### Hypothesis H1 (Ground Truth Recovery): SUPPORTED
- Observed Sensitivity: **100.00%** (Bound: $\ge 90.0\%$).
- Observed Specificity: **100.00%** (Bound: $\ge 95.0\%$).

### Hypothesis H2 (Small-Cell Privacy Guarantee): SUPPORTED
- Zero small cells leaked (0); small strata successfully masked (3 cells).

### Hypothesis H3 (Biological Noise Specificity): SUPPORTED
- Observed False Positive Rate: **0.00%** (Bound: $\le 2.0\%$).

---

## 5. Register & Tone Audit Certification
- **Neutral descriptive phrasing:** Verified (True).
- **Clinician identifiers present:** None (False).
- **Governing ADR:** [ADR 0016](file:///docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md).
