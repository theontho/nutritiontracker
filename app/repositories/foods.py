import sqlite3


class FoodRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure_fts(self) -> None:
        """Create the FTS5 virtual table for full-text search on foods if it doesn't exist."""
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS foods_fts USING fts5(
                name,
                brand,
                content='foods',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS foods_ai AFTER INSERT ON foods BEGIN
                INSERT INTO foods_fts(rowid, name, brand) VALUES (new.id, new.name, new.brand);
            END;

            CREATE TRIGGER IF NOT EXISTS foods_au AFTER UPDATE ON foods BEGIN
                INSERT INTO foods_fts(foods_fts, rowid, name, brand) VALUES ('delete', old.id, old.name, old.brand);
                INSERT INTO foods_fts(rowid, name, brand) VALUES (new.id, new.name, new.brand);
            END;

            CREATE TRIGGER IF NOT EXISTS foods_ad AFTER DELETE ON foods BEGIN
                INSERT INTO foods_fts(foods_fts, rowid, name, brand) VALUES ('delete', old.id, old.name, old.brand);
            END;
        """)
