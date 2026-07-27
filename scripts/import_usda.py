"""
Bulk import USDA FoodData Central data into the nutrition tracker database.

Usage:
    python -m scripts.import_usda <path_to_usda_json> [db_path] [--csv-dir=DIR]

Download the "FoodData Central Foundation Foods" or "SR Legacy" JSON and,
optionally, the matching Foundation Foods CSV archive from:
    https://fdc.nal.usda.gov/download-datasets
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.providers.food_data_central import (
    NUTRIENT_MAP,
    NUTRIENT_PRIORITY,
    normalize_usda_food,
)
from app.repositories.foods import FoodRepository


def _load_csv_fallback(csv_dir: Path, imported_ids: set[str]) -> list[dict]:
    required_files = ("food.csv", "foundation_food.csv", "food_nutrient.csv")
    missing_files = [name for name in required_files if not (csv_dir / name).is_file()]
    if missing_files:
        names = ", ".join(missing_files)
        raise FileNotFoundError(
            f"USDA CSV directory is missing required files: {names}"
        )

    with (csv_dir / "foundation_food.csv").open(
        newline="", encoding="utf-8-sig"
    ) as file:
        fallback_ids = {row["fdc_id"] for row in csv.DictReader(file)} - imported_ids

    foods: dict[str, dict] = {}
    with (csv_dir / "food.csv").open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            fdc_id = row["fdc_id"]
            if fdc_id in fallback_ids:
                foods[fdc_id] = {
                    "source": "food_data_central",
                    "source_code": fdc_id,
                    "name": row["description"],
                    **{field: 0 for field in NUTRIENT_MAP.values()},
                }

    missing_foods = fallback_ids - foods.keys()
    if missing_foods:
        ids = ", ".join(sorted(missing_foods))
        raise ValueError(f"USDA food.csv is missing fallback food IDs: {ids}")

    priorities: dict[str, dict[str, int]] = {fdc_id: {} for fdc_id in foods}
    with (csv_dir / "food_nutrient.csv").open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            food = foods.get(row["fdc_id"])
            if food is None:
                continue
            nutrient_id = int(row["nutrient_id"])
            field = NUTRIENT_MAP.get(nutrient_id)
            priority = NUTRIENT_PRIORITY.get(nutrient_id, 0)
            if (
                field
                and row["amount"]
                and priority >= priorities[row["fdc_id"]].get(field, -1)
            ):
                food[field] = float(row["amount"])
                priorities[row["fdc_id"]][field] = priority

    return list(foods.values())


def import_usda(file_path: str, db_path: str | None = None, csv_dir: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = FoodRepository(conn)
    repo.ensure_fts()

    with open(file_path) as f:
        data = json.load(f)

    foods = (
        data
        if isinstance(data, list)
        else data.get("FoundationFoods", data.get("SRLegacyFoods", []))
    )
    count = 0
    skipped = 0
    imported_ids = set()
    batch_size = 1000
    for raw in foods:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        normalized = normalize_usda_food(raw)
        repo.create_no_commit(**normalized)
        imported_ids.add(normalized["source_code"])
        count += 1
        if count % batch_size == 0:
            conn.commit()
            print(f"  Imported {count} foods...")
    conn.commit()

    fallback_count = 0
    if csv_dir:
        fallback_foods = _load_csv_fallback(Path(csv_dir), imported_ids)
        for food in fallback_foods:
            repo.create_no_commit(**food)
            fallback_count += 1
            if fallback_count % batch_size == 0:
                conn.commit()
                print(f"  Imported {fallback_count} CSV fallback foods...")
        conn.commit()

    print(
        f"Done. Imported {count} USDA foods from JSON "
        f"(skipped {skipped} invalid records); "
        f"added {fallback_count} CSV fallback foods."
    )
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path")
    parser.add_argument("db_path", nargs="?")
    parser.add_argument("--csv-dir")
    args = parser.parse_args()
    import_usda(args.json_path, args.db_path, args.csv_dir)
