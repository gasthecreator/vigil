"""Permit an explicit model abstention without inventing a numeric score.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a9
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("risk_assessments") as batch_op:
        batch_op.alter_column("score", existing_type=sa.Float(), nullable=True)
        batch_op.create_check_constraint(
            "chk_risk_null_score_requires_abstention",
            "score IS NOT NULL OR (abstention = true AND adjudicated_action = 'abstain')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM risk_assessments WHERE score IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot restore NOT NULL score: risk assessments contain explicit abstentions."
        )
    with op.batch_alter_table("risk_assessments") as batch_op:
        batch_op.drop_constraint("chk_risk_null_score_requires_abstention", type_="check")
        batch_op.alter_column("score", existing_type=sa.Float(), nullable=False)
