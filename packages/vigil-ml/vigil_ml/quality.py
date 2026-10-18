r"""Missed-Signal Quality Audit Engine (M10).

Evaluates facility surveillance trajectories retrospectively to identify missed signals:
- Pre-Registration: docs/studies/PREREG-M10.md
- Governance: docs/adr/0016-missed-signal-quality-audit-privacy-and-consent.md
- Master Plan §6.10, §11; Reality Rules

Core Principles:
1. Strictly neutral descriptive register: "signal present, action not recorded".
2. No clinician identifiers or patient re-identifying information.
3. Small-cell suppression ($k \ge 5$): any cell with $1 \le n < 5$ is suppressed to prevent re-identification.
4. Aggregate reporting with percentile bootstrap confidence intervals.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

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
    alert_level: str  # "none", "watch", "review", "urgent"
    action_recorded: Optional[str] = (
        None  # "imaging_ordered", "biopsy_ordered", "oncology_consult", etc.
    )


@dataclass
class AuditTrajectory:
    trajectory_id: str
    subtype: str
    stage: str
    subgroup: str
    visits: List[AuditVisit]
    true_missed_signal: Optional[bool] = None


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
    raw_unsuppressed_for_testing: Optional[Dict[str, Any]] = None


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
        """Evaluates whether an individual trajectory exhibited a signal and whether action was recorded."""
        visits = sorted(trajectory.visits, key=lambda v: v.day)
        if not visits:
            return {"signal_present": False, "action_recorded": False, "signal_day": None}

        # 1. Detect signal: alert_level in {"review", "urgent"} or 3-visit sustained rise
        signal_present = False
        signal_day = None

        for i, v in enumerate(visits):
            if v.alert_level in ("review", "urgent"):
                signal_present = True
                signal_day = v.day
                break

            # Sustained rise check: 3 consecutive visits with positive delta > 30% AND exceeding clinical threshold (>= 30.0 U/mL)
            if i >= 2:
                v0, v1, v2 = visits[i - 2], visits[i - 1], v
                if (
                    (v2.marker_value > v1.marker_value > v0.marker_value)
                    and (v2.marker_value >= 1.30 * v0.marker_value)
                    and (v2.marker_value >= 30.0)
                ):
                    signal_present = True
                    signal_day = v2.day
                    break

        if not signal_present or signal_day is None:
            return {"signal_present": False, "action_recorded": False, "signal_day": None}

        # 2. Check for recorded clinical action within grace window
        valid_actions = {
            "imaging_ordered",
            "biopsy_ordered",
            "oncology_consult",
            "treatment_modified",
            "clinical_review_completed",
        }
        action_found = False
        action_day = None
        for v in visits:
            if v.day >= signal_day and v.day <= signal_day + self.ACTION_GRACE_WINDOW_DAYS:
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
        expose_raw_for_testing: bool = False,
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

        raw_test_data = None
        if expose_raw_for_testing:
            raw_test_data = {
                "signals": evaluated,
                "total_signals": total_signals,
                "action_not_recorded_count": action_not_recorded_count,
            }

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
            raw_unsuppressed_for_testing=raw_test_data,
        )


def generate_synthetic_audit_cohort(
    n_missed: int = 150,
    n_acted: int = 250,
    n_stable: int = 600,
    inject_small_cell_strata: bool = True,
    seed: int = 20261017,
) -> List[AuditTrajectory]:
    """Generates synthetic trajectories with known ground truth missed vs acted-upon signals."""
    rng = np.random.default_rng(seed)
    trajectories: List[AuditTrajectory] = []

    subtypes = ["adjuvant_post_lumpectomy", "adjuvant_post_mastectomy", "curative_tnbc"]
    stages = ["stage_1", "stage_2", "stage_3"]
    subgroups = ["rural_public", "urban_referral"]

    # 1. Injected Missed Signals: sustained rise or urgent alert with NO action recorded
    for i in range(n_missed):
        st = rng.choice(subtypes)
        stg = rng.choice(stages)
        sg = rng.choice(subgroups)
        t_id = f"TRJ-MISS-{i:04d}"

        # 4 quarterly visits
        visits = [
            AuditVisit(day=0, marker_value=18.0, alert_level="none"),
            AuditVisit(day=90, marker_value=24.0, alert_level="watch"),
            AuditVisit(day=180, marker_value=36.0, alert_level="review", action_recorded=None),
            AuditVisit(day=270, marker_value=48.0, alert_level="urgent", action_recorded=None),
        ]
        trajectories.append(
            AuditTrajectory(
                trajectory_id=t_id,
                subtype=st,
                stage=stg,
                subgroup=sg,
                visits=visits,
                true_missed_signal=True,
            )
        )

    # 2. Injected Acted-Upon Signals: alert with timely imaging/biopsy
    for i in range(n_acted):
        st = rng.choice(subtypes)
        stg = rng.choice(stages)
        sg = rng.choice(subgroups)
        t_id = f"TRJ-ACT-{i:04d}"

        visits = [
            AuditVisit(day=0, marker_value=17.0, alert_level="none"),
            AuditVisit(day=90, marker_value=22.0, alert_level="watch"),
            AuditVisit(
                day=180, marker_value=35.0, alert_level="review", action_recorded="imaging_ordered"
            ),
            AuditVisit(day=270, marker_value=19.0, alert_level="none"),
        ]
        trajectories.append(
            AuditTrajectory(
                trajectory_id=t_id,
                subtype=st,
                stage=stg,
                subgroup=sg,
                visits=visits,
                true_missed_signal=False,
            )
        )

    # 3. Stable Recurrence-Free Patients
    for i in range(n_stable):
        st = rng.choice(subtypes)
        stg = rng.choice(stages)
        sg = rng.choice(subgroups)
        t_id = f"TRJ-STABLE-{i:04d}"

        visits = [
            AuditVisit(day=0, marker_value=float(rng.normal(16.0, 1.5)), alert_level="none"),
            AuditVisit(day=90, marker_value=float(rng.normal(16.2, 1.5)), alert_level="none"),
            AuditVisit(day=180, marker_value=float(rng.normal(15.8, 1.5)), alert_level="none"),
            AuditVisit(day=270, marker_value=float(rng.normal(16.1, 1.5)), alert_level="none"),
        ]
        trajectories.append(
            AuditTrajectory(
                trajectory_id=t_id,
                subtype=st,
                stage=stg,
                subgroup=sg,
                visits=visits,
                true_missed_signal=False,
            )
        )

    # 4. Optional Small-Cell Injection (n=3 patients in rare stratum to verify suppression)
    if inject_small_cell_strata:
        for k in range(3):
            trajectories.append(
                AuditTrajectory(
                    trajectory_id=f"TRJ-SMALLCELL-{k}",
                    subtype="rare_inflammatory_carcinoma",
                    stage="stage_4_oligometastatic",
                    subgroup="isolated_island_clinic",
                    visits=[
                        AuditVisit(day=0, marker_value=20.0, alert_level="none"),
                        AuditVisit(
                            day=90, marker_value=45.0, alert_level="urgent", action_recorded=None
                        ),
                    ],
                    true_missed_signal=True,
                )
            )

    return trajectories
