import json
import sqlite3


class RecipeRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, *, user_id: int, name: str, servings: float,
               total_weight_g: float, ingredients: list[dict],
               nutrients_per_100: dict, nutrients_per_serving: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO recipes
               (user_id, name, servings, total_weight_g, ingredients,
                nutrients_per_100, nutrients_per_serving)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, servings, total_weight_g,
             json.dumps(ingredients), json.dumps(nutrients_per_100),
             json.dumps(nutrients_per_serving)),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, recipe_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["ingredients"] = json.loads(d["ingredients"])
        d["nutrients_per_100"] = json.loads(d["nutrients_per_100"])
        d["nutrients_per_serving"] = json.loads(d["nutrients_per_serving"])
        return d

    def list_all(self, *, user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM recipes WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["ingredients"] = json.loads(d["ingredients"])
            d["nutrients_per_100"] = json.loads(d["nutrients_per_100"])
            d["nutrients_per_serving"] = json.loads(d["nutrients_per_serving"])
            results.append(d)
        return results

    def update(self, recipe_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        for k in ("ingredients", "nutrients_per_100", "nutrients_per_serving"):
            if k in kwargs and isinstance(kwargs[k], (dict, list)):
                kwargs[k] = json.dumps(kwargs[k])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [recipe_id]
        self.conn.execute(
            f"UPDATE recipes SET {sets}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return True

    def delete(self, recipe_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        self.conn.commit()
        return cur.rowcount > 0
