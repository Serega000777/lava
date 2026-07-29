"""Verification audit immutability

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION prevent_verification_decision_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'verification decisions are append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER verification_decisions_append_only
        BEFORE UPDATE OR DELETE ON verification_decisions
        FOR EACH ROW EXECUTE FUNCTION prevent_verification_decision_mutation()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER verification_decisions_append_only ON verification_decisions"
    )
    op.execute("DROP FUNCTION prevent_verification_decision_mutation")
