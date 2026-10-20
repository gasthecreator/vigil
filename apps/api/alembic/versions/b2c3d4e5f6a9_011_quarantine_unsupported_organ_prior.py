"""Allow baseline profiles to omit the retracted M1 organ prior.

Revision ID: b2c3d4e5f6a9
Revises: aa10bb20cc30, a1b2c3d4e5f7
"""

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a9"
down_revision = ("aa10bb20cc30", "a1b2c3d4e5f7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("baseline_profiles") as batch_op:
        batch_op.alter_column(
            "target_organ_susceptibility_vector",
            existing_type=sa.JSON(),
            nullable=True,
        )


def downgrade() -> None:
    # Historical rows may already contain null after the quarantine. A reverse
    # migration cannot invent the unsupported vector values, so fail explicitly.
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM baseline_profiles "
            "WHERE target_organ_susceptibility_vector IS NULL"
        )
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot restore NOT NULL: baseline rows have no validated M1 organ prior."
        )
    with op.batch_alter_table("baseline_profiles") as batch_op:
        batch_op.alter_column(
            "target_organ_susceptibility_vector",
            existing_type=sa.JSON(),
            nullable=False,
        )
