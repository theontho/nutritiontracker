import json
import sqlite3


class DiaryRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, *, user_id: int, date: str, meal_type: str,
               food_id: int, food_snapshot: dict, food_name: str = "",
               amount: float, unit: str, grams: float, nutrients_total: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO diary_entries
               (user_id, date, meal_type, food_id, food_snapshot, food_name, amount, unit, grams, nutrients_total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, date, meal_type, food_id,
             json.dumps(food_snapshot), food_name, amount, unit, grams,
             json.dumps(nutrients_total)),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, entry_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM diary_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["food_snapshot"] = json.loads(d["food_snapshot"])
        d["nutrients_total"] = json.loads(d["nutrients_total"])
        return d

    def list_by_date(self, *, user_id: int, date: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM diary_entries WHERE user_id = ? AND date = ? ORDER BY created_at",
            (user_id, date),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["food_snapshot"] = json.loads(d["food_snapshot"])
            d["nutrients_total"] = json.loads(d["nutrients_total"])
            results.append(d)
        return results

    def search_by_food_name(self, *, user_id: int, query: str) -> list[dict]:
        """Return all diary entries whose food_name contains the query string (case-insensitive), newest first."""
        rows = self.conn.execute(
            """SELECT * FROM diary_entries
               WHERE user_id = ? AND LOWER(food_name) LIKE '%' || LOWER(?) || '%'
               ORDER BY date DESC, created_at DESC""",
            (user_id, query),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["food_snapshot"] = json.loads(d["food_snapshot"])
            d["nutrients_total"] = json.loads(d["nutrients_total"])
            results.append(d)
        return results

    def update(self, entry_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for k in ("food_snapshot", "nutrients_total"):
            if k in kwargs and isinstance(kwargs[k], dict):
                kwargs[k] = json.dumps(kwargs[k])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [entry_id]
        self.conn.execute(
            f"UPDATE diary_entries SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, entry_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cur.rowcount > 0
