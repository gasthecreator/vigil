"""009 scale indexes for triage/timeline budgets (MASTER_PLAN §9.5 / G-03).

Revision ID: c9d0e1f2a3b4
Revises: b2c3d4e5f6a8
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite indexes used by batched triage and 5-year timeline queries.
    with op.batch_alter_table("observations", schema=None) as batch_op:
        batch_op.create_index(
            "ix_observations_patient_specimen",
            ["patient_id", "specimen_collected_at"],
            unique=False,
        )
    with op.batch_alter_table("risk_assessments", schema=None) as batch_op:
        batch_op.create_index(
            "ix_risk_assessments_patient_created",
            ["patient_id", "created_at"],
            unique=False,
        )
    with op.batch_alter_table("follow_up_tasks", schema=None) as batch_op:
        batch_op.create_index(
            "ix_follow_up_tasks_status_patient_due",
            ["status", "patient_id", "due_date"],
            unique=False,
        )
    with op.batch_alter_table("consent_records", schema=None) as batch_op:
        batch_op.create_index(
            "ix_consent_records_patient_granted",
            ["patient_id", "granted"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("consent_records", schema=None) as batch_op:
        batch_op.drop_index("ix_consent_records_patient_granted")
    with op.batch_alter_table("follow_up_tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_follow_up_tasks_status_patient_due")
    with op.batch_alter_table("risk_assessments", schema=None) as batch_op:
        batch_op.drop_index("ix_risk_assessments_patient_created")
    with op.batch_alter_table("observations", schema=None) as batch_op:
        batch_op.drop_index("ix_observations_patient_specimen")
