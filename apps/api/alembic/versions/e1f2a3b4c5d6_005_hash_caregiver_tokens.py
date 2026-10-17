"""005 hash caregiver tokens at rest (Condition P11-E)

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
"""

import hashlib

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns
    with op.batch_alter_table("caregiver_shares") as batch:
        batch.add_column(sa.Column("token_hash", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("token_preview", sa.String(length=32), nullable=True, server_default="cg_***")
        )

    # 2. Hash existing plaintext tokens if present
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, share_token FROM caregiver_shares")).fetchall()
    for row in rows:
        share_id = row[0]
        token = row[1]
        if token:
            thash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            tprev = f"{token[:5]}...{token[-4:]}" if len(token) > 8 else "cg_***"
            conn.execute(
                sa.text(
                    "UPDATE caregiver_shares SET token_hash = :thash, token_preview = :tprev WHERE id = :id"
                ),
                {"thash": thash, "tprev": tprev, "id": share_id},
            )

    # 3. Clean up old share_token and enforce non-null unique index on token_hash
    with op.batch_alter_table("caregiver_shares") as batch:
        batch.drop_index("ix_caregiver_shares_share_token")
        batch.drop_column("share_token")
        batch.alter_column("token_hash", nullable=False)
        batch.alter_column("token_preview", nullable=False)
        batch.create_index("ix_caregiver_shares_token_hash", ["token_hash"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("caregiver_shares") as batch:
        batch.drop_index("ix_caregiver_shares_token_hash")
        batch.add_column(sa.Column("share_token", sa.String(length=64), nullable=True))
        batch.drop_column("token_preview")
        batch.drop_column("token_hash")
        batch.create_index("ix_caregiver_shares_share_token", ["share_token"], unique=True)
