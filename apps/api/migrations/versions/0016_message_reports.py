"""Message reports

Revision ID: 0016
Revises: 0015
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_code", sa.String(length=32), nullable=True),
        sa.Column("resolution_comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("reporter_id <> reported_user_id"),
        sa.CheckConstraint("status IN ('open', 'resolved', 'dismissed')"),
        sa.CheckConstraint("reason_code IN ('spam', 'fraud', 'harassment', 'prohibited_content', 'other')"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reporter_id", "client_request_id"),
        sa.UniqueConstraint("reporter_id", "message_id"),
    )
    op.create_index("ix_message_reports_message_id", "message_reports", ["message_id"])
    op.create_index("ix_message_reports_reporter_id", "message_reports", ["reporter_id"])
    op.create_index("ix_message_reports_reported_user_id", "message_reports", ["reported_user_id"])
    op.create_index("ix_message_reports_status", "message_reports", ["status"])


def downgrade() -> None:
    op.drop_table("message_reports")
