"""Record whether diary portions were measured or estimated.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-04
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE diary_entries ADD COLUMN amount_method TEXT NOT NULL "
        "DEFAULT 'unspecified' CHECK(amount_method IN "
        "('measured','estimated','unspecified'))"
    )


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")
