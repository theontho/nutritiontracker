"""Mark inferred dimensions on migrated mood events.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-07
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE events
        SET mood = json_set(mood, '$.dimension_source', 'legacy_inferred')
        WHERE mood IS NOT NULL
          AND json_extract(mood, '$.version') = 2
          AND json_extract(mood, '$.dimension_source') IS NULL
    """)


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")
