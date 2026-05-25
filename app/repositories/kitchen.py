import json
import sqlite3


class KitchenRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _inventory_row(self, row) -> dict | None:
        return dict(row) if row else None

    def _meal_row(self, row) -> dict | None:
        if not row:
            return None
        meal = dict(row)
        meal["tags"] = json.loads(meal["tags"])
        meal["ingredients"] = self.list_meal_ingredients(meal["id"])
        return meal

    def _shopping_row(self, row) -> dict | None:
        if not row:
            return None
        item = dict(row)
        item["checked"] = bool(item["checked"])
        item["linked_meal_ids"] = json.loads(item["linked_meal_ids"])
        return item

    def upsert_inventory_item(
        self,
        *,
        user_id: int,
        display_name: str,
        canonical_name: str,
        status: str,
        location: str | None = None,
        category: str | None = None,
        notes: str | None = None,
    ) -> dict:
        self.conn.execute(
            """INSERT INTO kitchen_inventory_items
               (user_id, canonical_name, display_name, status, location, category, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, canonical_name) DO UPDATE SET
                 display_name = excluded.display_name,
                 status = excluded.status,
                 location = excluded.location,
                 category = excluded.category,
                 notes = excluded.notes,
                 last_confirmed_at = datetime('now'),
                 updated_at = datetime('now')""",
            (user_id, canonical_name, display_name, status, location, category, notes),
        )
        self.conn.commit()
        return self.get_inventory_item(user_id=user_id, canonical_name=canonical_name)

    def get_inventory_item(self, *, user_id: int, canonical_name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM kitchen_inventory_items WHERE user_id = ? AND canonical_name = ?",
            (user_id, canonical_name),
        ).fetchone()
        return self._inventory_row(row)

    def list_inventory(
        self,
        *,
        user_id: int,
        status: str | None = None,
        location: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> list[dict]:
        clauses = ["user_id = ?"]
        values: list = [user_id]
        if status:
            clauses.append("status = ?")
            values.append(status)
        if location:
            clauses.append("location = ?")
            values.append(location)
        if category:
            clauses.append("category = ?")
            values.append(category)
        if query:
            clauses.append("LOWER(display_name) LIKE '%' || LOWER(?) || '%'")
            values.append(query)
        rows = self.conn.execute(
            f"""SELECT * FROM kitchen_inventory_items
                WHERE {' AND '.join(clauses)}
                ORDER BY status = 'use_soon' DESC, display_name ASC""",
            values,
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_inventory_item(self, *, user_id: int, item_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM kitchen_inventory_items WHERE user_id = ? AND id = ?",
            (user_id, item_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def create_favorite_meal(
        self,
        *,
        user_id: int,
        name: str,
        tags: list[str],
        ingredients: list[dict],
        prep_time_minutes: int | None = None,
        effort: str | None = None,
        favorite_score: int = 0,
        nutrition_template_id: int | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """INSERT INTO favorite_meals
               (user_id, name, tags, prep_time_minutes, effort, favorite_score, nutrition_template_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                name,
                json.dumps(tags),
                prep_time_minutes,
                effort,
                favorite_score,
                nutrition_template_id,
            ),
        )
        meal_id = cur.lastrowid
        for ingredient in ingredients:
            self.conn.execute(
                """INSERT INTO favorite_meal_ingredients
                   (meal_id, canonical_name, display_name, role, category)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    meal_id,
                    ingredient["canonical_name"],
                    ingredient["display_name"],
                    ingredient["role"],
                    ingredient.get("category"),
                ),
            )
        self.conn.commit()
        return self.get_favorite_meal(user_id=user_id, meal_id=meal_id)

    def get_favorite_meal(self, *, user_id: int, meal_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM favorite_meals WHERE user_id = ? AND id = ?",
            (user_id, meal_id),
        ).fetchone()
        return self._meal_row(row)

    def list_favorite_meals(self, *, user_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM favorite_meals WHERE user_id = ? ORDER BY favorite_score DESC, name ASC",
            (user_id,),
        ).fetchall()
        return [self._meal_row(row) for row in rows]

    def list_meal_ingredients(self, meal_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM favorite_meal_ingredients WHERE meal_id = ? ORDER BY role, display_name",
            (meal_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_meal_made(
        self, *, user_id: int, meal_id: int, made_at: str
    ) -> dict | None:
        self.conn.execute(
            """UPDATE favorite_meals
               SET last_made_at = ?, times_made = times_made + 1, updated_at = datetime('now')
               WHERE user_id = ? AND id = ?""",
            (made_at, user_id, meal_id),
        )
        self.conn.commit()
        return self.get_favorite_meal(user_id=user_id, meal_id=meal_id)

    def upsert_shopping_list_item(
        self,
        *,
        user_id: int,
        display_name: str,
        canonical_name: str,
        source: str,
        linked_meal_ids: list[int],
        notes: str | None = None,
    ) -> dict:
        self.conn.execute(
            """INSERT INTO shopping_list_items
               (user_id, canonical_name, display_name, source, linked_meal_ids, notes)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, canonical_name) DO UPDATE SET
                 display_name = excluded.display_name,
                 source = excluded.source,
                 linked_meal_ids = excluded.linked_meal_ids,
                 notes = excluded.notes,
                 checked = 0,
                 updated_at = datetime('now')""",
            (
                user_id,
                canonical_name,
                display_name,
                source,
                json.dumps(linked_meal_ids),
                notes,
            ),
        )
        self.conn.commit()
        return self.get_shopping_list_item(
            user_id=user_id, canonical_name=canonical_name
        )

    def get_shopping_list_item(
        self, *, user_id: int, canonical_name: str
    ) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM shopping_list_items WHERE user_id = ? AND canonical_name = ?",
            (user_id, canonical_name),
        ).fetchone()
        return self._shopping_row(row)

    def list_shopping_items(
        self, *, user_id: int, checked: bool | None = None
    ) -> list[dict]:
        if checked is None:
            rows = self.conn.execute(
                "SELECT * FROM shopping_list_items WHERE user_id = ? ORDER BY checked ASC, display_name ASC",
                (user_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM shopping_list_items WHERE user_id = ? AND checked = ? ORDER BY display_name ASC",
                (user_id, int(checked)),
            ).fetchall()
        return [self._shopping_row(row) for row in rows]

    def set_shopping_item_checked(
        self, *, user_id: int, item_id: int, checked: bool
    ) -> dict | None:
        self.conn.execute(
            """UPDATE shopping_list_items
               SET checked = ?, updated_at = datetime('now')
               WHERE user_id = ? AND id = ?""",
            (int(checked), user_id, item_id),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM shopping_list_items WHERE user_id = ? AND id = ?",
            (user_id, item_id),
        ).fetchone()
        return self._shopping_row(row)
