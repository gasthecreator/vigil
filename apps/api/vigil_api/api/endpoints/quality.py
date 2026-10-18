"""API Endpoints for Missed-Signal Quality Audit Engine (M10).

Implements:
- Master Plan §6.10, §11, and Phase 7b deliverables
- ADR 0016: Missed-Signal Quality Audit Privacy, Register, and Consent Governance
- Pre-Registration: docs/studies/PREREG-M10.md
- Small-cell suppression floor (k >= 5) to prevent patient re-identification
- Strictly neutral descriptive register (no punitive or accusatory terminology)
- RBAC: Strictly restricted to quality_lead and admin roles
- Cryptographically chained AuditEvent recording on every audit run
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.database import get_db
from vigil_api.models.patient import Patient
from vigil_api.models.v2 import AlertSeverity, User, UserRole
from vigil_api.schemas.v2 import (
    QualityAuditRequest,
    QualityAuditResponse,
    StratumAuditMetricResponse,
)
from vigil_ml.quality import (
    AuditReport,
    AuditTrajectory,
    AuditVisit,
    MissedSignalAuditEngine,
    generate_synthetic_audit_cohort,
    verify_neutral_register,
)

logger = logging.getLogger(__name__)

from vigil_api.consent import has_active_consent

router = APIRouter()


def _extract_trajectories_from_db(
    db: Session,
    current_user: User,
    facility_id: Optional[str] = None,
    lookback_days: int = 365,
) -> List[AuditTrajectory]:
    """Extract longitudinal surveillance trajectories from the facility database."""
    query = db.query(Patient)
    if facility_id:
        query = query.filter(Patient.facility_id == facility_id)
    patients = query.all()
    trajectories: List[AuditTrajectory] = []

    for p in patients:
        # ADR 0017: Enforce patient consent. Exclude patients without active consent.
        if not has_active_consent(p.id, db, current_user):
            continue

        obs_list = sorted(p.observations, key=lambda o: o.specimen_collected_at)
        if not obs_list:
            continue
        first_date = obs_list[0].specimen_collected_at
        visits = []
        for o in obs_list:
            dt = o.specimen_collected_at
            day = max(0, (dt - first_date).days)

            # Clinician-attributable actions check (Condition P13-C)
            # Must come from clinician events: AlertAcknowledgement or completed FollowUpTask
            action_rec = None
            if o.risk_assessment and o.risk_assessment.alerts:
                for a in o.risk_assessment.alerts:
                    for ack in a.acknowledgements:
                        if ack.acknowledged_at and 0 <= (ack.acknowledged_at - dt).days <= 30:
                            action_rec = "clinical_review_completed"
                            break
                    if action_rec:
                        break

            if not action_rec and p.follow_up_tasks:
                for t in p.follow_up_tasks:
                    if (
                        t.status == "completed"
                        and t.completed_at
                        and 0 <= (t.completed_at - dt).days <= 30
                    ):
                        action_rec = (
                            "imaging_ordered"
                            if t.task_type == "imaging_referral"
                            else "clinical_review_completed"
                        )
                        break

            visits.append(
                AuditVisit(
                    day=day,
                    marker_value=float(o.value),
                    action_recorded=action_rec,
                )
            )

        stage_str = f"stage_{p.initial_stage.lower()}" if p.initial_stage else "stage_2"
        trajectories.append(
            AuditTrajectory(
                trajectory_id=str(p.id),
                subtype=p.primary_cancer_type or "breast",
                stage=stage_str,
                subgroup="urban_referral" if p.facility_id else "rural_public",
                visits=visits,
            )
        )
    return trajectories


def _build_audit_response(report: AuditReport, facility_id: Optional[str]) -> QualityAuditResponse:
    """Transform an AuditReport dataclass into an API response schema with neutral narrative summary."""

    def _convert_breakdown(
        bd: Dict[str, Any],
    ) -> Dict[str, StratumAuditMetricResponse]:
        return {
            k: StratumAuditMetricResponse(
                stratum_name=v.stratum_name,
                total_signals=v.total_signals,
                action_not_recorded_count=v.action_not_recorded_count,
                action_not_recorded_rate=v.action_not_recorded_rate,
                is_suppressed=v.is_suppressed,
            )
            for k, v in bd.items()
        }

    subgroup_resp = _convert_breakdown(report.subgroup_breakdown)
    subtype_resp = _convert_breakdown(report.subtype_breakdown)
    stage_resp = _convert_breakdown(report.stage_breakdown)

    narrative = (
        f"Retrospective surveillance quality audit completed across {report.total_patients_audited} patient trajectories. "
        f"Identified {report.total_signals_detected} surveillance signals meeting clinical review criteria. "
        f"Timely clinical action was recorded in {report.total_action_recorded} instances. "
        f"For {report.total_action_not_recorded} signals, no corresponding action was recorded within the 30-day window "
        f"({report.overall_action_not_recorded_rate * 100:.1f}%, 95% bootstrap CI: "
        f"[{report.overall_bootstrap_ci_95[0] * 100:.1f}%, {report.overall_bootstrap_ci_95[1] * 100:.1f}%]). "
        f"Small-cell suppression applied to {report.suppressed_strata_count} strata to prevent patient re-identification."
    )

    if not verify_neutral_register(narrative):
        raise ValueError("Audit narrative violated mandatory neutral register.")

    return QualityAuditResponse(
        audit_id=report.audit_id,
        facility_id=facility_id,
        total_patients_audited=report.total_patients_audited,
        total_signals_detected=report.total_signals_detected,
        total_action_recorded=report.total_action_recorded,
        total_action_not_recorded=report.total_action_not_recorded,
        overall_action_not_recorded_rate=report.overall_action_not_recorded_rate,
        overall_bootstrap_ci_95=[
            report.overall_bootstrap_ci_95[0],
            report.overall_bootstrap_ci_95[1],
        ],
        subgroup_breakdown=subgroup_resp,
        subtype_breakdown=subtype_resp,
        stage_breakdown=stage_resp,
        suppressed_strata_count=report.suppressed_strata_count,
        register_audit_verified=True,
        narrative_summary=narrative,
        synthetic=True,
    )


@router.post("/audit", response_model=QualityAuditResponse, status_code=status.HTTP_200_OK)
def run_quality_audit(
    payload: QualityAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.QUALITY_LEAD, UserRole.ADMIN)),
):
    """Executes a retrospective missed-signal quality audit (M10).

    Access Control:
    - Restricted to quality_lead and admin roles.
    - Clinicians, nurse clerks, radiographers, patients, and caregivers are rejected with 403.

    Privacy & Register:
    - Small-cell suppression (k >= 5) on all demographic and clinical breakdown strata.
    - Strictly neutral descriptive register ('signal present, action not recorded').
    - Zero clinician or identifiable patient information returned.
    - Chained AuditEvent recorded for institutional auditability.
    """
    # Facility data and the synthetic benchmark are NEVER mixed: padding a small facility with
    # fabricated trajectories would produce official-looking quality statistics that are mostly invented.
    if payload.include_synthetic_benchmark:
        trajectories = generate_synthetic_audit_cohort(
            n_missed=150,
            n_acted=250,
            n_stable=600,
            inject_small_cell_strata=True,
            seed=20261017,
        )
    else:
        trajectories = _extract_trajectories_from_db(
            db,
            current_user,
            facility_id=payload.facility_id,
            lookback_days=payload.lookback_days,
        )

    engine = MissedSignalAuditEngine()
    report = engine.generate_audit_report(trajectories, n_bootstrap=payload.n_bootstrap)

    # Record cryptographic audit event
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="quality.audit.execute",
        resource_type="facility_audit",
        resource_id=report.audit_id,
        details={
            "facility_id": payload.facility_id,
            "lookback_days": payload.lookback_days,
            "n_bootstrap": payload.n_bootstrap,
            "total_patients_audited": report.total_patients_audited,
            "total_signals_detected": report.total_signals_detected,
            "suppressed_strata_count": report.suppressed_strata_count,
            "overall_rate": report.overall_action_not_recorded_rate,
        },
    )
    db.commit()

    response = _build_audit_response(report, payload.facility_id)
    if payload.include_synthetic_benchmark:
        response.narrative_summary = (
            "SYNTHETIC BENCHMARK ONLY - this is not facility data. " + response.narrative_summary
        )
    return response


@router.get("/audit/latest", response_model=QualityAuditResponse)
def get_latest_quality_audit(
    facility_id: Optional[str] = Query(None, description="Optional facility identifier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.QUALITY_LEAD, UserRole.ADMIN)),
):
    """Retrieves the latest retrospective missed-signal quality audit for the workstation.

    Access Control:
    - Restricted to quality_lead and admin roles.
    """
    req = QualityAuditRequest(
        facility_id=facility_id,
        lookback_days=365,
        n_bootstrap=1000,
        include_synthetic_benchmark=True,
    )
    return run_quality_audit(payload=req, db=db, current_user=current_user)
