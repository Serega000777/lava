"""Message read receipts

Revision ID: 0018
Revises: 0017
"""
import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_messages_unread_by_conversation",
        "messages",
        ["conversation_id", "sender_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_messages_unread_by_conversation", table_name="messages")
    op.drop_column("messages", "read_at")
