"""Review disputes and immutable moderation decisions

Revision ID: 0023
Revises: 0022
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_disputes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opened_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "reason_code IN ('transaction_not_completed', 'abusive', "
            "'personal_data', 'fraudulent', 'other')"
        ),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["review_id", "opened_by"],
            ["reviews.id", "reviews.reviewee_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id"),
    )
    op.create_index("ix_review_disputes_review_id", "review_disputes", ["review_id"])
    op.create_index("ix_review_disputes_opened_by", "review_disputes", ["opened_by"])

    op.create_table(
        "review_moderation_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dispute_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("moderator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("outcome IN ('keep', 'exclude')"),
        sa.CheckConstraint(
            "reason_code IN ('complies', 'insufficient_evidence', 'abusive', "
            "'personal_data', 'fraudulent', 'transaction_not_completed', 'other')"
        ),
        sa.ForeignKeyConstraint(
            ["dispute_id"], ["review_disputes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["moderator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dispute_id"),
    )
    op.create_index(
        "ix_review_moderation_decisions_dispute_id",
        "review_moderation_decisions",
        ["dispute_id"],
    )
    op.create_index(
        "ix_review_moderation_decisions_moderator_id",
        "review_moderation_decisions",
        ["moderator_id"],
    )
    op.execute("""
        CREATE FUNCTION prevent_review_dispute_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'review disputes are append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER review_disputes_append_only
        BEFORE UPDATE ON review_disputes
        FOR EACH ROW EXECUTE FUNCTION prevent_review_dispute_mutation()
    """)
    op.execute("""
        CREATE TRIGGER review_moderation_decisions_append_only
        BEFORE UPDATE ON review_moderation_decisions
        FOR EACH ROW EXECUTE FUNCTION prevent_review_dispute_mutation()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER review_moderation_decisions_append_only "
        "ON review_moderation_decisions"
    )
    op.execute("DROP TRIGGER review_disputes_append_only ON review_disputes")
    op.execute("DROP FUNCTION prevent_review_dispute_mutation")
    op.drop_index(
        "ix_review_moderation_decisions_moderator_id",
        table_name="review_moderation_decisions",
    )
    op.drop_index(
        "ix_review_moderation_decisions_dispute_id",
        table_name="review_moderation_decisions",
    )
    op.drop_table("review_moderation_decisions")
    op.drop_index("ix_review_disputes_opened_by", table_name="review_disputes")
    op.drop_index("ix_review_disputes_review_id", table_name="review_disputes")
    op.drop_table("review_disputes")
