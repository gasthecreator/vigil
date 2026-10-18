"""Unit and Property Tests for Treatment Continuity Harm Model (M7).

Verifies Master Plan §6.7, Evidence E8, and Condition P11-A/B:
1. Supported clinical contexts and evidence citations.
2. Piecewise delay threshold (8-week grace period, 8-12 week ramp).
3. Monotonicity and uncertainty interval ordering (harm_min <= harm <= harm_max).
4. Treatment interruption penalties for unplanned gaps.
5. Sensitivity analysis sweeps across hazard ratios.
"""

import pytest
from vigil_ml.continuity import (
    ClinicalContext,
    ContinuityHarmModel,
)


@pytest.fixture
def harm_model():
    return ContinuityHarmModel()


def test_supported_contexts_and_evidence_citations(harm_model):
    """Verifies that all 4 clinical contexts are supported with honest evidence labels."""
    # 1. Adjuvant post-lumpectomy (E8-backed, downgraded to SECONDARY per EVIDENCE.md)
    lump = harm_model.compute_harm(ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value, delay_days=60)
    assert lump.evidence_level == "SECONDARY"
    assert "E8" in lump.evidence_citation
    assert "Mackillop" in lump.evidence_citation
    assert lump.grace_period_days == 56
    assert lump.details["is_assumption"] is False
    assert lump.details["rr_bounds_type"] == "empirical_95ci"

    # 2. Adjuvant post-mastectomy (labeled ASSUMPTION)
    pmrt = harm_model.compute_harm(ClinicalContext.ADJUVANT_POST_MASTECTOMY.value, delay_days=60)
    assert lump.evidence_level != pmrt.evidence_level
    assert pmrt.evidence_level == "ASSUMPTION"
    assert "ASSUMPTION" in pmrt.evidence_citation
    assert pmrt.details["is_assumption"] is True
    assert pmrt.details["rr_bounds_type"] == "assumption_range"
    assert pmrt.details["parameter_assumption_ranges"]["base_event_rate"] == [0.06, 0.15]

    # 3. Curative TNBC (accelerated proliferation, labeled ASSUMPTION)
    tnbc = harm_model.compute_harm(ClinicalContext.CURATIVE_TNBC.value, delay_days=50)
    assert tnbc.evidence_level == "ASSUMPTION"
    assert tnbc.grace_period_days == 42  # 6 weeks
    assert tnbc.details["parameter_assumption_ranges"]["grace_period_days"] == [28, 56]

    # 4. Palliative bone/brain (zero grace period, acute complication)
    pal = harm_model.compute_harm(ClinicalContext.PALLIATIVE_BONE_BRAIN.value, delay_days=5)
    assert pal.evidence_level == "ASSUMPTION"
    assert pal.grace_period_days == 0
    assert not pal.in_grace_period
    assert pal.expected_harm > 0.0
    assert pal.details["parameter_assumption_ranges"]["rr_per_month"] == [1.15, 1.50]


def test_multi_parameter_sensitivity_analysis(harm_model):
    """Verifies parameter_sensitivity_analysis sweeps across grace, ramp, base rate, and daily penalty."""
    res = harm_model.parameter_sensitivity_analysis(
        ClinicalContext.CURATIVE_TNBC.value, delay_days=55, interruption_days=4
    )
    assert res["clinical_context"] == "curative_tnbc"
    assert res["evidence_level"] == "ASSUMPTION"
    # Grace sweep: shorter grace (min) increases harm, longer grace (max) decreases harm
    assert res["grace_period_sweep"]["harm_at_min"] >= res["grace_period_sweep"]["harm_at_max"]
    # Base rate sweep: higher base rate increases harm
    assert res["base_rate_sweep"]["harm_at_max"] >= res["base_rate_sweep"]["harm_at_min"]
    # Interruption penalty sweep: higher penalty increases harm
    assert res["interruption_penalty_sweep"]["harm_at_max"] >= res["interruption_penalty_sweep"]["harm_at_min"]


