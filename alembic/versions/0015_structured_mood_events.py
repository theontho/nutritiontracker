"""Add structured measurement kinds and mood event data.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-07
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE event_types ADD COLUMN measurement_kind TEXT NOT NULL "
        "DEFAULT 'generic' CHECK(measurement_kind IN "
        "('generic', 'bristol_stool', 'urine_color', 'mood'))"
    )
    op.execute(
        "ALTER TABLE events ADD COLUMN mood TEXT "
        "CHECK(mood IS NULL OR json_valid(mood))"
    )
    op.execute("""
        UPDATE event_types
        SET measurement_kind = CASE
            WHEN lower(coalesce(unit, '')) LIKE '%bristol stool%' THEN 'bristol_stool'
            WHEN lower(coalesce(unit, '')) LIKE '%urine color%' THEN 'urine_color'
            WHEN lower(name) = 'mood' THEN 'mood'
            ELSE 'generic'
        END
    """)


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")
