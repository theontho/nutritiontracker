import json
import sqlite3


class ActivityRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_observation(self, *, user_id: int, source: str, observed_at: str,
                           local_date: str, period_start: str, period_end: str,
                           steps_total_today: int, timezone: str,
                           raw_payload: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO step_observations
               (user_id, source, observed_at, local_date, period_start, period_end,
                steps_total_today, timezone, raw_payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, source, observed_at, local_date, period_start, period_end,
             steps_total_today, timezone, json.dumps(raw_payload)),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_daily(self, *, user_id: int, date: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM daily_activity WHERE user_id = ? AND date = ? ORDER BY last_observed_at DESC LIMIT 1",
            (user_id, date),
        ).fetchone()
        return dict(row) if row else None

    def upsert_daily(self, *, user_id: int, date: str, source: str,
                     steps: int, last_observed_at: str, anomaly_flag: bool) -> None:
        self.conn.execute(
            """INSERT INTO daily_activity (user_id, date, source, steps, last_observed_at, anomaly_flag)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, date, source) DO UPDATE SET
                   steps = excluded.steps,
                   last_observed_at = excluded.last_observed_at,
                   anomaly_flag = excluded.anomaly_flag,
                   updated_at = datetime('now')""",
            (user_id, date, source, steps, last_observed_at, int(anomaly_flag)),
        )
        self.conn.commit()

    def list_by_date_range(self, *, user_id: int, start: str, end: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM daily_activity WHERE user_id = ? AND date >= ? AND date <= ?
               ORDER BY date""",
            (user_id, start, end),
        ).fetchall()
        return [dict(r) for r in rows]
