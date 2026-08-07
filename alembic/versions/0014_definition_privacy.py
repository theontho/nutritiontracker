"""Add first-class privacy to reusable definitions.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-07
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("event_types", "foods", "recipes", "favorite_meals"):
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN is_private INTEGER NOT NULL DEFAULT 0 "
            "CHECK(is_private IN (0, 1))"
        )

    # Preserve privacy choices encoded before the structured field existed.
    op.execute("""
        UPDATE event_types
        SET is_private = 1
        WHERE lower(ltrim(coalesce(notes, ''))) LIKE 'private%'
           OR lower(ltrim(coalesce(notes, ''))) LIKE '[private]%'
           OR lower(name) IN (
               'pee', 'poop', 'urine', 'urination', 'bowel movement',
               'bowel movements', 'stool', 'stools', 'defecation'
           )
           OR lower(coalesce(unit, '')) LIKE '%bristol stool%'
           OR lower(coalesce(unit, '')) LIKE '%urine color%'
    """)


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")
