"""Verification decisions

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "verification_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("previous_level", sa.SmallInteger(), nullable=False),
        sa.Column("new_level", sa.SmallInteger(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("previous_level BETWEEN 0 AND 4"),
        sa.CheckConstraint("new_level BETWEEN 0 AND 4"),
        sa.CheckConstraint("previous_level <> new_level"),
        sa.CheckConstraint("source IN ('phone_otp', 'admin_review')"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_decisions_user_id", "verification_decisions", ["user_id"])


def downgrade() -> None:
    op.drop_table("verification_decisions")
