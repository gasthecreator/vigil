"""006 radiotherapy continuity and delay ledger (M7)

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
"""

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. linac_machines
    op.create_table(
        "linac_machines",
        sa.Column("id", sa.String(length=36), primary_key=True, index=True),
        sa.Column(
            "facility_id",
            sa.String(length=36),
            sa.ForeignKey("facilities.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("machine_name", sa.String(length=100), nullable=False),
        sa.Column("daily_slot_capacity", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="operational"),
        sa.Column("downtime_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_return_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_linac_machines_status", "linac_machines", ["status"])

    # 2. radiotherapy_courses
    op.create_table(
        "radiotherapy_courses",
        sa.Column("id", sa.String(length=36), primary_key=True, index=True),
        sa.Column(
            "patient_id",
            sa.String(length=36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "assigned_machine_id",
            sa.String(length=36),
            sa.ForeignKey("linac_machines.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("clinical_context", sa.String(length=50), nullable=False),
        sa.Column("total_fractions", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("fractions_delivered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prescribed_start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("urgency_tier", sa.String(length=50), nullable=False, server_default="routine"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("baseline_subgroup", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_radiotherapy_courses_status", "radiotherapy_courses", ["status"])

    # 3. delay_ledger_entries
    op.create_table(
        "delay_ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True, index=True),
        sa.Column(
            "patient_id",
            sa.String(length=36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "course_id",
            sa.String(length=36),
            sa.ForeignKey("radiotherapy_courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("delay_days", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("marginal_harm", sa.Float(), nullable=True),
        sa.Column("moved_from_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moved_to_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clinician_overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "recorded_by", sa.String(length=100), nullable=False, server_default="system_cp_sat"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("delay_ledger_entries")
    op.drop_table("radiotherapy_courses")
    op.drop_table("linac_machines")
