"""Listing media metadata

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listing_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("position BETWEEN 0 AND 9"),
        sa.CheckConstraint("size_bytes > 0"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", "position"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_listing_media_listing_id", "listing_media", ["listing_id"])


def downgrade() -> None:
    op.drop_table("listing_media")
