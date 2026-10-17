import os
from logging.config import fileConfig

import vigil_api.models  # noqa: F401 - ensure all models are registered on Base.metadata
from alembic import context
from sqlalchemy import create_engine, pool
from vigil_api.config import settings
from vigil_api.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve target database URL respecting alembic config, env vars, and settings."""
    url = config.get_main_option("sqlalchemy.url")
    if not url or url.startswith("driver://"):
        url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Supports SQLite ALTER TABLE batch migrations
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
