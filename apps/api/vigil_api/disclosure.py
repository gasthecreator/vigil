"""Bad-news disclosure gate (hazard H17), shared by every patient-facing route.

While a patient's escalate-level (or high-tier) result has not been released by a clinician
(``Patient.disclosure_unlocked_at is None``), no route reachable with a ``patient`` or ``caregiver`` token may
return model output about that patient. Clinical staff are never affected. The decision is made on the server
from stored state; nothing in the request can change it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vigil_api.models.patient import RiskInference
from vigil_api.models.v2 import Patient, RiskAssessment, User, UserRole

DISCLOSURE_LOCKED_DETAIL = {
    "code": "disclosure_locked",
    "message": "Your care team has this result and will talk it through with you. Please ask them when you are ready.",
}

PATIENT_FACING_ROLES = frozenset({UserRole.PATIENT.value, UserRole.CAREGIVER.value})


def role_value(user: User) -> str:
    role: Any = user.role
    return role if isinstance(role, str) else role.value


def has_unreleased_bad_news(db: Session, patient: Patient) -> bool:
    """True if the patient has an escalate-level or high-tier result and no clinician release."""
    if patient.disclosure_unlocked_at is not None:
        return False
    escalated = db.execute(
        select(RiskAssessment.id)
        .where(RiskAssessment.patient_id == patient.id)
        .where(
            (RiskAssessment.adjudicated_action == "escalate") | (RiskAssessment.risk_tier == "high")
        )
        .limit(1)
    ).first()
    if escalated is not None:
        return True
    legacy = db.execute(
        select(RiskInference.id)
        .where(RiskInference.patient_id == patient.id)
        .where(RiskInference.triage_flag.is_(True))
        .limit(1)
    ).first()
    return legacy is not None


def withheld_for(db: Session, patient: Patient, user: User) -> bool:
    """True when this caller is patient-facing and the patient's bad news is still locked."""
    return role_value(user) in PATIENT_FACING_ROLES and has_unreleased_bad_news(db, patient)
