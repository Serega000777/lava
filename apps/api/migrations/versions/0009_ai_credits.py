"""AI generations and immutable credits

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("ai_generated_fields", sa.JSON(), server_default="[]", nullable=False),
    )
    op.create_table(
        "credit_accounts",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("balance >= 0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "credit_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('welcome_grant', 'ai_text_debit', 'ai_text_refund')"),
        sa.CheckConstraint("amount <> 0"),
        sa.CheckConstraint("balance_after >= 0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "kind", "reference_id"),
    )
    op.create_index("ix_credit_ledger_user_created", "credit_ledger", ["user_id", "created_at"])
    op.execute("""
        CREATE FUNCTION prevent_credit_ledger_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'credit ledger is append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER credit_ledger_append_only
        BEFORE UPDATE OR DELETE ON credit_ledger
        FOR EACH ROW EXECUTE FUNCTION prevent_credit_ledger_mutation()
    """)
    op.create_table(
        "ai_generations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("credit_cost", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'completed', 'failed', 'accepted')"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "client_request_id"),
    )
    op.create_index("ix_ai_generations_user_created", "ai_generations", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("ai_generations")
    op.execute("DROP TRIGGER credit_ledger_append_only ON credit_ledger")
    op.execute("DROP FUNCTION prevent_credit_ledger_mutation")
    op.drop_table("credit_ledger")
    op.drop_table("credit_accounts")
    op.drop_column("listings", "ai_generated_fields")
