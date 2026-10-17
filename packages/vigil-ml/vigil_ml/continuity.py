"""Treatment Continuity Harm Model (M7).

Quantifies expected clinical harm of radiotherapy delay and unplanned treatment interruption
across distinct breast cancer clinical contexts. Grounded in Master Plan §6.7 (M7) and
evidence register E8 (Mackillop et al. 2016 meta-analysis).

Supported Contexts:
1. adjuvant_post_lumpectomy: Adjuvant radiation following breast-conserving surgery (E8).
2. adjuvant_post_mastectomy: Post-mastectomy radiation therapy (PMRT).
3. curative_tnbc: Curative intent triple-negative breast cancer with accelerated clonogen repopulation.
4. palliative_bone_brain: Palliative radiation for bone metastases or brain metastases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ClinicalContext(str, Enum):
    ADJUVANT_POST_LUMPECTOMY = "adjuvant_post_lumpectomy"
    ADJUVANT_POST_MASTECTOMY = "adjuvant_post_mastectomy"
    CURATIVE_TNBC = "curative_tnbc"
    PALLIATIVE_BONE_BRAIN = "palliative_bone_brain"


@dataclass(frozen=True)
class ContextHarmParameters:
    context: ClinicalContext
    grace_period_days: int
    ramp_end_days: int
    base_event_rate: float
    rr_per_month: float
    rr_ci_lower: float
    rr_ci_upper: float
    interruption_daily_penalty: float
    evidence_level: str  # "HIGH", "MODERATE", "ASSUMPTION"
    evidence_citation: str


# Parameter Registry: Grounded in E8; unretrieved literature parameters are labeled ASSUMPTION.
CONTEXT_REGISTRY: Dict[ClinicalContext, ContextHarmParameters] = {
    ClinicalContext.ADJUVANT_POST_LUMPECTOMY: ContextHarmParameters(
        context=ClinicalContext.ADJUVANT_POST_LUMPECTOMY,
        grace_period_days=56,  # 8 weeks
        ramp_end_days=84,  # 12 weeks
        base_event_rate=0.05,  # 5-year local recurrence baseline (~5%)
        rr_per_month=1.08,  # E8: Mackillop et al. 2016 (n=79,600)
        rr_ci_lower=1.02,
        rr_ci_upper=1.14,
        interruption_daily_penalty=0.010,
        evidence_level="HIGH",
        evidence_citation="E8: Mackillop et al., Clin Oncol 2016 (n=79,600; RR=1.08/mo, 95% CI 1.02-1.14)",
    ),
    ClinicalContext.ADJUVANT_POST_MASTECTOMY: ContextHarmParameters(
        context=ClinicalContext.ADJUVANT_POST_MASTECTOMY,
        grace_period_days=56,  # 8 weeks
        ramp_end_days=84,  # 12 weeks
        base_event_rate=0.10,  # 5-year chest wall recurrence baseline (~10%)
        rr_per_month=1.10,  # Extrapolated from retrospective PMRT cohorts
        rr_ci_lower=1.03,
        rr_ci_upper=1.18,
        interruption_daily_penalty=0.015,
        evidence_level="ASSUMPTION",
        evidence_citation="ASSUMPTION: Extrapolated from retrospective PMRT cohorts (RR=1.10/mo, 95% CI 1.03-1.18)",
    ),
    ClinicalContext.CURATIVE_TNBC: ContextHarmParameters(
        context=ClinicalContext.CURATIVE_TNBC,
        grace_period_days=42,  # 6 weeks (shorter window due to rapid proliferation)
        ramp_end_days=70,  # 10 weeks
        base_event_rate=0.15,  # Higher recurrence hazard
        rr_per_month=1.15,  # Fast doubling time / high Ki-67 index
        rr_ci_lower=1.05,
        rr_ci_upper=1.28,
        interruption_daily_penalty=0.025,  # Significant accelerated repopulation penalty
        evidence_level="ASSUMPTION",
        evidence_citation="ASSUMPTION: Accelerated clonogen repopulation in high-grade TNBC (RR=1.15/mo, 95% CI 1.05-1.28)",
    ),
    ClinicalContext.PALLIATIVE_BONE_BRAIN: ContextHarmParameters(
        context=ClinicalContext.PALLIATIVE_BONE_BRAIN,
        grace_period_days=0,  # Zero grace period: immediate pain and neurologic compression risk
        ramp_end_days=14,  # Rapid escalation window
        base_event_rate=0.20,  # High acute complication risk
        rr_per_month=1.30,  # Weekly progressive impairment rate
        rr_ci_lower=1.15,
        rr_ci_upper=1.50,
        interruption_daily_penalty=0.040,  # Daily symptom escalation
        evidence_level="ASSUMPTION",
        evidence_citation="ASSUMPTION: Acute pain/neurological progression rate without radiotherapy (RR=1.30/mo)",
    ),
}


@dataclass
class HarmEstimate:
    clinical_context: str
    delay_days: int
    interruption_days: int
    expected_harm: float
    harm_min: float
    harm_max: float
    delay_harm: float
    interruption_harm: float
    grace_period_days: int
    in_grace_period: bool
    evidence_level: str
    evidence_citation: str
    details: Dict[str, Any] = field(default_factory=dict)


class ContinuityHarmModel:
    """Continuity Harm Model calculating piecewise expected excess harm from delays and breaks."""

    def __init__(
        self, custom_registry: Optional[Dict[ClinicalContext, ContextHarmParameters]] = None
    ):
        self.registry = custom_registry or CONTEXT_REGISTRY

    def get_parameters(self, context_str: str) -> ContextHarmParameters:
        try:
            ctx = ClinicalContext(context_str.strip().lower())
            return self.registry[ctx]
        except (ValueError, KeyError):
            # Fallback to standard adjuvant post-lumpectomy parameters
            return self.registry[ClinicalContext.ADJUVANT_POST_LUMPECTOMY]

    def _compute_piecewise_delay_multiplier(
        self, delay_days: int, params: ContextHarmParameters, rr: float
    ) -> float:
        """Computes excess relative risk factor based on piecewise delay curve.

        Piecewise formulation:
        - If delay_days <= grace_period_days: 0.0 excess harm (baseline window).
        - If grace_period_days < delay_days <= ramp_end_days:
            Linear interpolation between 0.0 and full excess rate at ramp_end.
        - If delay_days > ramp_end_days:
            Continuous exponential / compound growth per month beyond grace period.
        """
        if delay_days <= params.grace_period_days:
            return 0.0

        excess_days = delay_days - params.grace_period_days
        ramp_span = max(1, params.ramp_end_days - params.grace_period_days)

        if delay_days <= params.ramp_end_days:
            fraction_of_ramp = excess_days / ramp_span
            monthly_rate = rr - 1.0
            # Scaled excess at the ramp end point
            excess_at_ramp_end = monthly_rate * (ramp_span / 30.0)
            return fraction_of_ramp * excess_at_ramp_end
        else:
            # Beyond ramp: compound excess delay months
            excess_months = excess_days / 30.0
            # Excess hazard = (rr ^ excess_months) - 1.0
            return float((rr**excess_months) - 1.0)

    def compute_harm(
        self,
        clinical_context: str,
        delay_days: int,
        interruption_days: int = 0,
        custom_rr: Optional[float] = None,
    ) -> HarmEstimate:
        """Computes point estimate and uncertainty bounds for treatment delay and interruption."""
        params = self.get_parameters(clinical_context)
        eff_delay = max(0, int(delay_days))
        eff_interruption = max(0, int(interruption_days))

        rr_point = custom_rr if custom_rr is not None else params.rr_per_month
        rr_low = params.rr_ci_lower
        rr_high = params.rr_ci_upper

        # 1. Delay harm
        excess_point = self._compute_piecewise_delay_multiplier(eff_delay, params, rr_point)
        excess_low = self._compute_piecewise_delay_multiplier(eff_delay, params, rr_low)
        excess_high = self._compute_piecewise_delay_multiplier(eff_delay, params, rr_high)

        delay_harm_point = params.base_event_rate * excess_point
        delay_harm_min = params.base_event_rate * excess_low
        delay_harm_max = params.base_event_rate * excess_high

        # 2. Interruption harm (unplanned treatment gap during course)
        # Normal weekend gap (2 days) is standard; excess days penalize clonogen repopulation
        unplanned_gap_days = max(0, eff_interruption - 2)
        interruption_harm = unplanned_gap_days * params.interruption_daily_penalty

        total_harm_point = delay_harm_point + interruption_harm
        total_harm_min = delay_harm_min + interruption_harm
        total_harm_max = delay_harm_max + interruption_harm

        # Bounded within [0.0, 1.0] probability scale
        return HarmEstimate(
            clinical_context=params.context.value,
            delay_days=eff_delay,
            interruption_days=eff_interruption,
            expected_harm=round(min(1.0, total_harm_point), 5),
            harm_min=round(min(1.0, total_harm_min), 5),
            harm_max=round(min(1.0, total_harm_max), 5),
            delay_harm=round(min(1.0, delay_harm_point), 5),
            interruption_harm=round(min(1.0, interruption_harm), 5),
            grace_period_days=params.grace_period_days,
            in_grace_period=(eff_delay <= params.grace_period_days),
            evidence_level=params.evidence_level,
            evidence_citation=params.evidence_citation,
            details={
                "base_event_rate": params.base_event_rate,
                "rr_per_month": rr_point,
                "rr_95ci": [rr_low, rr_high],
                "unplanned_gap_days": unplanned_gap_days,
            },
        )

    def marginal_harm(
        self, clinical_context: str, current_delay: int, additional_delay: int = 1
    ) -> float:
        """Returns the incremental expected harm incurred by delaying by additional_delay days."""
        h1 = self.compute_harm(clinical_context, current_delay).expected_harm
        h2 = self.compute_harm(clinical_context, current_delay + additional_delay).expected_harm
        return max(0.0, round(h2 - h1, 6))

    def sensitivity_analysis(
        self,
        clinical_context: str,
        delay_days: int,
        rr_sweep: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Performs sensitivity sweep over hazard ratio / relative risk values."""
        params = self.get_parameters(clinical_context)
        sweep = rr_sweep or [1.02, 1.05, 1.08, 1.10, 1.15, 1.20, 1.25, 1.30]

        results = []
        for rr in sweep:
            est = self.compute_harm(clinical_context, delay_days, custom_rr=rr)
            results.append(
                {
                    "rr": rr,
                    "delay_days": delay_days,
                    "expected_harm": est.expected_harm,
                    "excess_multiplier": round(
                        self._compute_piecewise_delay_multiplier(delay_days, params, rr), 4
                    ),
                }
            )
        return results
