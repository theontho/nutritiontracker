import json
import sqlite3

import pytest

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
    event_type_id = source.execute(
        "INSERT INTO event_types (name, unit) VALUES ('Walking', 'minutes')"
    ).lastrowid
    source.execute(
        """INSERT INTO events (event_type_id, date, at, value, unit)
           VALUES (?, '2026-08-01', '08:30', 20, 'minutes')""",
        (event_type_id,),
    )
    source.commit()
    source.close()

    target = _connection(target_path)
    _insert_food(
        target, source="custom", source_code=None, name="Unrelated custom food"
    )
    target_catalog_food = _insert_food(
        target, source="food_data_central", source_code="fdc-1", name="Catalog food"
    )
    target.commit()
    target.close()

    copied = migrate_personal_data(source_path, target_path)

    assert copied["diary_entries"] == 2
    assert copied["journal_entries"] == 1
    assert copied["event_types"] == 1
    assert copied["events"] == 1
    target = sqlite3.connect(target_path)
    target.row_factory = sqlite3.Row
    rows = target.execute(
        "SELECT food_id, food_name FROM diary_entries ORDER BY id"
    ).fetchall()
    custom_food = target.execute(
        "SELECT id FROM foods WHERE source = 'custom' AND name = 'Custom food'"
    ).fetchone()
    journal = target.execute("SELECT body FROM journal_entries").fetchone()
    event = target.execute(
        """SELECT et.name, e.value, e.unit
           FROM events e JOIN event_types et ON et.id = e.event_type_id"""
    ).fetchone()
    target.close()

    assert rows[0]["food_id"] == target_catalog_food
    assert rows[1]["food_id"] == custom_food["id"]
    assert journal["body"] == "Preserve me"
    assert dict(event) == {"name": "Walking", "value": 20.0, "unit": "minutes"}


def test_migrates_accounts_and_preserves_their_ids(tmp_path):
    """Diary rows and owned foods point at users by id, so ids must survive.

    The target is freshly built and already carries a seeded default account,
    so the incoming ids collide and the source has to win.
    """
    source_path = tmp_path / "source.db"
    target_path = tmp_path / "target.db"
    source = _connection(source_path)
    target = _connection(target_path)

    source.execute("DELETE FROM users")
    source.execute(
        "INSERT INTO users (id, name, token_hash) VALUES (1, 'Primary', NULL)"
    )
    source.execute(
        "INSERT INTO users (id, name, token_hash) VALUES (2, 'Second', 'hashed')"
    )
    food_id = _insert_food(
        source, source="food_data_central", source_code="fdc-1", name="Catalog food"
    )
    source.execute(
        """INSERT INTO diary_entries
           (user_id, date, meal_type, food_id, food_snapshot, food_name, amount, unit, grams, nutrients_total)
           VALUES (2, '2026-08-01', 'breakfast', ?, ?, 'Catalog food', 1, 'g', 100, ?)""",
        (
            food_id,
            json.dumps({"name": "Catalog food"}),
            json.dumps({"calories_kcal": 100}),
        ),
    )
    source.commit()

    _insert_food(
        target, source="food_data_central", source_code="fdc-1", name="Catalog food"
    )
    target.commit()
    target.close()
    source.close()

    copied = migrate_personal_data(source_path, target_path)
    assert copied["users"] == 2

    check = sqlite3.connect(target_path)
    check.row_factory = sqlite3.Row
    users = {
        row["id"]: row["name"] for row in check.execute("SELECT id, name FROM users")
    }
    assert users[1] == "Primary"
    assert users[2] == "Second"

    entry = check.execute("SELECT user_id FROM diary_entries").fetchone()
    assert entry["user_id"] == 2
    check.close()


def test_legacy_fdc_food_prefers_exact_modern_usda_identity(tmp_path):
    source_path = tmp_path / "source.db"
    target_path = tmp_path / "target.db"
    source = _connection(source_path)
    legacy_food = _insert_food(
        source,
        source="food_data_central",
        source_code="170393",
        name="Carrots, raw",
    )
    source.execute(
        """INSERT INTO diary_entries
           (date, meal_type, food_id, food_snapshot, food_name, amount, unit, grams, nutrients_total)
           VALUES ('2026-08-01', 'breakfast', ?, '{}', 'Carrots, raw', 100, 'g', 100, '{}')""",
        (legacy_food,),
    )
    source.commit()
    source.close()

    target = _connection(target_path)
    _insert_food(
        target,
        source="food_data_central",
        source_code="170393",
        name="Legacy carrots",
    )
    modern_food = _insert_food(
        target,
        source="usda_sr_legacy",
        source_code="170393",
        name="Carrots, raw",
    )
    target.commit()
    target.close()

    migrate_personal_data(source_path, target_path)

    check = sqlite3.connect(target_path)
    remapped_food = check.execute("SELECT food_id FROM diary_entries").fetchone()[0]
    check.close()
    assert remapped_food == modern_food


def test_legacy_fdc_food_rejects_ambiguous_modern_matches(tmp_path):
    source_path = tmp_path / "source.db"
    target_path = tmp_path / "target.db"
    source = _connection(source_path)
    legacy_food = _insert_food(
        source,
        source="food_data_central",
        source_code="duplicate-id",
        name="Ambiguous food",
    )
    source.execute(
        """INSERT INTO diary_entries
           (date, meal_type, food_id, food_snapshot, food_name, amount, unit, grams, nutrients_total)
           VALUES ('2026-08-01', 'breakfast', ?, '{}', 'Ambiguous food', 100, 'g', 100, '{}')""",
        (legacy_food,),
    )
    source.commit()
    source.close()

    target = _connection(target_path)
    _insert_food(
        target,
        source="usda_foundation",
        source_code="duplicate-id",
        name="Foundation match",
    )
    _insert_food(
        target,
        source="usda_sr_legacy",
        source_code="duplicate-id",
        name="SR match",
    )
    target.commit()
    target.close()

    with pytest.raises(ValueError, match="Ambiguous modern USDA match"):
        migrate_personal_data(source_path, target_path)
