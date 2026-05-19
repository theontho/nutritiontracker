"""Initial schema — all tables as of v0.1.0.

Revision ID: 0001
Revises:
Create Date: 2026-05-19
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL CHECK(source IN ('custom','open_food_facts','food_data_central','recipe')),
            source_code TEXT,
            name TEXT NOT NULL,
            brand TEXT,
            barcode TEXT,
            image_url TEXT,
            serving_quantity REAL,
            serving_unit TEXT,
            serving_size_text TEXT,
            base_quantity REAL NOT NULL DEFAULT 100,
            base_unit TEXT NOT NULL DEFAULT 'g',
            density_g_per_ml REAL,
            calories_kcal REAL DEFAULT 0,
            protein_g REAL DEFAULT 0,
            carbs_g REAL DEFAULT 0,
            fat_g REAL DEFAULT 0,
            sugar_g REAL DEFAULT 0,
            saturated_fat_g REAL DEFAULT 0,
            fiber_g REAL DEFAULT 0,
            sodium_mg REAL DEFAULT 0,
            potassium_mg REAL DEFAULT 0,
            calcium_mg REAL DEFAULT 0,
            iron_mg REAL DEFAULT 0,
            magnesium_mg REAL DEFAULT 0,
            zinc_mg REAL DEFAULT 0,
            phosphorus_mg REAL DEFAULT 0,
            vitamin_a_ug REAL DEFAULT 0,
            vitamin_c_mg REAL DEFAULT 0,
            vitamin_d_ug REAL DEFAULT 0,
            vitamin_b6_mg REAL DEFAULT 0,
            vitamin_b12_ug REAL DEFAULT 0,
            niacin_mg REAL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast','lunch','dinner','snack')),
            food_id INTEGER NOT NULL REFERENCES foods(id),
            food_snapshot TEXT NOT NULL,
            amount REAL NOT NULL,
            unit TEXT NOT NULL,
            grams REAL NOT NULL,
            nutrients_total TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            name TEXT NOT NULL,
            servings REAL NOT NULL,
            total_weight_g REAL NOT NULL,
            ingredients TEXT NOT NULL,
            nutrients_per_100 TEXT NOT NULL,
            nutrients_per_serving TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS weight_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            body TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            mood_score INTEGER,
            stress_score INTEGER,
            sleep_quality INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS step_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            source TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            local_date TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            steps_total_today INTEGER NOT NULL,
            timezone TEXT NOT NULL,
            raw_payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            steps INTEGER NOT NULL,
            last_observed_at TEXT NOT NULL,
            anomaly_flag INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, date, source)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_foods_barcode ON foods(barcode)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_foods_source ON foods(source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_foods_source_code ON foods(source, source_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_diary_user_date ON diary_entries(user_id, date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_weight_user_date ON weight_entries(user_id, date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_journal_user_date ON journal_entries(user_id, date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_step_obs_user_date ON step_observations(user_id, local_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_daily_activity_user_date ON daily_activity(user_id, date)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS daily_activity")
    op.execute("DROP TABLE IF EXISTS step_observations")
    op.execute("DROP TABLE IF EXISTS journal_entries")
    op.execute("DROP TABLE IF EXISTS weight_entries")
    op.execute("DROP TABLE IF EXISTS recipes")
    op.execute("DROP TABLE IF EXISTS diary_entries")
    op.execute("DROP TABLE IF EXISTS foods")
