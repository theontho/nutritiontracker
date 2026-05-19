import json
import sqlite3


class JournalRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, *, user_id: int, date: str, body: str, tags: list,
               mood_score: int | None, stress_score: int | None,
               sleep_quality: int | None) -> int:
        cur = self.conn.execute(
            """INSERT INTO journal_entries
               (user_id, date, body, tags, mood_score, stress_score, sleep_quality)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, date, body, json.dumps(tags), mood_score, stress_score, sleep_quality),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, entry_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["tags"] = json.loads(d["tags"])
        return d

    def list_by_date(self, *, user_id: int, date: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM journal_entries WHERE user_id = ? AND date = ? ORDER BY created_at",
            (user_id, date),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["tags"] = json.loads(d["tags"])
            result.append(d)
        return result

    def list_by_date_range(self, *, user_id: int, start: str, end: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM journal_entries WHERE user_id = ? AND date >= ? AND date <= ?
               ORDER BY date, created_at""",
            (user_id, start, end),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["tags"] = json.loads(d["tags"])
            result.append(d)
        return result

    def update(self, entry_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        if "tags" in kwargs and isinstance(kwargs["tags"], list):
            kwargs["tags"] = json.dumps(kwargs["tags"])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [entry_id]
        cur = self.conn.execute(
            f"UPDATE journal_entries SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, entry_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cur.rowcount > 0
