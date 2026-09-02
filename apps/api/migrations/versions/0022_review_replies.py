"""Immutable reviewee replies

Revision ID: 0022
Revises: 0021
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_reviews_id_reviewee", "reviews", ["id", "reviewee_id"]
    )
    op.create_table(
        "review_replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["review_id", "author_id"],
            ["reviews.id", "reviews.reviewee_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id"),
    )
    op.create_index("ix_review_replies_author_id", "review_replies", ["author_id"])
    op.create_index("ix_review_replies_review_id", "review_replies", ["review_id"])
    op.execute("""
        CREATE FUNCTION prevent_review_reply_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'review replies are immutable';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER review_replies_immutable
        BEFORE UPDATE ON review_replies
        FOR EACH ROW EXECUTE FUNCTION prevent_review_reply_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER review_replies_immutable ON review_replies")
    op.execute("DROP FUNCTION prevent_review_reply_mutation")
    op.drop_index("ix_review_replies_review_id", table_name="review_replies")
    op.drop_index("ix_review_replies_author_id", table_name="review_replies")
    op.drop_table("review_replies")
    op.drop_constraint("uq_reviews_id_reviewee", "reviews", type_="unique")
