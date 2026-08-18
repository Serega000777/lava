"""Recipient-confirmed message delivery receipts

Revision ID: 0020
Revises: 0019
"""
import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_messages_undelivered_by_conversation",
        "messages",
        ["conversation_id", "sender_id"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_messages_undelivered_by_conversation", table_name="messages")
    op.drop_column("messages", "delivered_at")
