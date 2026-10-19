"""Alembic upgrade/downgrade on Postgres (G-02).

Skipped unless VIGIL_POSTGRES_TEST_URL / DATABASE_URL points at Postgres.
CI sets VIGIL_POSTGRES_TEST_URL via the service container.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.postgres


def _pg_url() -> str | None:
    for key in ("VIGIL_POSTGRES_TEST_URL", "DATABASE_URL"):
        url = os.environ.get(key, "")
        if url.startswith("postgresql"):
            # Strip query options for admin connections
            return url.split("?", 1)[0]
    return None


@pytest.fixture
def postgres_alembic():
    url = _pg_url()
    if not url:
        pytest.skip("No Postgres URL (set VIGIL_POSTGRES_TEST_URL)")

    schema = "vigil_mig_test"
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {schema}"))

    # search_path via connect_args — avoids ConfigParser '%' interpolation issues
    scoped_engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})

    ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg = Config(ini_path)
    # env.py reads DATABASE_URL; keep it bare (no %)
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    cfg.set_main_option("sqlalchemy.url", url)

    # Monkeypatch create_engine inside alembic env by setting PGOPTIONS
    os.environ["PGOPTIONS"] = f"-c search_path={schema}"

    yield cfg, url, scoped_engine, schema, admin

    if old is not None:
        os.environ["DATABASE_URL"] = old
    else:
        os.environ.pop("DATABASE_URL", None)
    os.environ.pop("PGOPTIONS", None)
    with admin.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
    scoped_engine.dispose()
    admin.dispose()


def test_postgres_alembic_upgrade_downgrade_upgrade(postgres_alembic):
    cfg, url, engine, schema, admin = postgres_alembic
    os.environ["PGOPTIONS"] = f"-c search_path={schema}"
    os.environ["DATABASE_URL"] = url

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        n = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = :s AND table_name = 'patients'"
            ),
            {"s": schema},
        ).scalar()
        assert n == 1
        idx = conn.execute(
            text(
                "SELECT count(*) FROM pg_indexes "
                "WHERE schemaname = :s AND indexname = 'ix_observations_patient_specimen'"
            ),
            {"s": schema},
        ).scalar()
        assert idx == 1

    command.downgrade(cfg, "b2c3d4e5f6a8")
    command.upgrade(cfg, "head")

    with Session(engine) as session:
        session.execute(
            text(
                "INSERT INTO patients (id, biological_sex, primary_cancer_type, synthetic, status, created_at, updated_at) "
                "VALUES ('pg-mig-1', 'female', 'breast', true, 'active', :t, :t)"
            ),
            {"t": datetime.now(timezone.utc)},
        )
        session.commit()


def test_gate_catches_sqlite_only_boolean_default_that_migration_001_once_had():
    """Seeded-defect proof that the Postgres job can fail: the pattern `server_default=text("0")` on a boolean column
    (what migration 001 shipped with) is valid on SQLite and rejected by Postgres. If this test ever stops raising on
    Postgres, the gate no longer detects the class of bug it exists for."""
    url = _pg_url()
    if not url:
        pytest.skip("No Postgres URL (set VIGIL_POSTGRES_TEST_URL)")
    from sqlalchemy import Boolean, Column, Integer, MetaData, Table
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.schema import CreateTable

    eng = create_engine(url)
    try:
        bad = Table(
            "zz_seeded_bad",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("flag", Boolean, nullable=False, server_default=text("0")),
        )
        good = Table(
            "zz_seeded_good",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("flag", Boolean, nullable=False, server_default=text("false")),
        )
        with eng.connect() as conn:
            with pytest.raises(DBAPIError):
                conn.execute(CreateTable(bad))
            conn.rollback()
            conn.execute(CreateTable(good))
            conn.rollback()
    finally:
        eng.dispose()
