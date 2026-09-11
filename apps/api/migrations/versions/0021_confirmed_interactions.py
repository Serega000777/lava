"""Explicit two-party interaction confirmation for reviews

Revision ID: 0021
Revises: 0020
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("buyer_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seller_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(completed_at IS NOT NULL) = "
            "(buyer_confirmed_at IS NOT NULL AND seller_confirmed_at IS NOT NULL)",
            name="ck_interactions_completed_by_both",
        ),
        sa.CheckConstraint(
            "(buyer_confirmed_at IS NULL AND seller_confirmed_at IS NULL) "
            "OR contacted_at IS NOT NULL",
            name="ck_interactions_confirmation_requires_contact",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id"),
        sa.UniqueConstraint(
            "id", "conversation_id", name="uq_interactions_id_conversation"
        ),
    )
    op.execute("""
        INSERT INTO interactions (
            id,
            conversation_id,
            contacted_at,
            buyer_confirmed_at,
            seller_confirmed_at,
            completed_at
        )
        SELECT
            gen_random_uuid(),
            conversations.id,
            MIN(messages.created_at),
            CASE WHEN COUNT(reviews.id) > 0 THEN MIN(reviews.created_at) END,
            CASE WHEN COUNT(reviews.id) > 0 THEN MIN(reviews.created_at) END,
            CASE WHEN COUNT(reviews.id) > 0 THEN MIN(reviews.created_at) END
        FROM conversations
        LEFT JOIN messages ON messages.conversation_id = conversations.id
        LEFT JOIN reviews ON reviews.conversation_id = conversations.id
        GROUP BY conversations.id
    """)

    op.add_column(
        "reviews",
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("""
        UPDATE reviews
        SET interaction_id = interactions.id
        FROM interactions
        WHERE interactions.conversation_id = reviews.conversation_id
    """)
    op.alter_column("reviews", "interaction_id", nullable=False)
    op.create_foreign_key(
        "fk_reviews_interaction_conversation",
        "reviews",
        "interactions",
        ["interaction_id", "conversation_id"],
        ["id", "conversation_id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_reviews_interaction_id", "reviews", ["interaction_id"])

    op.execute("""
        CREATE FUNCTION prevent_interaction_confirmation_mutation() RETURNS trigger AS $$
        BEGIN
            IF OLD.contacted_at IS NOT NULL
               AND NEW.contacted_at IS DISTINCT FROM OLD.contacted_at THEN
                RAISE EXCEPTION 'interaction contact time is immutable';
            END IF;
            IF OLD.buyer_confirmed_at IS NOT NULL
               AND NEW.buyer_confirmed_at IS DISTINCT FROM OLD.buyer_confirmed_at THEN
                RAISE EXCEPTION 'buyer confirmation is immutable';
            END IF;
            IF OLD.seller_confirmed_at IS NOT NULL
               AND NEW.seller_confirmed_at IS DISTINCT FROM OLD.seller_confirmed_at THEN
                RAISE EXCEPTION 'seller confirmation is immutable';
            END IF;
            IF OLD.completed_at IS NOT NULL
               AND NEW.completed_at IS DISTINCT FROM OLD.completed_at THEN
                RAISE EXCEPTION 'interaction completion is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER interactions_confirmation_immutable
        BEFORE UPDATE ON interactions
        FOR EACH ROW EXECUTE FUNCTION prevent_interaction_confirmation_mutation()
    """)
    op.execute("""
        CREATE FUNCTION prevent_review_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'reviews are immutable';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER reviews_immutable
        BEFORE UPDATE ON reviews
        FOR EACH ROW EXECUTE FUNCTION prevent_review_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER reviews_immutable ON reviews")
    op.execute("DROP FUNCTION prevent_review_mutation")
    op.execute("DROP TRIGGER interactions_confirmation_immutable ON interactions")
    op.execute("DROP FUNCTION prevent_interaction_confirmation_mutation")
    op.drop_index("ix_reviews_interaction_id", table_name="reviews")
    op.drop_constraint(
        "fk_reviews_interaction_conversation", "reviews", type_="foreignkey"
    )
    op.drop_column("reviews", "interaction_id")
    op.drop_table("interactions")
