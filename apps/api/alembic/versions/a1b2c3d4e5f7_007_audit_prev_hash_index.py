"""007 index audit_events.prev_hash (O(log N) leaf check on append)

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
"""

from alembic import op

revision = "a1b2c3d4e5f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_audit_events_prev_hash", "audit_events", ["prev_hash"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_prev_hash", table_name="audit_events")