def test_scheduler_ranking_stability(harm_model):
    """Verifies that patient triage ranking remains highly concordant under parameter perturbations."""
    cohort = [
        {"id": "P_PAL", "clinical_context": "palliative_bone_brain", "delay_days": 10},
        {"id": "P_TNBC", "clinical_context": "curative_tnbc", "delay_days": 60},
        {"id": "P_PMRT", "clinical_context": "adjuvant_post_mastectomy", "delay_days": 75},
        {"id": "P_LUMP", "clinical_context": "adjuvant_post_lumpectomy", "delay_days": 65},
    ]
    stability = harm_model.evaluate_ranking_stability(cohort)
    assert stability["spearman_correlation"] >= 0.80
    assert stability["concordant_pairs_fraction"] >= 0.80


def test_piecewise_delay_curve_lumpectomy(harm_model):
    """Verifies 8-week (56-day) grace period and 8-12 week ramp for post-lumpectomy radiation."""
    # Within grace period: 0 excess harm
    est_30d = harm_model.compute_harm(ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value, delay_days=30)
    assert est_30d.in_grace_period is True
    assert est_30d.delay_harm == 0.0
    assert est_30d.expected_harm == 0.0

    est_56d = harm_model.compute_harm(ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value, delay_days=56)
    assert est_56d.in_grace_period is True
    assert est_56d.delay_harm == 0.0

    # Within ramp (day 70)
    est_70d = harm_model.compute_harm(ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value, delay_days=70)
    assert est_70d.in_grace_period is False
    assert est_70d.delay_harm > 0.0

    # Past ramp (day 100)
    est_100d = harm_model.compute_harm(
        ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value, delay_days=100
    )
    assert est_100d.delay_harm > est_70d.delay_harm


def test_uncertainty_bounds_ordering(harm_model):
    """Verifies that harm_min <= expected_harm <= harm_max holds across all delays."""
    for ctx in ClinicalContext:
        for delay in [0, 14, 45, 60, 90, 150]:
            est = harm_model.compute_harm(ctx.value, delay_days=delay)
            assert est.harm_min <= est.expected_harm, f"harm_min > expected for {ctx} at {delay}d"
            assert est.expected_harm <= est.harm_max, f"expected > harm_max for {ctx} at {delay}d"
            assert 0.0 <= est.expected_harm <= 1.0


def test_interruption_penalty_for_unplanned_gaps(harm_model):
    """Verifies that routine 2-day weekend breaks incur 0 penalty, while unplanned breaks penalize clonogen repopulation."""
    # 2 days (weekend) -> 0 penalty
    weekend = harm_model.compute_harm(
        ClinicalContext.CURATIVE_TNBC.value, delay_days=30, interruption_days=2
    )
    assert weekend.interruption_harm == 0.0

    # 5 days (e.g. machine down Wed-Fri plus weekend) -> penalty for 3 unplanned days
    gap_5d = harm_model.compute_harm(
        ClinicalContext.CURATIVE_TNBC.value, delay_days=30, interruption_days=5
    )
    assert gap_5d.interruption_harm > 0.0
    assert gap_5d.expected_harm > weekend.expected_harm


def test_monotonicity_property(harm_model):
    """Property test: harm must be strictly non-decreasing with respect to delay."""
    for ctx in ClinicalContext:
        prev_harm = 0.0
        for d in range(0, 180, 5):
            curr_harm = harm_model.compute_harm(ctx.value, delay_days=d).expected_harm
            assert curr_harm >= prev_harm, (
                f"Non-monotone harm in {ctx} at day {d}: {curr_harm} < {prev_harm}"
            )
            prev_harm = curr_harm

            marginal = harm_model.marginal_harm(ctx.value, d, additional_delay=1)
            assert marginal >= 0.0


def test_sensitivity_analysis_monotonicity(harm_model):
    """Verifies sensitivity sweep over hazard ratios."""
    sweep = harm_model.sensitivity_analysis(
        ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value,
        delay_days=100,
        rr_sweep=[1.02, 1.05, 1.08, 1.14, 1.25],
    )
    assert len(sweep) == 5
    for i in range(len(sweep) - 1):
        assert sweep[i]["expected_harm"] <= sweep[i + 1]["expected_harm"]
