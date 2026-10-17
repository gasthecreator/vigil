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
    rr_ci_lower: float  # For SECONDARY evidence: lower 95% CI; for ASSUMPTION: lower bound of assumption range
    rr_ci_upper: float  # For SECONDARY evidence: upper 95% CI; for ASSUMPTION: upper bound of assumption range
    interruption_daily_penalty: float
    evidence_level: str  # "SECONDARY", "ASSUMPTION"
    evidence_citation: str
    grace_period_range: tuple[int, int] = (42, 70)
    ramp_end_range: tuple[int, int] = (70, 112)
    base_event_rate_range: tuple[float, float] = (0.03, 0.08)
    interruption_daily_penalty_range: tuple[float, float] = (0.005, 0.020)
    rr_assumption_range: Optional[tuple[float, float]] = None


# Parameter Registry: E8 is SECONDARY in EVIDENCE.md; unretrieved parameters are labeled ASSUMPTION with explicit ranges.
CONTEXT_REGISTRY: Dict[ClinicalContext, ContextHarmParameters] = {
    ClinicalContext.ADJUVANT_POST_LUMPECTOMY: ContextHarmParameters(
        context=ClinicalContext.ADJUVANT_POST_LUMPECTOMY,
        grace_period_days=56,  # 8 weeks
        ramp_end_days=84,  # 12 weeks
        base_event_rate=0.05,  # 5-year local recurrence baseline (~5%)
        rr_per_month=1.08,  # E8 meta-analysis (Mackillop et al., Clin Oncol 2016, n=79,600)
        rr_ci_lower=1.02,
        rr_ci_upper=1.14,
        interruption_daily_penalty=0.010,
        evidence_level="SECONDARY",
        evidence_citation="E8: Mackillop et al., Clin Oncol 2016 (SECONDARY: meta-analysis n=79,600; RR=1.08/mo, 95% CI 1.02-1.14)",
        grace_period_range=(42, 70),  # ASSUMPTION range: 6-10 weeks
        ramp_end_range=(70, 112),  # ASSUMPTION range: 10-16 weeks
        base_event_rate_range=(0.03, 0.08),  # ASSUMPTION range
        interruption_daily_penalty_range=(0.005, 0.020),  # ASSUMPTION range
        rr_assumption_range=None,  # Empirical 95% CI 1.02-1.14 from E8
    ),
    ClinicalContext.ADJUVANT_POST_MASTECTOMY: ContextHarmParameters(
        context=ClinicalContext.ADJUVANT_POST_MASTECTOMY,
        grace_period_days=56,  # 8 weeks
        ramp_end_days=84,  # 12 weeks
        base_event_rate=0.10,  # 5-year chest wall recurrence baseline (~10%)
        rr_per_month=1.10,
        rr_ci_lower=1.03,
        rr_ci_upper=1.18,
        interruption_daily_penalty=0.015,
        evidence_level="ASSUMPTION",
        evidence_citation="ASSUMPTION: Extrapolated from retrospective PMRT cohorts (assumption range: RR 1.03-1.18/mo)",
        grace_period_range=(42, 70),
        ramp_end_range=(70, 112),
        base_event_rate_range=(0.06, 0.15),
        interruption_daily_penalty_range=(0.008, 0.030),
        rr_assumption_range=(1.03, 1.18),
    ),
    ClinicalContext.CURATIVE_TNBC: ContextHarmParameters(
        context=ClinicalContext.CURATIVE_TNBC,
        grace_period_days=42,  # 6 weeks (shorter window due to rapid proliferation)
        ramp_end_days=70,  # 10 weeks
        base_event_rate=0.15,  # Higher recurrence hazard
        rr_per_month=1.15,
        rr_ci_lower=1.05,
        rr_ci_upper=1.28,
        interruption_daily_penalty=0.025,
        evidence_level="ASSUMPTION",
        evidence_citation="ASSUMPTION: Accelerated clonogen repopulation in high-grade TNBC (assumption range: RR 1.05-1.28/mo)",
        grace_period_range=(28, 56),
        ramp_end_range=(56, 84),
        base_event_rate_range=(0.10, 0.22),
        interruption_daily_penalty_range=(0.015, 0.040),
        rr_assumption_range=(1.05, 1.28),
    ),
    ClinicalContext.PALLIATIVE_BONE_BRAIN: ContextHarmParameters(
        context=ClinicalContext.PALLIATIVE_BONE_BRAIN,
        grace_period_days=0,  # Zero grace period: immediate pain and neurologic compression risk
        ramp_end_days=14,  # Rapid escalation window
        base_event_rate=0.20,  # High acute complication risk
        rr_per_month=1.30,
        rr_ci_lower=1.15,
        rr_ci_upper=1.50,
        interruption_daily_penalty=0.040,
        evidence_level="ASSUMPTION",
        evidence_citation="ASSUMPTION: Acute pain/neurological progression rate without radiotherapy (assumption range: RR 1.15-1.50/mo)",
        grace_period_range=(0, 7),
        ramp_end_range=(7, 21),
        base_event_rate_range=(0.12, 0.30),
        interruption_daily_penalty_range=(0.020, 0.060),
        rr_assumption_range=(1.15, 1.50),
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
                "rr_bounds": [rr_low, rr_high],
                "rr_bounds_type": (
                    "empirical_95ci"
                    if params.evidence_level == "SECONDARY"
                    else "assumption_range"
                ),
                "is_assumption": (params.evidence_level == "ASSUMPTION"),
                "parameter_assumption_ranges": {
                    "grace_period_days": list(params.grace_period_range),
                    "ramp_end_days": list(params.ramp_end_range),
                    "base_event_rate": list(params.base_event_rate_range),
                    "interruption_daily_penalty": list(params.interruption_daily_penalty_range),
                    "rr_per_month": (
                        list(params.rr_assumption_range)
                        if params.rr_assumption_range is not None
                        else None
                    ),
                },
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

    def _compute_with_override(
        self,
        params: ContextHarmParameters,
        delay_days: int,
        interruption_days: int = 0,
        **overrides,
    ) -> float:
        """Helper to recompute total harm under perturbed parameter values."""
        eff_params = ContextHarmParameters(
            context=params.context,
            grace_period_days=overrides.get("grace_period_days", params.grace_period_days),
            ramp_end_days=overrides.get("ramp_end_days", params.ramp_end_days),
            base_event_rate=overrides.get("base_event_rate", params.base_event_rate),
            rr_per_month=overrides.get("rr_per_month", params.rr_per_month),
            rr_ci_lower=overrides.get("rr_ci_lower", params.rr_ci_lower),
            rr_ci_upper=overrides.get("rr_ci_upper", params.rr_ci_upper),
            interruption_daily_penalty=overrides.get(
                "interruption_daily_penalty", params.interruption_daily_penalty
            ),
            evidence_level=params.evidence_level,
            evidence_citation=params.evidence_citation,
            grace_period_range=params.grace_period_range,
            ramp_end_range=params.ramp_end_range,
            base_event_rate_range=params.base_event_rate_range,
            interruption_daily_penalty_range=params.interruption_daily_penalty_range,
            rr_assumption_range=params.rr_assumption_range,
        )
        eff_delay = max(0, int(delay_days))
        eff_interruption = max(0, int(interruption_days))
        excess = self._compute_piecewise_delay_multiplier(
            eff_delay, eff_params, eff_params.rr_per_month
        )
        delay_harm = eff_params.base_event_rate * excess
        unplanned_gap_days = max(0, eff_interruption - 2)
        interruption_harm = unplanned_gap_days * eff_params.interruption_daily_penalty
        return round(min(1.0, max(0.0, delay_harm + interruption_harm)), 5)

    def parameter_sensitivity_analysis(
        self,
        clinical_context: str,
        delay_days: int,
        interruption_days: int = 0,
    ) -> Dict[str, Any]:
        """Multi-parameter sensitivity analysis sweeping over grace, ramp, base rate, penalty, and RR ranges."""
        params = self.get_parameters(clinical_context)
        baseline = self.compute_harm(clinical_context, delay_days, interruption_days)

        # 1. Grace period sweep
        g_min, g_max = params.grace_period_range
        harm_g_min = self._compute_with_override(
            params, delay_days, interruption_days, grace_period_days=g_min
        )
        harm_g_max = self._compute_with_override(
            params, delay_days, interruption_days, grace_period_days=g_max
        )

        # 2. Ramp end sweep
        r_min, r_max = params.ramp_end_range
        harm_r_min = self._compute_with_override(
            params, delay_days, interruption_days, ramp_end_days=r_min
        )
        harm_r_max = self._compute_with_override(
            params, delay_days, interruption_days, ramp_end_days=r_max
        )

        # 3. Base event rate sweep
        b_min, b_max = params.base_event_rate_range
        harm_b_min = self._compute_with_override(
            params, delay_days, interruption_days, base_event_rate=b_min
        )
        harm_b_max = self._compute_with_override(
            params, delay_days, interruption_days, base_event_rate=b_max
        )

        # 4. Interruption penalty sweep
        p_min, p_max = params.interruption_daily_penalty_range
        harm_p_min = self._compute_with_override(
            params, delay_days, interruption_days, interruption_daily_penalty=p_min
        )
        harm_p_max = self._compute_with_override(
            params, delay_days, interruption_days, interruption_daily_penalty=p_max
        )

        return {
            "clinical_context": params.context.value,
            "evidence_level": params.evidence_level,
            "delay_days": delay_days,
            "interruption_days": interruption_days,
            "baseline_expected_harm": baseline.expected_harm,
            "grace_period_sweep": {
                "min": g_min,
                "max": g_max,
                "harm_at_min": harm_g_min,
                "harm_at_max": harm_g_max,
            },
            "ramp_end_sweep": {
                "min": r_min,
                "max": r_max,
                "harm_at_min": harm_r_min,
                "harm_at_max": harm_r_max,
            },
            "base_rate_sweep": {
                "min": b_min,
                "max": b_max,
                "harm_at_min": harm_b_min,
                "harm_at_max": harm_b_max,
            },
            "interruption_penalty_sweep": {
                "min": p_min,
                "max": p_max,
                "harm_at_min": harm_p_min,
                "harm_at_max": harm_p_max,
            },
            "rr_bounds": {
                "min": params.rr_ci_lower,
                "max": params.rr_ci_upper,
                "harm_at_min": baseline.harm_min,
                "harm_at_max": baseline.harm_max,
            },
        }

    def evaluate_ranking_stability(
        self,
        cohort: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluates pairwise ranking consistency of patients under baseline vs perturbed parameter settings."""
        if len(cohort) < 2:
            return {"spearman_correlation": 1.0, "concordant_pairs_fraction": 1.0}

        def rank_cohort(model_evaluator) -> List[str]:
            scored = [(p["id"], model_evaluator(p)) for p in cohort]
            scored.sort(key=lambda item: -item[1])
            return [item[0] for item in scored]

        baseline_ranking = rank_cohort(
            lambda p: self.marginal_harm(p["clinical_context"], p.get("delay_days", 0), 1)
        )

        def perturbed_evaluator(p):
            ctx_params = self.get_parameters(p["clinical_context"])
            h1 = self._compute_with_override(
                ctx_params,
                p.get("delay_days", 0),
                0,
                base_event_rate=ctx_params.base_event_rate_range[1],
                rr_per_month=ctx_params.rr_ci_upper,
            )
            h2 = self._compute_with_override(
                ctx_params,
                p.get("delay_days", 0) + 1,
                0,
                base_event_rate=ctx_params.base_event_rate_range[1],
                rr_per_month=ctx_params.rr_ci_upper,
            )
            return max(0.0, h2 - h1)

        perturbed_ranking = rank_cohort(perturbed_evaluator)

        n = len(cohort)
        base_pos = {pid: i for i, pid in enumerate(baseline_ranking)}
        pert_pos = {pid: i for i, pid in enumerate(perturbed_ranking)}

        d_sq = sum((base_pos[pid] - pert_pos[pid]) ** 2 for pid in base_pos)
        spearman = 1.0 - (6.0 * d_sq) / (n * (n**2 - 1)) if n > 1 else 1.0

        concordant = 0
        total_pairs = 0
        pids = list(base_pos.keys())
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                total_pairs += 1
                b_diff = base_pos[pids[i]] - base_pos[pids[j]]
                p_diff = pert_pos[pids[i]] - pert_pos[pids[j]]
                if (b_diff * p_diff) > 0:
                    concordant += 1

        concordance_rate = (concordant / total_pairs) if total_pairs > 0 else 1.0

        return {
            "n_patients": n,
            "spearman_correlation": round(float(spearman), 4),
            "concordant_pairs_fraction": round(float(concordance_rate), 4),
            "baseline_order": baseline_ranking,
            "perturbed_order": perturbed_ranking,
        }
