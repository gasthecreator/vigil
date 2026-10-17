"""002_mrn_blind_index_and_idempotency_patient

Revision ID: a8d29b13fe45
Revises: 4188f88c97cc
Create Date: 2026-10-17 12:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8d29b13fe45"
down_revision: Union[str, Sequence[str], None] = "4188f88c97cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add blind index columns to patients
    with op.batch_alter_table("patients", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mrn_bidx", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("external_id_bidx", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_patients_mrn_bidx", ["mrn_bidx"], unique=False)
        batch_op.create_index("ix_patients_external_id_bidx", ["external_id_bidx"], unique=False)
        # Drop plaintext index on ciphertext columns
        batch_op.drop_index("ix_patients_external_id")

    # 2. Add patient_id to idempotency_records and scope uniqueness
    with op.batch_alter_table("idempotency_records", schema=None) as batch_op:
        batch_op.add_column(sa.Column("patient_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_idempotency_records_patient_id",
            "patients",
            ["patient_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_idempotency_records_patient_id", ["patient_id"], unique=False)
        batch_op.drop_index("ix_idempotency_records_idempotency_key")
        batch_op.create_index(
            "ix_idempotency_records_idempotency_key", ["idempotency_key"], unique=False
        )
        batch_op.create_unique_constraint(
            "uq_patient_idempotency_key", ["patient_id", "idempotency_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("idempotency_records", schema=None) as batch_op:
        batch_op.drop_constraint("uq_patient_idempotency_key", type_="unique")
        batch_op.drop_index("ix_idempotency_records_idempotency_key")
        batch_op.create_index(
            "ix_idempotency_records_idempotency_key", ["idempotency_key"], unique=True
        )
        batch_op.drop_index("ix_idempotency_records_patient_id")
        batch_op.drop_constraint("fk_idempotency_records_patient_id", type_="foreignkey")
        batch_op.drop_column("patient_id")

    with op.batch_alter_table("patients", schema=None) as batch_op:
        batch_op.create_index("ix_patients_external_id", ["external_id"], unique=False)
        batch_op.drop_index("ix_patients_external_id_bidx")
        batch_op.drop_index("ix_patients_mrn_bidx")
        batch_op.drop_column("external_id_bidx")
        batch_op.drop_column("mrn_bidx")
