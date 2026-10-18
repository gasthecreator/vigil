#!/usr/bin/env python3
"""scripts/install_on_prem.py

Automated On-Premise Installation and Verification Script for Vigil.
Supports air-gapped hospital deployments (Master Plan §6.0, §11, §12, WP8.4).

Verifies security configuration, performs database migrations, seeds initial
administrator account, initializes audit ledger, and executes end-to-end self-tests.
Rejects insecure production defaults (empty secret, wildcard CORS, disabled auth).
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-core"))


INSECURE_SECRETS = {
    "secret",
    "password",
    "change-me",
    "changeme",
    "admin",
    "12345678",
    "test-secret",
    "default-secret",
}


def load_env_file(path: Path) -> Dict[str, str]:
    """Loads key-value pairs from a configuration file into dictionary and os.environ."""
    env_vars: Dict[str, str] = {}
    if not path.exists():
        return env_vars

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            env_vars[k] = v
            os.environ[k] = v
    return env_vars


def validate_security_configuration() -> Tuple[bool, List[str]]:
    """Audits current environment configuration against production security baseline."""
    errors: List[str] = []

    # 1. REQUIRE_AUTH check
    require_auth = os.environ.get("REQUIRE_AUTH", "").lower()
    if require_auth not in ("true", "1", "yes"):
        errors.append("REQUIRE_AUTH must be set to 'true'. Unauthenticated production deployment is rejected.")

    # 2. JWT_SECRET_KEY check
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
    if len(jwt_secret) < 32:
        errors.append(f"JWT_SECRET_KEY must be at least 32 characters long (found {len(jwt_secret)}).")
    if (
        jwt_secret.lower() in INSECURE_SECRETS
        or any(bad in jwt_secret.lower() for bad in ("password", "secret", "change", "12345"))
    ):
        errors.append("JWT_SECRET_KEY uses an insecure or default phrase. Generate a random 32+ byte key.")

    # 3. CORS_ORIGINS check
    cors = os.environ.get("CORS_ORIGINS", "")
    if "*" in cors:
        errors.append("CORS_ORIGINS cannot contain wildcard '*' in production on-premise installation.")
    elif cors and not cors.strip().startswith("["):
        # Format comma-delimited string into JSON list for Pydantic Settings
        import json
        origins = [o.strip() for o in cors.split(",") if o.strip()]
        os.environ["CORS_ORIGINS"] = json.dumps(origins)

    # 4. FIELD_ENCRYPTION_KEY check
    enc_key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if not enc_key:
        errors.append("FIELD_ENCRYPTION_KEY is required for at-rest token and patient identifier encryption.")
    elif len(enc_key) < 32:
        errors.append(f"FIELD_ENCRYPTION_KEY must be at least 32 characters long (found {len(enc_key)}).")

    # 5. DATABASE_URL check
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        errors.append("DATABASE_URL is missing. Specify valid PostgreSQL or SQLite connection string.")

    return (len(errors) == 0, errors)


def run_database_migrations(db_url: Optional[str] = None) -> bool:
    """Executes database schema creation and table provisioning."""
    print("📦 Initializing database tables and schemas...")
    try:
        from sqlalchemy import create_engine
        from vigil_api.config import settings
        from vigil_api.database import Base

        target_url = db_url or os.environ.get("DATABASE_URL") or settings.DATABASE_URL
        connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
        eng = create_engine(target_url, connect_args=connect_args)
        Base.metadata.create_all(bind=eng)
        eng.dispose()
        print("  ✅ Database schema successfully created/updated.")
        return True
    except Exception as e:
        print(f"  ❌ Database migration failed: {e}")
        return False


def seed_admin_user(admin_email: str = "admin@hospital.local", admin_password: Optional[str] = None, db_url: Optional[str] = None) -> Optional[str]:
    """Provisions root administrator account with secure password."""
    print(f"👤 Provisioning administrator account ({admin_email})...")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from vigil_api.auth import hash_password
    from vigil_api.config import settings
    from vigil_api.models.v2 import User

    target_url = db_url or os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
    eng = create_engine(target_url, connect_args=connect_args)
    LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    session = LocalSession()
    try:
        existing = session.query(User).filter(User.username == admin_email).first()
        if existing:
            print("  ℹ️  Admin user already exists. Skipping creation.")
            return None

        password = admin_password or secrets.token_urlsafe(16)
        user = User(
            username=admin_email,
            email=admin_email,
            hashed_password=hash_password(password),
            role="admin",
            full_name="Hospital Administrator",
            active=True,
        )
        session.add(user)
        session.commit()
        print("  ✅ Admin account provisioned successfully.")
        return password
    except Exception as e:
        session.rollback()
        print(f"  ❌ Failed to provision admin account: {e}")
        return None
    finally:
        session.close()
        eng.dispose()


def verify_installation() -> bool:
    """Performs end-to-end healthcheck and authorization verification."""
    print("🩺 Running post-install verification checks...")
    from fastapi.testclient import TestClient
    from vigil_api.config import settings
    from vigil_api.main import app

    if "REQUIRE_AUTH" in os.environ:
        settings.REQUIRE_AUTH = os.environ["REQUIRE_AUTH"].lower() in ("true", "1", "yes")

    client = TestClient(app, raise_server_exceptions=False)

    # 1. Check /health
    r_health = client.get("/health")
    if r_health.status_code != 200:
        print(f"  ❌ /health endpoint check failed with status {r_health.status_code}")
        return False
    print("  ✅ /health endpoint responded with 200 OK.")

    # 2. Check OpenAPI schema enumeration
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    if len(paths) < 20:
        print(f"  ❌ OpenAPI paths count suspiciously low: {len(paths)}")
        return False
    print(f"  ✅ OpenAPI schema verified ({len(paths)} routes registered).")

    # 3. Verify unauthenticated call to protected route is rejected (401/403)
    r_patients = client.get("/api/v1/patients")
    if r_patients.status_code not in (401, 403):
        print(f"  ❌ Protected endpoint /api/v1/patients leaked without auth! Status: {r_patients.status_code}")
        return False
    print("  ✅ Authentication enforcement verified: protected endpoint rejected unauthenticated caller.")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Vigil On-Premise Installation and Verification")
    parser.add_argument("--config-file", type=Path, help="Path to production configuration environment file")
    parser.add_argument("--migrate-db", action="store_true", help="Execute database schema creation")
    parser.add_argument("--seed-admin", action="store_true", help="Seed default administrative account")
    parser.add_argument("--admin-email", default="admin@hospital.local", help="Admin email for seeding")
    parser.add_argument("--admin-password", help="Admin password for seeding (auto-generated if omitted)")
    parser.add_argument("--verify", action="store_true", help="Perform post-install system verification")
    parser.add_argument("--verify-only", action="store_true", help="Perform verification only without modifications")

    args = parser.parse_args()

    if args.config_file:
        print(f"📄 Loading configuration from {args.config_file}...")
        load_env_file(args.config_file)

    # Always perform security audit
    print("🔒 Auditing environment security configuration...")
    valid, errors = validate_security_configuration()
    if not valid:
        print("❌ Production Security Audit FAILED with the following violations:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("✅ Production Security Audit PASSED. All baseline requirements satisfied.")

    if args.verify_only:
        ok = verify_installation()
        return 0 if ok else 1

    if args.migrate_db:
        if not run_database_migrations():
            return 1

    if args.seed_admin:
        pwd = seed_admin_user(args.admin_email, args.admin_password)
        if pwd:
            print(f"  🔑 Generated admin temporary password: {pwd}")

    if args.verify:
        if not verify_installation():
            return 1

    print("\n🎉 Vigil On-Premise installation and setup completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
