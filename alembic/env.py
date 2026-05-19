"""Alembic environment — raw SQL migrations, no SQLAlchemy ORM.

Migrations use op.execute() with raw SQL. The DB path is read from NT_DB_PATH
env var (same as the app), falling back to alembic.ini's sqlalchemy.url.
"""
import os

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config

# Allow NT_DB_PATH to override the ini URL so we use the same DB as the app.
db_path = os.environ.get("NT_DB_PATH", "data/nutrition.db")
db_url = f"sqlite:///{db_path}"
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
