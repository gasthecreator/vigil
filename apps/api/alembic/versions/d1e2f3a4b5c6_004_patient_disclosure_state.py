"""004 patient disclosure state (bad-news mode, server-enforced)

Revision ID: d1e2f3a4b5c6
Revises: c78219abf103
"""

import sqlalchemy as sa
from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "c78219abf103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.add_column(
            sa.Column("disclosure_unlocked_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.drop_column("disclosure_unlocked_at")
