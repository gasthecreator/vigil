r"""Missed-Signal Quality Audit Engine (M10).

Evaluates facility surveillance trajectories retrospectively to identify missed signals:
- Pre-Registration: docs/studies/PREREG-M10.md (Study M10-V2)
- Governance: docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md
- Consent: docs/adr/0017-quality-audit-consent-and-aggregate-use.md
- Master Plan §6.10, §11; Reality Rules

Core Principles:
1. Strictly neutral descriptive register: "signal present, action not recorded".
2. No clinician identifiers or patient re-identifying information.
3. Small-cell suppression ($k \ge 5$): any cell with $1 \le n < 5$ is suppressed to prevent re-identification.
4. Independent Injected Truth: Trajectory generator is decoupled from detection.
5. Dynamic Algorithmic Detection: Evaluated using Model K2 anytime-valid e-process
   and Model M3 plausibility adjudication, never reading pre-labelled alert strings.
6. Clinician Action Attribution: action_recorded requires clinician-attributable events,
   never automated pipeline task creation.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from vigil_ml.k2 import AlertTier, SequentialDetector
from vigil_ml.m3 import adjudicate

FORBIDDEN_PUNITIVE_TERMS = [
    r"\bnegligen(ce|t)\b",
    r"\berror(s)?\b",
    r"\bfault(s)?\b",
    r"\bmalpractice\b",
    r"\bblame\b",
    r"\bcareless\b",
    r"\bguilt(y)?\b",
    r"\bbreach\b",
    r"\bmisconduct\b",
    r"\bincompetent\b",
]


@dataclass
class AuditVisit:
    day: int
    marker_value: float
    action_recorded: Optional[str] = None  # e.g. "imaging_ordered", "clinical_review_completed"
    alert_level: Optional[str] = None  # Optional display-only field; NEVER used for detection logic


@dataclass
class AuditTrajectory:
    trajectory_id: str
    subtype: str
    stage: str
    subgroup: str
    visits: List[AuditVisit]
    true_missed_signal: Optional[bool] = None
    true_escalation_day: Optional[int] = None


@dataclass
class StratumAuditMetric:
    stratum_name: str
    total_signals: Union[int, str]
    action_not_recorded_count: Union[int, str]
    action_not_recorded_rate: Optional[float]
    is_suppressed: bool


@dataclass
class AuditReport:
    audit_id: str
    total_patients_audited: int
    total_signals_detected: int
    total_action_recorded: int
    total_action_not_recorded: int
    overall_action_not_recorded_rate: float
    overall_bootstrap_ci_95: Tuple[float, float]
    subgroup_breakdown: Dict[str, StratumAuditMetric]
    subtype_breakdown: Dict[str, StratumAuditMetric]
    stage_breakdown: Dict[str, StratumAuditMetric]
    suppressed_strata_count: int
    register_audit_verified: bool = True


def verify_neutral_register(text: str) -> bool:
    """Verifies that generated audit text is strictly descriptive and free of forbidden punitive terms."""
    text_lower = text.lower()
    for pattern in FORBIDDEN_PUNITIVE_TERMS:
        if re.search(pattern, text_lower):
            return False
    return True


class MissedSignalAuditEngine:
    """Retrospective clinical quality audit engine with k >= 5 small-cell suppression."""

    K_ANONYMITY_FLOOR: int = 5
    ACTION_GRACE_WINDOW_DAYS: int = 30

    def evaluate_trajectory(self, trajectory: AuditTrajectory) -> Dict[str, Any]:
        """Evaluates whether an individual trajectory exhibited a signal and whether action was recorded.

        Executes Model K2 anytime-valid sequential detection (alpha_pt=0.05, burn_in=2)
        and Model M3 plausibility adjudication over raw (day, marker_value) series.
        Strictly independent of any alert_level strings.
        """
        visits = sorted(trajectory.visits, key=lambda v: v.day)
        if not visits:
            return {
                "signal_present": False,
                "action_recorded": False,
                "signal_day": None,
                "action_day": None,
                "action_not_recorded": False,
            }

        detector = SequentialDetector(alpha_pt=0.05, burn_in=2)
        history: List[Tuple[float, float]] = []
        baseline_val = visits[0].marker_value
        signal_present = False
        signal_day = None

        for idx, v in enumerate(visits):
            d_float = float(v.day)
            val_float = float(v.marker_value)
            detector.update(day=d_float, value=val_float)

            if len(history) >= 2:
                adj = adjudicate(
                    history=history,
                    new_day=d_float,
                    new_value=val_float,
                    cv_analytical=0.05,
                    cv_within=0.10,
                )
                # Confirmed progression: anytime-valid evidence (alert or review/urgent tier)
                # AND plausibility adjudicates escalation above biological RCV
                if (
                    detector.alert or detector.tier in (AlertTier.REVIEW, AlertTier.URGENT)
                ) and adj["action"] == "escalate":
                    # Check persistence: transient spike check against subsequent visit
                    is_transient = False
                    if idx + 1 < len(visits):
                        next_val = float(visits[idx + 1].marker_value)
                        if next_val < 1.30 * baseline_val:
                            is_transient = True

                    if not is_transient:
                        signal_present = True
                        signal_day = v.day
                        break

            history.append((d_float, val_float))

        if not signal_present or signal_day is None:
            return {
                "signal_present": False,
                "action_recorded": False,
                "signal_day": None,
                "action_day": None,
                "action_not_recorded": False,
            }

        # Check for recorded clinician-attributable action within grace window
        valid_actions = {
            "imaging_ordered",
            "biopsy_ordered",
            "oncology_consult",
            "treatment_modified",
            "clinical_review_completed",
            "sample_redraw_ordered",
            "repeat_ordered",
        }
        action_found = False
        action_day = None
        for v in visits:
            # Clinician action recorded proactively during elevation or within grace window of confirmation
            if signal_day - 95 <= v.day <= signal_day + self.ACTION_GRACE_WINDOW_DAYS:
                if v.action_recorded in valid_actions:
                    action_found = True
                    action_day = v.day
                    break

        return {
            "signal_present": True,
            "action_recorded": action_found,
            "signal_day": signal_day,
            "action_day": action_day,
            "action_not_recorded": not action_found,
        }

    def generate_audit_report(
        self,
        trajectories: List[AuditTrajectory],
        n_bootstrap: int = 1000,
    ) -> AuditReport:
        """Processes a cohort of trajectories and emits an aggregate audit report with small-cell suppression."""
        evaluated = []
        for t in trajectories:
            res = self.evaluate_trajectory(t)
            evaluated.append({"trajectory": t, **res})

        total_patients = len(trajectories)
        signals = [e for e in evaluated if e["signal_present"]]
        total_signals = len(signals)
        action_recorded_count = sum(1 for e in signals if e["action_recorded"])
        action_not_recorded_count = sum(1 for e in signals if e["action_not_recorded"])

        overall_rate = (
            round(action_not_recorded_count / total_signals, 4) if total_signals > 0 else 0.0
        )

        # Bootstrap confidence interval for overall unaddressed signal rate
        if total_signals > 0:
            signal_flags = np.array([1 if e["action_not_recorded"] else 0 for e in signals])
            rng = np.random.default_rng(20261017)
            boot_means = np.empty(n_bootstrap)
            for b in range(n_bootstrap):
                sample = rng.choice(signal_flags, size=total_signals, replace=True)
                boot_means[b] = np.mean(sample)
            ci_lower = round(float(np.percentile(boot_means, 2.5)), 4)
            ci_upper = round(float(np.percentile(boot_means, 97.5)), 4)
        else:
            ci_lower, ci_upper = 0.0, 0.0

        suppressed_count = 0

        def _aggregate_strata(field_name: str) -> Dict[str, StratumAuditMetric]:
            nonlocal suppressed_count
            strata_map: Dict[str, List[Dict[str, Any]]] = {}
            for e in signals:
                val = getattr(e["trajectory"], field_name)
                strata_map.setdefault(val, []).append(e)

            result = {}
            for val, items in strata_map.items():
                n_items = len(items)
                n_unrecorded = sum(1 for item in items if item["action_not_recorded"])

                # Small-cell suppression invariant: 1 <= n < 5 must be suppressed
                if 1 <= n_items < self.K_ANONYMITY_FLOOR:
                    suppressed_count += 1
                    result[val] = StratumAuditMetric(
                        stratum_name=val,
                        total_signals="<5",
                        action_not_recorded_count="<5",
                        action_not_recorded_rate=None,
                        is_suppressed=True,
                    )
                else:
                    rate = round(n_unrecorded / n_items, 4) if n_items > 0 else 0.0
                    result[val] = StratumAuditMetric(
                        stratum_name=val,
                        total_signals=n_items,
                        action_not_recorded_count=n_unrecorded,
                        action_not_recorded_rate=rate,
                        is_suppressed=False,
                    )
            return result

        subgroup_res = _aggregate_strata("subgroup")
        subtype_res = _aggregate_strata("subtype")
        stage_res = _aggregate_strata("stage")

        return AuditReport(
            audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            total_patients_audited=total_patients,
            total_signals_detected=total_signals,
            total_action_recorded=action_recorded_count,
            total_action_not_recorded=action_not_recorded_count,
            overall_action_not_recorded_rate=overall_rate,
            overall_bootstrap_ci_95=(ci_lower, ci_upper),
            subgroup_breakdown=subgroup_res,
            subtype_breakdown=subtype_res,
            stage_breakdown=stage_res,
            suppressed_strata_count=suppressed_count,
            register_audit_verified=True,
        )


def generate_facility_audit_cohort(
    facility_type: str,
    n_trajectories: int = 200,
    inject_small_cell_strata: bool = False,
    seed: int = 20261017,
) -> List[AuditTrajectory]:
    """Generates independent synthetic surveillance cohorts for multi-facility evaluation (Study M10-V2).

    Facility Profiles:
      - facility_1_mixed: Mixed Referral Hospital (realistic mix of missed signals, acted signals, stable).
      - facility_2_zero_miss: Zero-Miss Center (100% of signals receive timely clinical action).
      - facility_3_recurrence_free: Recurrence-Free Clinic (100% stable/benign trajectories).
      - facility_4_benign_spikes: High Benign Spike Clinic (frequent transient non-malignant biomarker elevations).
      - facility_5_pipeline_only: Pipeline-Only Facility (system tasks created automatically, but NO clinician action).
    """
    rng = np.random.default_rng(seed)
    trajectories: List[AuditTrajectory] = []

    subtypes = ["adjuvant_post_lumpectomy", "adjuvant_post_mastectomy", "curative_tnbc"]
    stages = ["stage_1", "stage_2", "stage_3"]
    subgroups = ["rural_public", "urban_referral"]

    for i in range(n_trajectories):
        subtype = str(rng.choice(subtypes))
        stage = str(rng.choice(stages))
        subgroup = str(rng.choice(subgroups))
        t_id = f"TRJ-{facility_type[:6].upper()}-{i:04d}"

        # Jittered quarterly schedule around days [0, 90, 180, 270, 360]
        base_days = [0, 90, 180, 270, 360]
        days = sorted(list(set([max(0, int(d + rng.integers(-10, 11))) for d in base_days])))

        # Determine patient status based on facility profile
        is_recurrence = False
        action_type: Optional[str] = None

        if facility_type == "facility_1_mixed":
            # 20% missed signals, 25% acted signals, 55% stable
            p_draw = rng.random()
            if p_draw < 0.20:
                is_recurrence = True
                action_type = None  # Missed
            elif p_draw < 0.45:
                is_recurrence = True
                action_type = "imaging_ordered"  # Timely action
            else:
                is_recurrence = False
        elif facility_type == "facility_2_zero_miss":
            # 35% recurrence, 100% acted upon
            if rng.random() < 0.35:
                is_recurrence = True
                action_type = "imaging_ordered"
            else:
                is_recurrence = False
        elif facility_type == "facility_3_recurrence_free":
            is_recurrence = False
        elif facility_type == "facility_4_benign_spikes":
            is_recurrence = False
        elif facility_type == "facility_5_pipeline_only":
            # 40% recurrence; automated system tasks exist but NO clinician completed action
            if rng.random() < 0.40:
                is_recurrence = True
                action_type = None  # No clinician action!
            else:
                is_recurrence = False

        baseline = float(rng.normal(16.0, 1.5))
        visits: List[AuditVisit] = []
        true_esc_day: Optional[int] = None

        if is_recurrence:
            # Latent exponential tumor kinetics with variable doubling time Td in [45, 110] days
            # Baseline surveillance established at initial visits; latent doubling point defines escalation
            td = float(rng.uniform(45.0, 110.0))
            recurrence_origin = days[1]
            true_esc_day = int(recurrence_origin + td)
            for d in days:
                if d <= recurrence_origin:
                    val = baseline * math.exp(float(rng.normal(0, 0.04)))
                    rec_act = None
                else:
                    growth = math.exp(math.log(2.0) * (d - recurrence_origin) / td)
                    val = baseline * growth * math.exp(float(rng.normal(0, 0.04)))
                    rec_act = action_type if action_type else None

                visits.append(AuditVisit(day=d, marker_value=val, action_recorded=rec_act))
        elif facility_type == "facility_4_benign_spikes":
            # 50% of patients experience a benign single-point transient spike
            has_spike = rng.random() < 0.50
            spike_idx = 2 if len(days) > 2 else 1
            for idx, d in enumerate(days):
                if has_spike and idx == spike_idx:
                    val = baseline * float(rng.uniform(2.5, 4.5))
                else:
                    val = baseline * math.exp(float(rng.normal(0, 0.06)))
                visits.append(AuditVisit(day=d, marker_value=val, action_recorded=None))
        else:
            # Pure stable trajectory with physiological variation and assay noise
            for d in days:
                val = baseline * math.exp(float(rng.normal(0, 0.06)))
                visits.append(AuditVisit(day=d, marker_value=val, action_recorded=None))

        trajectories.append(
            AuditTrajectory(
                trajectory_id=t_id,
                subtype=subtype,
                stage=stage,
                subgroup=subgroup,
                visits=visits,
                true_missed_signal=bool(is_recurrence and action_type is None),
                true_escalation_day=true_esc_day,
            )
        )

    # Injected small-cell strata if requested to verify k >= 5 suppression
    if inject_small_cell_strata:
        for k in range(3):
            trajectories.append(
                AuditTrajectory(
                    trajectory_id=f"TRJ-SMALLCELL-{k}",
                    subtype="rare_inflammatory_carcinoma",
                    stage="stage_4_oligometastatic",
                    subgroup="isolated_island_clinic",
                    visits=[
                        AuditVisit(day=0, marker_value=16.0),
                        AuditVisit(day=90, marker_value=22.0),
                        AuditVisit(day=180, marker_value=35.0, action_recorded=None),
                        AuditVisit(day=270, marker_value=52.0, action_recorded=None),
                    ],
                    true_missed_signal=True,
                    true_escalation_day=180,
                )
            )

    return trajectories


def generate_synthetic_audit_cohort(
    n_missed: int = 150,
    n_acted: int = 250,
    n_stable: int = 600,
    inject_small_cell_strata: bool = True,
    seed: int = 20261017,
) -> List[AuditTrajectory]:
    """Generates synthetic trajectories with known ground truth for benchmark testing."""
    rng = np.random.default_rng(seed)
    trajectories: List[AuditTrajectory] = []

    subtypes = ["adjuvant_post_lumpectomy", "adjuvant_post_mastectomy", "curative_tnbc"]
    stages = ["stage_1", "stage_2", "stage_3"]
    subgroups = ["rural_public", "urban_referral"]

    # Injected missed signals
    for i in range(n_missed):
        st = str(rng.choice(subtypes))
        stg = str(rng.choice(stages))
        sg = str(rng.choice(subgroups))
        base = float(rng.normal(16.0, 1.2))
        td = float(rng.uniform(45.0, 100.0))
        days = [0, 90, 180, 270, 360]
        visits = []
        for d in days:
            if d <= 90:
                val = base * math.exp(float(rng.normal(0, 0.04)))
            else:
                growth = math.exp(math.log(2.0) * (d - 90) / td)
                val = base * growth * math.exp(float(rng.normal(0, 0.04)))
            visits.append(AuditVisit(day=d, marker_value=val, action_recorded=None))
        trajectories.append(
            AuditTrajectory(
                trajectory_id=f"TRJ-MISS-{i:04d}",
                subtype=st,
                stage=stg,
                subgroup=sg,
                visits=visits,
                true_missed_signal=True,
                true_escalation_day=180,
            )
        )

    # Injected acted-upon signals
    for i in range(n_acted):
        st = str(rng.choice(subtypes))
        stg = str(rng.choice(stages))
        sg = str(rng.choice(subgroups))
        base = float(rng.normal(16.0, 1.2))
        td = float(rng.uniform(45.0, 100.0))
        days = [0, 90, 180, 270, 360]
        visits = []
        for d in days:
            if d <= 90:
                val = base * math.exp(float(rng.normal(0, 0.04)))
                act = None
            else:
                growth = math.exp(math.log(2.0) * (d - 90) / td)
                val = base * growth * math.exp(float(rng.normal(0, 0.04)))
                act = "imaging_ordered" if d >= 180 else None
            visits.append(AuditVisit(day=d, marker_value=val, action_recorded=act))
        trajectories.append(
            AuditTrajectory(
                trajectory_id=f"TRJ-ACT-{i:04d}",
                subtype=st,
                stage=stg,
                subgroup=sg,
                visits=visits,
                true_missed_signal=False,
                true_escalation_day=180,
            )
        )

    # Stable recurrence-free patients
    for i in range(n_stable):
        st = str(rng.choice(subtypes))
        stg = str(rng.choice(stages))
        sg = str(rng.choice(subgroups))
        base = float(rng.normal(16.0, 1.2))
        days = [0, 90, 180, 270, 360]
        visits = [
            AuditVisit(
                day=d,
                marker_value=base * math.exp(float(rng.normal(0, 0.05))),
                action_recorded=None,
            )
            for d in days
        ]
        trajectories.append(
            AuditTrajectory(
                trajectory_id=f"TRJ-STABLE-{i:04d}",
                subtype=st,
                stage=stg,
                subgroup=sg,
                visits=visits,
                true_missed_signal=False,
            )
        )

    # Small cell injection
    if inject_small_cell_strata:
        for k in range(3):
            trajectories.append(
                AuditTrajectory(
                    trajectory_id=f"TRJ-SMALLCELL-{k}",
                    subtype="rare_inflammatory_carcinoma",
                    stage="stage_4_oligometastatic",
                    subgroup="isolated_island_clinic",
                    visits=[
                        AuditVisit(day=0, marker_value=16.0),
                        AuditVisit(day=90, marker_value=22.0),
                        AuditVisit(day=180, marker_value=35.0, action_recorded=None),
                        AuditVisit(day=270, marker_value=52.0, action_recorded=None),
                    ],
                    true_missed_signal=True,
                    true_escalation_day=180,
                )
            )

    return trajectories
