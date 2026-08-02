"""Add per-user identities and custom-food ownership.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-01
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token_hash TEXT UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    op.execute("INSERT INTO users (id, name) VALUES (1, 'Default user')")
    op.execute("ALTER TABLE foods ADD COLUMN owner_user_id INTEGER REFERENCES users(id)")
    op.execute("UPDATE foods SET owner_user_id = 1 WHERE source = 'custom'")
    op.execute("CREATE INDEX idx_foods_owner ON foods(owner_user_id)")


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")
