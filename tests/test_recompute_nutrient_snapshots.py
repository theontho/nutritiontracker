import json
import sqlite3
from pathlib import Path

import pytest

from app.database import init_schema
from scripts.recompute_nutrient_snapshots import recompute


def _food(connection, *, source, name, categories, beta_carotene):
    return connection.execute(
        """
        INSERT INTO foods
            (source, name, categories_tags, calories_kcal, beta_carotene_ug)
        VALUES (?, ?, ?, 100, ?)
        """,
        (source, name, json.dumps(categories), beta_carotene),
    ).lastrowid


def _entry(connection, food_id, *, grams):
    connection.execute(
        """
        INSERT INTO diary_entries
            (date, meal_type, food_id, food_snapshot, food_name, amount, unit,
             grams, nutrients_total)
        VALUES ('2026-08-03', 'snack', ?, '{}', 'Stale name', ?, 'g', ?, '{}')
        """,
        (food_id, grams, grams),
    )


def test_recomputes_all_item_sources_and_recipe_snapshots(tmp_path):
    path = tmp_path / "nutrition.db"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    init_schema(connection)
    food = _food(
        connection,
        source="usda_sr_legacy",
        name="Carrots, raw",
        categories=[],
        beta_carotene=8280.0,
    )
    supplement = _food(
        connection,
        source="custom",
        name="Carotene supplement",
        categories=["supplement"],
        beta_carotene=2500.0,
    )
    medication = _food(
        connection,
        source="custom",
        name="Medication",
        categories=["medication"],
        beta_carotene=10.0,
    )
    _entry(connection, food, grams=220.0)
    _entry(connection, supplement, grams=2.0)
    _entry(connection, medication, grams=1.0)
    connection.execute(
        """
        INSERT INTO recipes
            (name, servings, total_weight_g, ingredients,
             nutrients_per_100, nutrients_per_serving)
        VALUES ('Carrot dish', 2, 220, ?, '{}', '{}')
        """,
        (
            json.dumps(
                [
                    {
                        "food_id": food,
                        "amount": 220.0,
                        "unit": "g",
                        "grams": 220.0,
                        "food_snapshot": {},
                    }
                ]
            ),
        ),
    )
    connection.commit()
    connection.close()

    assert recompute(path) == (3, 1)

    check = sqlite3.connect(path)
    check.row_factory = sqlite3.Row
    entries = check.execute(
        "SELECT food_name, nutrients_total FROM diary_entries ORDER BY id"
    ).fetchall()
    recipe = check.execute(
        "SELECT ingredients, nutrients_per_serving FROM recipes"
    ).fetchone()
    check.close()
    assert [entry["food_name"] for entry in entries] == [
        "Carrots, raw",
        "Carotene supplement",
        "Medication",
    ]
    assert json.loads(entries[0]["nutrients_total"])["beta_carotene_ug"] == (
        pytest.approx(18_216.0)
    )
    assert json.loads(entries[1]["nutrients_total"])["beta_carotene_ug"] == (
        pytest.approx(50.0)
    )
    ingredients = json.loads(recipe["ingredients"])
    assert ingredients[0]["food_snapshot"]["beta_carotene_ug"] == 8280.0
    assert json.loads(recipe["nutrients_per_serving"])["beta_carotene_ug"] == (
        pytest.approx(9108.0)
    )

    assert recompute(path) == (0, 0)

    update = sqlite3.connect(path)
    update.execute(
        "UPDATE foods SET beta_carotene_ug = 3000 WHERE id = ?",
        (supplement,),
    )
    update.commit()
    update.close()
    assert recompute(path) == (1, 0)

    update = sqlite3.connect(path)
    update.execute("UPDATE foods SET beta_carotene_ug = 8000 WHERE id = ?", (food,))
    update.commit()
    update.close()
    assert recompute(path) == (1, 1)


def test_catalog_push_refreshes_snapshots_before_swap():
    script = (Path(__file__).parents[1] / "bin" / "db-push").read_text()

    migrate = script.index("scripts.migrate_personal_data")
    recompute_snapshots = script.index("scripts.recompute_nutrient_snapshots")
    swap = script.index("mv '$NT_DEPLOY_DB' '$NT_DEPLOY_DB.replaced-$STAMP'")
    assert migrate < recompute_snapshots < swap
    assert "PRAGMA foreign_key_check" in script
