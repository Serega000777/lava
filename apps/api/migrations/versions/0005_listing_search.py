"""listing search indexes

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_listings_title_trgm ON listings USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_listings_description_trgm ON listings USING gin (description gin_trgm_ops)"
    )
    op.create_index(
        "ix_listings_active_discovery",
        "listings",
        ["category_id", "city", "created_at"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_listings_active_discovery", table_name="listings")
    op.drop_index("ix_listings_description_trgm", table_name="listings")
    op.drop_index("ix_listings_title_trgm", table_name="listings")
