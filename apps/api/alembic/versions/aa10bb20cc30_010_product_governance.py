"""J8 model governance records and audited M4 feedback.

Revision ID: aa10bb20cc30
Revises: c9d0e1f2a3b4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "aa10bb20cc30"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_governance_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sequence", sa.Integer(), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("record_hash", sa.String(length=64), nullable=False, unique=True),
    )
    op.create_index("ix_model_governance_records_sequence", "model_governance_records", ["sequence"])
    op.create_index("ix_model_governance_records_event_type", "model_governance_records", ["event_type"])
    op.create_table(
        "test_ladder_feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("modality", sa.String(length=64), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("turnaround_days", sa.Integer(), nullable=True),
        sa.Column("price_band", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("verified_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_by", sa.String(length=100), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_ladder_feedback_facility_id", "test_ladder_feedback", ["facility_id"])

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        for table in ("model_governance_records", "test_ladder_feedback"):
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER prevent_{table.lower()}_{action.lower()} "
                    f"BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only table'); END"
                )
    elif bind.dialect.name == "postgresql":
        op.execute(
            "CREATE FUNCTION vigil_reject_append_only_mutation() RETURNS trigger LANGUAGE plpgsql AS "
            "$$ BEGIN RAISE EXCEPTION 'append-only table'; END $$"
        )
        for table in ("model_governance_records", "test_ladder_feedback"):
            op.execute(
                f"CREATE TRIGGER prevent_{table}_mutation BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION vigil_reject_append_only_mutation()"
            )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("model_governance_records", "test_ladder_feedback"):
        if bind.dialect.name == "sqlite":
            for action in ("update", "delete"):
                op.execute(f"DROP TRIGGER IF EXISTS prevent_{table}_{action}")
        elif bind.dialect.name == "postgresql":
            op.execute(f"DROP TRIGGER IF EXISTS prevent_{table}_mutation ON {table}")
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS vigil_reject_append_only_mutation()")
    op.drop_index("ix_test_ladder_feedback_facility_id", table_name="test_ladder_feedback")
    op.drop_table("test_ladder_feedback")
    op.drop_index("ix_model_governance_records_event_type", table_name="model_governance_records")
    op.drop_index("ix_model_governance_records_sequence", table_name="model_governance_records")
    op.drop_table("model_governance_records")
