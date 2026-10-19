"""008 ocr_drafts: local lab-report importer drafts (never observations until confirm)

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ocr_drafts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("engine", sa.String(length=50), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("suggestion", sa.JSON(), nullable=False),
        sa.Column("confusion_flags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=100), nullable=True),
        sa.Column("observation_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ocr_drafts_id", "ocr_drafts", ["id"])
    op.create_index("ix_ocr_drafts_patient_id", "ocr_drafts", ["patient_id"])
    op.create_index("ix_ocr_drafts_status", "ocr_drafts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ocr_drafts_status", table_name="ocr_drafts")
    op.drop_index("ix_ocr_drafts_patient_id", table_name="ocr_drafts")
    op.drop_index("ix_ocr_drafts_id", table_name="ocr_drafts")
    op.drop_table("ocr_drafts")
