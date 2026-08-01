import json
import sqlite3

from app.database import init_schema
from scripts.migrate_personal_data import migrate_personal_data


def _connection(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _insert_food(conn, *, source, source_code, name):
    return conn.execute(
        """INSERT INTO foods (source, source_code, name, calories_kcal)
           VALUES (?, ?, ?, 100)""",
        (source, source_code, name),
    ).lastrowid


def test_migrates_personal_records_and_remaps_diary_foods(tmp_path):
    source_path = tmp_path / "source.db"
    target_path = tmp_path / "target.db"
    source = _connection(source_path)
    source_catalog_food = _insert_food(
        source, source="food_data_central", source_code="fdc-1", name="Catalog food"
    )
    source_custom_food = _insert_food(
        source, source="custom", source_code=None, name="Custom food"
    )
    for food_id, name in (
        (source_catalog_food, "Catalog food"),
        (source_custom_food, "Custom food"),
    ):
        source.execute(
            """INSERT INTO diary_entries
               (date, meal_type, food_id, food_snapshot, food_name, amount, unit, grams, nutrients_total)
               VALUES ('2026-08-01', 'breakfast', ?, ?, ?, 1, 'g', 100, ?)""",
            (
                food_id,
                json.dumps({"name": name, "calories_kcal": 100}),
                name,
                json.dumps({"calories_kcal": 100}),
            ),
        )
    source.execute(
        "INSERT INTO journal_entries (date, body) VALUES ('2026-08-01', 'Preserve me')"
    )
    source.commit()
    source.close()

    target = _connection(target_path)
    _insert_food(target, source="custom", source_code=None, name="Unrelated custom food")
    target_catalog_food = _insert_food(
        target, source="food_data_central", source_code="fdc-1", name="Catalog food"
    )
    target.commit()
    target.close()

    copied = migrate_personal_data(source_path, target_path)

    assert copied["diary_entries"] == 2
    assert copied["journal_entries"] == 1
    target = sqlite3.connect(target_path)
    target.row_factory = sqlite3.Row
    rows = target.execute(
        "SELECT food_id, food_name FROM diary_entries ORDER BY id"
    ).fetchall()
    custom_food = target.execute(
        "SELECT id FROM foods WHERE source = 'custom' AND name = 'Custom food'"
    ).fetchone()
    journal = target.execute("SELECT body FROM journal_entries").fetchone()
    target.close()

    assert rows[0]["food_id"] == target_catalog_food
    assert rows[1]["food_id"] == custom_food["id"]
    assert journal["body"] == "Preserve me"
