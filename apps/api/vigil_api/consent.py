"""Patient Consent Verification Engine.

Implements Master Plan §11 and Phase 5a Consent requirements:
- Verifies that an unexpired, unwithdrawn ConsentRecord exists prior to any patient data read.
- Validates role-specific access constraints:
  - 'patient' role may only access their own record.
  - 'caregiver' role requires explicit caregiver consent delegation.
  - All roles are blocked from reading patient clinical data if consent is revoked, expired, or absent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from vigil_api.models.v2 import ConsentRecord, Patient, User, UserRole


def verify_patient_consent(
    patient_id: str,
    db: Session,
    user: User,
    required_scope: str = "surveillance_monitoring",
) -> Patient:
    """Verify active patient consent and authorization before disclosing patient data."""
    now = datetime.now(timezone.utc)

    # 1. Verify patient existence
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    # 2. Check active consent records
    consents = (
        db.execute(
            select(ConsentRecord)
            .where(ConsentRecord.patient_id == patient_id)
            .order_by(ConsentRecord.granted_at.desc())
        )
        .scalars()
        .all()
    )

    # The most recent decision per consent type governs: a later withdrawal (granted=False or
    # withdrawn_at set) or an expired record revokes an earlier grant instead of being skipped.
    active_consent: Optional[ConsentRecord] = None
    seen_types: set[str] = set()
    for c in consents:
        if c.consent_type in seen_types:
            continue
        seen_types.add(c.consent_type)
        if not c.granted:
            continue
        if c.withdrawn_at is not None:
            continue
        if c.expires_at is not None:
            # Handle tz-aware and naive timestamps safely
            exp = c.expires_at if c.expires_at.tzinfo else c.expires_at.replace(tzinfo=timezone.utc)
            if exp <= now:
                continue
        active_consent = c
        break

    if active_consent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: active patient consent is absent, expired, or withdrawn.",
        )

    # 3. Role-specific authorization checks
    if user.role == UserRole.PATIENT.value:
        # Patient can only access their own record
        is_own = (
            user.id == patient.id
            or user.username == patient.id
            or getattr(user, "patient_id", None) == patient.id
            or getattr(user, "id", None) == getattr(patient, "external_id", None)
        )
        if not is_own:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: patient cannot access another patient's records.",
            )

    elif user.role == UserRole.CAREGIVER.value:
        # Caregiver access requires explicit caregiver consent delegation in scope
        if (
            "caregiver" not in active_consent.scope.lower()
            and active_consent.scope.lower() != "full"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: caregiver delegation is not authorized by patient consent.",
            )

    return patient


def has_active_consent(
    patient_id: str,
    db: Session,
    user: User,
    required_scope: str = "surveillance_monitoring",
) -> bool:
    """Check whether active patient consent exists without raising an HTTPException."""
    try:
        verify_patient_consent(
            patient_id=patient_id, db=db, user=user, required_scope=required_scope
        )
        return True
    except HTTPException:
        return False
