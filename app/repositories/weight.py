import sqlite3


class WeightRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, *, user_id: int, date: str, weight_kg: float,
               notes: str | None = None) -> int:
        cur = self.conn.execute(
            """INSERT INTO weight_entries (user_id, date, weight_kg, notes)
               VALUES (?, ?, ?, ?)""",
            (user_id, date, weight_kg, notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, entry_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM weight_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_by_date_range(self, *, user_id: int, start: str, end: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM weight_entries
               WHERE user_id = ? AND date >= ? AND date <= ?
               ORDER BY date""",
            (user_id, start, end),
        ).fetchall()
        return [dict(r) for r in rows]

    def update(self, entry_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [entry_id]
        self.conn.execute(
            f"UPDATE weight_entries SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, entry_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM weight_entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cur.rowcount > 0
