"""Persist the food-data method for each source.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-04
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE food_sources ADD COLUMN data_method TEXT NOT NULL "
        "DEFAULT 'unspecified' CHECK(data_method IN "
        "('database-matched','label-derived','recipe-calculated',"
        "'user-entered','unspecified'))"
    )


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")
