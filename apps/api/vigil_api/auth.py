"""Authentication and Role-Based Access Control (RBAC) Engine.

Implements Master Plan §9.2, §11, and Phase 5a Auth requirements:
- Roles: clinician, nurse_clerk, quality_lead, admin, patient, caregiver.
- JWT bearer token issuing and verification.
- Enforces role requirements on API endpoints.
- In production/staging (or when REQUIRE_AUTH=true), denies unauthenticated mutations.
"""

from __future__ import annotations

import hashlib
import secrets
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


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hash password using scrypt with per-user salt (RFC 7914 / NIST SP 800-63B)."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or not plain_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) == 6 and parts[0] == "scrypt":
            n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
            salt = bytes.fromhex(parts[4])
            expected_dk = bytes.fromhex(parts[5])
            dk = hashlib.scrypt(plain_password.encode("utf-8"), salt=salt, n=n, r=r, p=p)
            return secrets.compare_digest(dk, expected_dk)
    except Exception:
        return False
    return False


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

    In non-local profiles or when REQUIRE_AUTH is active, requires a valid JWT token
    and resolves the active user from the database.
    Header-claimed roles (X-Vigil-Role) are strictly rejected outside 'local' environment.
    """
    if auth and auth.credentials:
        payload = decode_token(auth.credentials)
        user_id = payload.get("sub")
        role = payload.get("role")
        facility_id = payload.get("facility_id")

        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if user is None:
            if settings.ENVIRONMENT != "local":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Local dev only: create/return user if not present
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
        elif not user.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user.patient_id = payload.get("patient_id")
        return user

    if settings.ENVIRONMENT != "local" or settings.REQUIRE_AUTH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials. Header-claimed roles are forbidden in non-local environments.",
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
    normalized_roles = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role}' lacks permission for this resource.",
            )
        return current_user

    return role_checker
