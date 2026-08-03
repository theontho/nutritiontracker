import json
import sqlite3

import pytest

from app.database import init_schema
from scripts.merge_food_nutrients import merge_missing_nutrients


def _database(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    init_schema(connection)
    return connection


def _food(connection, *, name, **nutrients):
    columns = ["source", "name", *nutrients]
    values = ["custom", name, *nutrients.values()]
    placeholders = ", ".join("?" for _ in columns)
    return connection.execute(
        f"INSERT INTO foods ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    ).lastrowid


def _entry(connection, food_id, *, grams=220.0):
    return connection.execute(
        """
        INSERT INTO diary_entries
            (date, meal_type, food_id, food_snapshot, food_name, amount, unit,
             grams, nutrients_total)
        VALUES ('2026-08-03', 'snack', ?, '{}', 'Carrots', ?, 'g', ?, '{}')
        """,
        (food_id, grams, grams),
    ).lastrowid


def test_merges_only_missing_nutrients_and_refreshes_diary(tmp_path):
    path = tmp_path / "nutrition.db"
    connection = _database(path)
    target = _food(
        connection,
        name="Enriched carrots",
        calories_kcal=41.0,
        vitamin_a_ug=835.0,
        biotin_ug=5.0,
    )
    reference = _food(
        connection,
        name="Carrots, raw",
        calories_kcal=41.0,
        vitamin_a_ug=835.0,
        beta_carotene_ug=8280.0,
        alpha_carotene_ug=3480.0,
    )
    entry = _entry(connection, target)
    connection.commit()
    connection.close()

    result = merge_missing_nutrients(path, target, reference)

    assert result["merged_fields"] == ("beta_carotene_ug", "alpha_carotene_ug")
    assert result["diary_entries_refreshed"] == 1
    check = sqlite3.connect(path)
    check.row_factory = sqlite3.Row
    food = check.execute("SELECT * FROM foods WHERE id = ?", (target,)).fetchone()
    diary = check.execute(
        "SELECT food_name, food_snapshot, nutrients_total FROM diary_entries WHERE id = ?",
        (entry,),
    ).fetchone()
    check.close()
    assert food["biotin_ug"] == 5.0
    assert food["beta_carotene_ug"] == 8280.0
    assert diary["food_name"] == "Enriched carrots"
    assert json.loads(diary["food_snapshot"])["beta_carotene_ug"] == 8280.0
    assert json.loads(diary["nutrients_total"])["beta_carotene_ug"] == pytest.approx(
        18_216.0
    )


def test_rejects_foods_with_conflicting_overlapping_nutrients(tmp_path):
    path = tmp_path / "nutrition.db"
    connection = _database(path)
    target = _food(connection, name="Target", calories_kcal=41.0)
    reference = _food(
        connection,
        name="Different food",
        calories_kcal=44.0,
        beta_carotene_ug=7340.0,
    )
    entry = _entry(connection, target)
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="calories_kcal"):
        merge_missing_nutrients(path, target, reference)

    check = sqlite3.connect(path)
    beta_carotene = check.execute(
        "SELECT beta_carotene_ug FROM foods WHERE id = ?", (target,)
    ).fetchone()[0]
    snapshot = check.execute(
        "SELECT food_snapshot FROM diary_entries WHERE id = ?", (entry,)
    ).fetchone()[0]
    check.close()
    assert beta_carotene is None
    assert snapshot == "{}"
