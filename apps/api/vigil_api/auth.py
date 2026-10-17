"""Authentication and Role-Based Access Control (RBAC) Engine.

Implements Master Plan §9.2, §11, and Phase 5a Auth requirements:
- Roles: clinician, nurse_clerk, quality_lead, admin, patient, caregiver.
- JWT bearer token issuing and verification.
- Enforces role requirements on API endpoints.
- In production/staging (or when REQUIRE_AUTH=true), denies unauthenticated mutations.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from vigil_api.config import settings
from vigil_api.database import get_db
from vigil_api.models.v2 import User, UserRole

# Bearer security scheme (auto_error=False to allow conditional local fallback)
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Deterministic password hashing using salted SHA-256."""
    salt = "vigil_oncology_salt_"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def create_access_token(
    subject: str,
    role: str,
    facility_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": subject,
        "role": role,
        "facility_id": facility_id,
        "patient_id": patient_id,
        "iat": now,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    x_vigil_role: Optional[str] = Header(None, alias="X-Vigil-Role"),
    x_vigil_user_id: Optional[str] = Header(None, alias="X-Vigil-User-Id"),
) -> User:
    """FastAPI dependency for extracting the authenticated user.

    If REQUIRE_AUTH is active, requires a valid JWT token.
    If REQUIRE_AUTH is false and no token is present, supports local dev emulation
    via headers or defaults to clinician.
    """
    if auth and auth.credentials:
        payload = decode_token(auth.credentials)
        user_id = payload.get("sub")
        role = payload.get("role")
        facility_id = payload.get("facility_id")

        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if user is None:
            user = User(
                id=user_id,
                username=user_id,
                email=f"{user_id}@vigil.internal",
                full_name=f"User {user_id}",
                role=role or UserRole.CLINICIAN.value,
                facility_id=facility_id,
                active=True,
                hashed_password="",
            )
        user.patient_id = payload.get("patient_id")
        return user

    if settings.REQUIRE_AUTH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Local development / prototype fallback
    role = x_vigil_role or UserRole.CLINICIAN.value
    user_id = x_vigil_user_id or "local-dev-user"
    return User(
        id=user_id,
        username="local_dev",
        email="dev@vigil.internal",
        full_name="Local Development User",
        role=role,
        facility_id=None,
        active=True,
        hashed_password="",
    )


def require_roles(*allowed_roles: UserRole | str) -> Callable[[User], User]:
    """Dependency factory checking that current user has one of the allowed roles."""
    normalized_roles = [
        r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles
    ]

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role}' lacks permission for this resource.",
            )
        return current_user

    return role_checker
