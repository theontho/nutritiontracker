"""Refresh diary and recipe nutrient snapshots from the current food catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import settings
from app.database import get_connection
from app.services.diary import (
    SNAPSHOT_CATALOG_VERSION_KEY,
    build_food_snapshot,
    compute_entry_nutrients,
)
from app.services.recipe_nutrition import compute_recipe_nutrients


def recompute(db_path: Path) -> tuple[int, int]:
    connection = get_connection(db_path)
    diary_count = 0
    recipe_count = 0
    try:
        connection.execute("BEGIN IMMEDIATE")
        diary_rows = connection.execute(
            """
            SELECT d.id AS entry_id, d.grams, d.food_snapshot AS saved_food_snapshot, f.*
            FROM diary_entries d
            JOIN foods f ON f.id = d.food_id
            ORDER BY d.id
            """
        ).fetchall()
        for row in diary_rows:
            food = dict(row)
            entry_id = int(food.pop("entry_id"))
            grams = float(food.pop("grams"))
            saved_snapshot = json.loads(str(food.pop("saved_food_snapshot")))
            if not isinstance(saved_snapshot, dict):
                raise ValueError(
                    f"Diary entry {entry_id} has a malformed food snapshot"
                )
            snapshot = build_food_snapshot(food)
            if saved_snapshot.get(SNAPSHOT_CATALOG_VERSION_KEY) == snapshot.get(
                SNAPSHOT_CATALOG_VERSION_KEY
            ):
                continue
            nutrients = compute_entry_nutrients(food, grams)
            connection.execute(
                """
                UPDATE diary_entries
                SET food_snapshot = ?, food_name = ?, nutrients_total = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    json.dumps(snapshot, separators=(",", ":")),
                    food["name"],
                    json.dumps(nutrients, separators=(",", ":")),
                    entry_id,
                ),
            )
            diary_count += 1

        recipe_rows = connection.execute(
            "SELECT id, servings, total_weight_g, ingredients FROM recipes ORDER BY id"
        ).fetchall()
        for recipe in recipe_rows:
            ingredients = json.loads(str(recipe["ingredients"]))
            changed = False
            for ingredient in ingredients:
                food_row = connection.execute(
                    "SELECT * FROM foods WHERE id = ?", (ingredient["food_id"],)
                ).fetchone()
                if food_row is None:
                    raise RuntimeError(
                        f"Recipe {recipe['id']} references missing food "
                        f"{ingredient['food_id']}"
                    )
                snapshot = build_food_snapshot(dict(food_row))
                saved_snapshot = ingredient.get("food_snapshot")
                saved_version = (
                    saved_snapshot.get(SNAPSHOT_CATALOG_VERSION_KEY)
                    if isinstance(saved_snapshot, dict)
                    else None
                )
                if saved_version != snapshot[SNAPSHOT_CATALOG_VERSION_KEY]:
                    ingredient["food_snapshot"] = snapshot
                    changed = True
            if not changed:
                continue
            per_100, per_serving = compute_recipe_nutrients(
                ingredients,
                float(recipe["total_weight_g"]),
                float(recipe["servings"]),
            )
            connection.execute(
                """
                UPDATE recipes
                SET ingredients = ?, nutrients_per_100 = ?,
                    nutrients_per_serving = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    json.dumps(ingredients, separators=(",", ":")),
                    json.dumps(per_100, separators=(",", ":")),
                    json.dumps(per_serving, separators=(",", ":")),
                    recipe["id"],
                ),
            )
            recipe_count += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return diary_count, recipe_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute saved diary and recipe nutrients from current foods."
    )
    parser.add_argument("--db", type=Path, default=settings.db_path)
    args = parser.parse_args()
    diary_count, recipe_count = recompute(args.db)
    print(f"Recomputed {diary_count} diary entries and {recipe_count} recipes.")


if __name__ == "__main__":
    main()
