"""003_symptoms_and_caregiver_shares

Revision ID: c78219abf103
Revises: a8d29b13fe45
Create Date: 2026-10-17 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c78219abf103"
down_revision: Union[str, Sequence[str], None] = "a8d29b13fe45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create symptoms table
    op.create_table(
        "symptoms",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("symptom_name", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("input_modality", sa.String(length=20), nullable=False, server_default="text"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_symptoms_id", "symptoms", ["id"])
    op.create_index("ix_symptoms_patient_id", "symptoms", ["patient_id"])
    op.create_index("ix_symptoms_symptom_name", "symptoms", ["symptom_name"])

    # 2. Create caregiver_shares table
    op.create_table(
        "caregiver_shares",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("share_token", sa.String(length=64), nullable=False),
        sa.Column("caregiver_name", sa.String(length=100), nullable=False),
        sa.Column(
            "relationship_type", sa.String(length=50), nullable=False, server_default="caregiver"
        ),
        sa.Column("scope", sa.String(length=50), nullable=False, server_default="view_summary"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_caregiver_shares_id", "caregiver_shares", ["id"])
    op.create_index("ix_caregiver_shares_patient_id", "caregiver_shares", ["patient_id"])
    op.create_index(
        "ix_caregiver_shares_share_token", "caregiver_shares", ["share_token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_caregiver_shares_share_token", table_name="caregiver_shares")
    op.drop_index("ix_caregiver_shares_patient_id", table_name="caregiver_shares")
    op.drop_index("ix_caregiver_shares_id", table_name="caregiver_shares")
    op.drop_table("caregiver_shares")

    op.drop_index("ix_symptoms_symptom_name", table_name="symptoms")
    op.drop_index("ix_symptoms_patient_id", table_name="symptoms")
    op.drop_index("ix_symptoms_id", table_name="symptoms")
    op.drop_table("symptoms")
