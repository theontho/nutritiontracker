"""
Bulk import USDA FoodData Central data into the nutrition tracker database.

Usage:
    python -m scripts.import_usda <path_to_usda_json>

Download the "FoodData Central Foundation Foods" or "SR Legacy" JSON from:
    https://fdc.nal.usda.gov/download-datasets
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.repositories.foods import FoodRepository
from app.providers.food_data_central import normalize_usda_food


def import_usda(file_path: str, db_path: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = FoodRepository(conn)
    repo.ensure_fts()

    with open(file_path) as f:
        data = json.load(f)

    foods = data if isinstance(data, list) else data.get("FoundationFoods", data.get("SRLegacyFoods", []))
    count = 0
    batch_size = 1000
    for raw in foods:
        normalized = normalize_usda_food(raw)
        repo.create_no_commit(**normalized)
        count += 1
        if count % batch_size == 0:
            conn.commit()
            print(f"  Imported {count} foods...")
    conn.commit()

    print(f"Done. Imported {count} USDA foods.")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_usda <path_to_usda_json> [db_path]")
        sys.exit(1)
    import_usda(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
