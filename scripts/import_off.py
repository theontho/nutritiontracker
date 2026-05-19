"""
Bulk import OpenFoodFacts data into the nutrition tracker database.

Accepts plain JSONL or gzip-compressed JSONL (.jsonl.gz / .gz).
Use --country to restrict to products sold in a specific country tag
(e.g. en:united-states). Without --country all products are imported.

Usage:
    python -m scripts.import_off <path_to_off_jsonl_or_gz> [db_path] [--country=en:united-states]

Download the data dump from:
    https://world.openfoodfacts.org/data
    (Use the JSONL export — openfoodfacts-products.jsonl.gz, ~12 GB)
"""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_connection, init_schema
from app.repositories.foods import FoodRepository
from app.providers.open_food_facts import normalize_off_food


def _open_file(file_path: str):
    if file_path.endswith(".gz"):
        return gzip.open(file_path, "rt", encoding="utf-8", errors="replace")
    return open(file_path, encoding="utf-8", errors="replace")


def import_off(file_path: str, db_path: str | None = None, country: str | None = None):
    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = FoodRepository(conn)
    repo.ensure_fts()

    count = 0
    skipped = 0
    with _open_file(file_path) as f:
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

            if country:
                tags = raw.get("countries_tags", [])
                if country not in tags:
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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a.split("=", 1)[0].lstrip("-"): a.split("=", 1)[1]
             for a in sys.argv[1:] if a.startswith("--") and "=" in a}

    if not args:
        print("Usage: python -m scripts.import_off <path_to_off_jsonl_or_gz> [db_path] [--country=en:united-states]")
        sys.exit(1)

    import_off(
        args[0],
        args[1] if len(args) > 1 else None,
        country=flags.get("country"),
    )
