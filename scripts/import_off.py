"""
Bulk import OpenFoodFacts data into the nutrition tracker database.

Usage:
    python -m scripts.import_off <path_to_off_jsonl>

Download the data dump from:
    https://world.openfoodfacts.org/data
    (Use the JSONL export)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.repositories.foods import FoodRepository
from app.providers.open_food_facts import normalize_off_food


def import_off(file_path: str, db_path: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = FoodRepository(conn)
    repo.ensure_fts()

    count = 0
    skipped = 0
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            name = raw.get("product_name", "").strip()
            if not name:
                skipped += 1
                continue

            normalized = normalize_off_food(raw)
            repo.create_no_commit(**normalized)
            count += 1
            if count % 5000 == 0:
                conn.commit()
                print(f"  Imported {count} foods (skipped {skipped})...")
    conn.commit()

    print(f"Done. Imported {count} OpenFoodFacts foods (skipped {skipped}).")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_off <path_to_off_jsonl> [db_path]")
        sys.exit(1)
    import_off(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
