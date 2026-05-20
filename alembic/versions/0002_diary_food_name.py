"""Add food_name column to diary_entries.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-20
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE diary_entries ADD COLUMN food_name TEXT NOT NULL DEFAULT ''")
    op.execute("UPDATE diary_entries SET food_name = json_extract(food_snapshot, '$.name') WHERE food_name = ''")
    op.execute("CREATE INDEX IF NOT EXISTS idx_diary_food_name ON diary_entries(user_id, food_name)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_diary_food_name")
    # SQLite does not support DROP COLUMN before 3.35 — leave column in place on downgrade
