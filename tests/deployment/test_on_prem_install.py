"""tests/deployment/test_on_prem_install.py

Tests for Vigil On-Premise Installation & Air-Gapped Deployment.
Enforces Master Plan §6.0, §11, §12, and WP8.4.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from install_on_prem import (
    run_database_migrations,
    seed_admin_user,
    validate_security_configuration,
    verify_installation,
)


def test_validate_security_rejects_insecure_defaults(monkeypatch):
    """Asserts that insecure defaults (short secret, disabled auth, wildcard CORS) are blocked."""
    # Test missing auth
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", "k" * 32)
    monkeypatch.setenv("CORS_ORIGINS", "https://vigil.local")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    valid, errors = validate_security_configuration()
    assert not valid
    assert any("REQUIRE_AUTH" in e for e in errors)

    # Test short secret
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "short-secret")
    valid, errors = validate_security_configuration()
    assert not valid
    assert any("JWT_SECRET_KEY" in e for e in errors)

    # Test insecure phrase secret
    monkeypatch.setenv("JWT_SECRET_KEY", "password_password_password_password")
    valid, errors = validate_security_configuration()
    assert not valid
    assert any("insecure or default phrase" in e for e in errors)

    # Test wildcard CORS
    monkeypatch.setenv("JWT_SECRET_KEY", "valid_secret_key_with_at_least_32_characters_12345")
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com,*")
    valid, errors = validate_security_configuration()
    assert not valid
    assert any("CORS_ORIGINS" in e for e in errors)

    # Test missing field encryption key
    monkeypatch.setenv("CORS_ORIGINS", "https://hospital.local")
    monkeypatch.delenv("FIELD_ENCRYPTION_KEY", raising=False)
    valid, errors = validate_security_configuration()
    assert not valid
    assert any("FIELD_ENCRYPTION_KEY" in e for e in errors)


def test_validate_security_passes_compliant_config(monkeypatch):
    """Asserts that properly configured security environment passes audit."""
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "production_strong_key_32_bytes_long_entropy_valid")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", "field_encryption_strong_master_key_32b_valid")
    monkeypatch.setenv("CORS_ORIGINS", "https://vigil.hospital.local,https://192.168.1.50")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    valid, errors = validate_security_configuration()
    assert valid, f"Expected valid config but got errors: {errors}"
    assert len(errors) == 0


def test_on_prem_install_full_flow(tmp_path, monkeypatch):
    """Tests migrations, admin seeding, and verification in a clean temporary environment."""
    db_file = tmp_path / "on_prem_test.db"
    from vigil_api.config import settings

    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    # settings is process-global; CI may have already loaded a Postgres DATABASE_URL.
    monkeypatch.setattr(settings, "DATABASE_URL", db_url)
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.setattr(settings, "REQUIRE_AUTH", True)
    monkeypatch.setenv("JWT_SECRET_KEY", "a8f5c9e2b4d13708e5f2a1b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", "b9e1d2c3f4a58679a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3")
    monkeypatch.setenv("CORS_ORIGINS", "https://hospital.local")

    # 1. Run validation
    valid, errors = validate_security_configuration()
    assert valid, f"Config validation errors: {errors}"

    # 2. Run migrations
    assert run_database_migrations() is True
    assert db_file.exists()

    # 2. Seed admin user
    pwd = seed_admin_user("admin_test@hospital.local", "SuperSecurePassword123!")
    assert pwd == "SuperSecurePassword123!"

    # 3. Seed again should skip without error
    pwd2 = seed_admin_user("admin_test@hospital.local")
    assert pwd2 is None

    # 4. Verify installation
    assert verify_installation() is True


def test_install_script_cli(tmp_path):
    """Tests CLI execution of install_on_prem.py in subprocess with env file."""
    env_file = tmp_path / "production.env"
    db_file = tmp_path / "cli_test.db"
    env_content = f"""
REQUIRE_AUTH=true
JWT_SECRET_KEY=production_strong_key_32_bytes_long_entropy_valid
FIELD_ENCRYPTION_KEY=field_encryption_strong_master_key_32b_valid
CORS_ORIGINS=https://vigil.hospital.local
DATABASE_URL=sqlite:///{db_file}
"""
    env_file.write_text(env_content.strip())

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "install_on_prem.py"),
            "--config-file",
            str(env_file),
            "--migrate-db",
            "--seed-admin",
            "--verify",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"CLI installer failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert "Production Security Audit PASSED" in proc.stdout
    assert "Vigil On-Premise installation and setup completed successfully." in proc.stdout


def test_compose_stack_files_exist_and_are_non_root():
    """G-01: compose + Dockerfiles present; runtime USER is non-root vigil."""
    compose = (ROOT / "infra" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres:16.6-alpine@sha256:" in compose
    assert "Dockerfile.api" in compose
    assert "Dockerfile.web" in compose
    assert "Dockerfile.worker" in compose
    assert "healthcheck:" in compose
    for name in ("Dockerfile.api", "Dockerfile.web", "Dockerfile.worker"):
        text = (ROOT / "infra" / name).read_text(encoding="utf-8")
        assert "USER vigil" in text
        assert "@sha256:" in text
    env_ex = ROOT / "infra" / ".env.compose.example"
    assert env_ex.exists()
    assert "POSTGRES_PASSWORD" in env_ex.read_text(encoding="utf-8")


def _env_file(path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def test_compose_is_secure_by_default_and_dev_profile_is_separate():
    """The example operators copy must be the production profile; the insecure demo profile is a different file.
    Found by overseer review: the first version shipped ENVIRONMENT=local / REQUIRE_AUTH=false / default JWT secret."""
    compose = (ROOT / "infra" / "docker-compose.yml").read_text(encoding="utf-8")
    prod = _env_file(ROOT / "infra" / ".env.compose.example")
    dev = _env_file(ROOT / "infra" / ".env.compose.dev.example")

    assert prod["ENVIRONMENT"] == "production" and prod["REQUIRE_AUTH"] == "true"
    for key in ("POSTGRES_PASSWORD", "JWT_SECRET_KEY", "VIGIL_FIELD_ENCRYPTION_KEYS"):
        assert "REPLACE_ME" in prod[key], f"{key} must be a placeholder the API refuses to start with"
    assert dev["ENVIRONMENT"] == "local" and dev["REQUIRE_AUTH"] == "false"

    # compose defaults are the secure ones and secrets have no default
    assert "ENVIRONMENT: ${ENVIRONMENT:-production}" in compose
    assert "REQUIRE_AUTH: ${REQUIRE_AUTH:-true}" in compose
    assert "JWT_SECRET_KEY: ${JWT_SECRET_KEY:?" in compose
    assert "VIGIL_FIELD_ENCRYPTION_KEYS: ${VIGIL_FIELD_ENCRYPTION_KEYS:?" in compose
    assert "local-dev-only" not in compose
    # the database is never published on all interfaces
    assert '"127.0.0.1:${POSTGRES_PORT:-5432}:5432"' in compose
    assert '- "${POSTGRES_PORT:-5432}:5432"' not in compose

    # the entrypoint refuses unreplaced placeholders
    entry = (ROOT / "infra" / "entrypoint-api.sh").read_text(encoding="utf-8")
    assert "REPLACE_ME" in entry and "exit 78" in entry
