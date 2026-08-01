"""Copy personal tracker data into a rebuilt food database.

Usage:
    python -m scripts.migrate_personal_data <source_db> <target_db>

The target database must already contain the rebuilt food catalog and have no
personal records. Diary food references are resolved by source/source_code;
custom or otherwise unmatched foods are copied first and remapped.
"""

import argparse
import sqlite3
from pathlib import Path


PERSONAL_TABLES = (
    "diary_entries",
    "recipes",
    "weight_entries",
    "journal_entries",
    "step_observations",
    "daily_activity",
    "kitchen_inventory_items",
    "favorite_meals",
    "favorite_meal_ingredients",
    "shopping_list_items",
)


def _connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))


def _insert_row(
    target: sqlite3.Connection, table: str, row: sqlite3.Row, columns: tuple[str, ...],
    overrides: dict[str, object] | None = None,
) -> int:
    values = dict(row)
    if overrides:
        values.update(overrides)
    included = [column for column in columns if column in values]
    placeholders = ", ".join("?" for _ in included)
    target.execute(
        f"INSERT INTO {table} ({', '.join(included)}) VALUES ({placeholders})",
        [values[column] for column in included],
    )
    return target.execute("SELECT last_insert_rowid()").fetchone()[0]


def _find_or_copy_food(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    source_food_id: int,
    food_columns: tuple[str, ...],
    food_id_map: dict[int, int],
) -> int:
    if source_food_id in food_id_map:
        return food_id_map[source_food_id]

    food = source.execute("SELECT * FROM foods WHERE id = ?", (source_food_id,)).fetchone()
    if food is None:
        raise ValueError(f"Diary entry references missing source food {source_food_id}")

    source_code = food["source_code"]
    if source_code is not None:
        existing = target.execute(
            "SELECT id FROM foods WHERE source = ? AND source_code = ?",
            (food["source"], source_code),
        ).fetchone()
        if existing:
            food_id_map[source_food_id] = existing["id"]
            return existing["id"]

    target_food_columns = tuple(column for column in food_columns if column != "id")
    new_id = _insert_row(target, "foods", food, target_food_columns)
    food_id_map[source_food_id] = new_id
    return new_id


def migrate_personal_data(source_path: Path, target_path: Path) -> dict[str, int]:
    source = _connect_readonly(source_path)
    target = sqlite3.connect(target_path)
    target.row_factory = sqlite3.Row
    target.execute("PRAGMA foreign_keys=ON")

    try:
        for table in PERSONAL_TABLES:
            count = target.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if count:
                raise ValueError(f"Target table {table} is not empty")

        source_food_columns = _columns(source, "foods")
        target_food_columns = _columns(target, "foods")
        common_food_columns = tuple(
            column for column in source_food_columns if column in target_food_columns
        )
        food_id_map: dict[int, int] = {}

        for food in source.execute("SELECT id FROM foods WHERE source = 'custom' ORDER BY id"):
            _find_or_copy_food(
                source, target, food["id"], common_food_columns, food_id_map
            )

        for entry in source.execute("SELECT DISTINCT food_id FROM diary_entries"):
            _find_or_copy_food(
                source, target, entry["food_id"], common_food_columns, food_id_map
            )

        copied: dict[str, int] = {}
        for table in PERSONAL_TABLES:
            source_columns = _columns(source, table)
            target_columns = _columns(target, table)
            common_columns = tuple(
                column for column in source_columns if column in target_columns
            )
            count = 0
            for row in source.execute(f"SELECT * FROM {table} ORDER BY id"):
                overrides = None
                if table == "diary_entries":
                    overrides = {"food_id": food_id_map[row["food_id"]]}
                _insert_row(target, table, row, common_columns, overrides)
                count += 1
            copied[table] = count

        target.commit()
        return copied
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_db", type=Path)
    parser.add_argument("target_db", type=Path)
    args = parser.parse_args()

    copied = migrate_personal_data(args.source_db, args.target_db)
    print("Migrated personal records:")
    for table, count in copied.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
