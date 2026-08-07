import json
import sqlite3
from collections.abc import Sequence

from app.models.food import NUTRIENT_FIELDS


class FoodRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ensure_fts(self):
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS foods_fts USING fts5(
                name, brand, content='foods', content_rowid='id',
                tokenize='porter unicode61'
            );

            CREATE TRIGGER IF NOT EXISTS foods_ai AFTER INSERT ON foods BEGIN
                INSERT INTO foods_fts(rowid, name, brand)
                VALUES (new.id, new.name, new.brand);
            END;

            CREATE TRIGGER IF NOT EXISTS foods_ad AFTER DELETE ON foods BEGIN
                INSERT INTO foods_fts(foods_fts, rowid, name, brand)
                VALUES ('delete', old.id, old.name, old.brand);
            END;

            CREATE TRIGGER IF NOT EXISTS foods_au AFTER UPDATE ON foods BEGIN
                INSERT INTO foods_fts(foods_fts, rowid, name, brand)
                VALUES ('delete', old.id, old.name, old.brand);
                INSERT INTO foods_fts(rowid, name, brand)
                VALUES (new.id, new.name, new.brand);
            END;
        """)

    def create(
        self, *, source: str, name: str, owner_user_id: int | None = None, **kwargs
    ) -> int:
        other_fields = [
            "source_code",
            "is_private",
            "brand",
            "barcode",
            "image_url",
            "serving_quantity",
            "serving_unit",
            "serving_size_text",
            "ingredients_text",
            "allergens_tags",
            "dietary_tags",
            "categories_tags",
            "labels_tags",
            "countries_tags",
            "nutriscore_grade",
            "nova_group",
            "product_quantity",
            "product_quantity_unit",
            "base_quantity",
            "base_unit",
            "density_g_per_ml",
        ]
        all_fields = other_fields + list(NUTRIENT_FIELDS)
        fields = ["source", "name", "owner_user_id"]
        values = [source, name, owner_user_id]
        for f in all_fields:
            if f in kwargs:
                fields.append(f)
                values.append(
                    json.dumps(kwargs[f]) if f.endswith("_tags") else kwargs[f]
                )
        placeholders = ", ".join(["?"] * len(values))
        cols = ", ".join(fields)
        cur = self.conn.execute(
            f"INSERT INTO foods ({cols}) VALUES ({placeholders})", values
        )
        self.conn.commit()
        return cur.lastrowid

    def create_no_commit(self, **kwargs) -> int:
        """Same as create() but without committing — caller manages transactions for bulk imports."""
        source = kwargs.pop("source")
        name = kwargs.pop("name")
        other_fields = [
            "source_code",
            "is_private",
            "brand",
            "barcode",
            "image_url",
            "serving_quantity",
            "serving_unit",
            "serving_size_text",
            "ingredients_text",
            "allergens_tags",
            "dietary_tags",
            "categories_tags",
            "labels_tags",
            "countries_tags",
            "nutriscore_grade",
            "nova_group",
            "product_quantity",
            "product_quantity_unit",
            "base_quantity",
            "base_unit",
            "density_g_per_ml",
        ]
        all_fields = other_fields + list(NUTRIENT_FIELDS)
        fields = ["source", "name"]
        values = [source, name]
        for f in all_fields:
            if f in kwargs:
                fields.append(f)
                values.append(
                    json.dumps(kwargs[f]) if f.endswith("_tags") else kwargs[f]
                )
        placeholders = ", ".join(["?"] * len(values))
        cols = ", ".join(fields)
        conflict_clause = ""
        if "source_code" in fields:
            updates = ", ".join(
                f"{field} = excluded.{field}"
                for field in fields
                if field not in ("source", "source_code")
            )
            conflict_clause = (
                " ON CONFLICT(source, source_code) WHERE source_code IS NOT NULL"
                f" DO UPDATE SET {updates}, updated_at = datetime('now')"
            )
        cur = self.conn.execute(
            f"INSERT INTO foods ({cols}) VALUES ({placeholders})"
            f"{conflict_clause} RETURNING id",
            values,
        )
        return cur.fetchone()[0]

    def get(self, food_id: int, *, user_id: int | None = None) -> dict | None:
        query = "SELECT * FROM foods WHERE id = ?"
        values: list[int] = [food_id]
        if user_id is not None:
            query += " AND (owner_user_id IS NULL OR owner_user_id = ?)"
            values.append(user_id)
        row = self.conn.execute(query, values).fetchone()
        return self._deserialize(row)

    def get_by_barcode(
        self, barcode: str, *, user_id: int | None = None
    ) -> dict | None:
        query = "SELECT * FROM foods WHERE barcode = ?"
        values: list[int | str] = [barcode]
        if user_id is not None:
            query += " AND (owner_user_id IS NULL OR owner_user_id = ?)"
            values.append(user_id)
        row = self.conn.execute(query, values).fetchone()
        return self._deserialize(row)

    @staticmethod
    def build_fts_query(query: str) -> str:
        """Turn user input into an FTS5 prefix query, or "" if it has no terms.

        Each term is wrapped in an FTS5 string literal so that punctuation a
        user can reasonably type is matched literally instead of being parsed
        as query syntax. Unquoted, "Ben & Jerry's" and "AC/DC" and "Milk 2%"
        all raised `fts5: syntax error` and failed the request, "Yoghurt-Greek"
        raised `no such column: greek`, and a bare `AND` was read as an
        operator.

        NUL is stripped rather than quoted: SQLite's FTS5 parser is written
        against NUL-terminated C strings, so an embedded NUL truncates the
        expression mid-literal and the unclosed quote raises
        `fts5: unterminated string`.
        """
        cleaned = query.replace("\x00", "")
        terms = [term.replace('"', '""') for term in cleaned.strip().split()]
        return " ".join(f'"{term}"*' for term in terms)

    def search(
        self,
        query: str,
        *,
        sources: Sequence[str] | None = None,
        user_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Full-text matches ordered by relevance, each carrying its bm25 score.

        Ordering here is text relevance only. Callers that care about source
        quality re-rank the rows using the `relevance` score, which is why it
        is returned rather than discarded.
        """
        fts_query = self.build_fts_query(query)
        if not fts_query:
            # An empty MATCH is itself a syntax error.
            return []
        filters = ""
        filter_values: list[object] = []
        if sources:
            placeholders = ", ".join(["?"] * len(sources))
            filters += f" AND f.source IN ({placeholders})"
            filter_values.extend(sources)
        if user_id is not None:
            filters += " AND (f.owner_user_id IS NULL OR f.owner_user_id = ?)"
            filter_values.append(user_id)
        rows = self.conn.execute(
            """SELECT f.*, bm25(foods_fts) AS relevance
               FROM foods_fts fts
               JOIN foods f ON f.id = fts.rowid
               WHERE foods_fts MATCH ?"""
            + filters
            + """
               ORDER BY rank
               LIMIT ? OFFSET ?""",
            (fts_query, *filter_values, limit, offset),
        ).fetchall()
        return [self._deserialize(r) for r in rows]

    def update(self, food_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for field in (
            "allergens_tags",
            "dietary_tags",
            "categories_tags",
            "labels_tags",
            "countries_tags",
        ):
            if field in kwargs and isinstance(kwargs[field], list):
                kwargs[field] = json.dumps(kwargs[field])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [food_id]
        self.conn.execute(
            f"UPDATE foods SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, food_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def list_sources(self) -> list[dict]:
        """Registered data sources with how many foods each contributes."""
        rows = self.conn.execute("""
            SELECT s.code, s.label, s.publisher, s.tier, s.data_method,
                   s.license, s.url, s.citation, s.dataset_version,
                   (SELECT COUNT(*) FROM foods f WHERE f.source = s.code) AS food_count
            FROM food_sources s
            ORDER BY s.tier, s.code
        """).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _deserialize(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        food = dict(row)
        food["is_private"] = bool(food["is_private"])
        for field in (
            "allergens_tags",
            "dietary_tags",
            "categories_tags",
            "labels_tags",
            "countries_tags",
        ):
            food[field] = json.loads(food[field])
        return food
