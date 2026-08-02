"""Bulk import Open Food Facts Parquet data into the nutrition tracker database.

Usage:
    python -m scripts.import_off_parquet <path_to_food_parquet> [db_path]
        [--country=en:united-states]
"""

import argparse
from pathlib import Path

from app.database import get_connection, init_schema
from app.providers.open_food_facts import normalize_off_food
from app.repositories.foods import FoodRepository


PARQUET_COLUMNS = (
    "code",
    "product_name",
    "brands",
    "countries_tags",
    "serving_quantity",
    "serving_size",
    "nutriments",
)


def _product_name(names: list[dict] | None) -> str:
    if not names:
        return ""
    preferred = ("main", "en")
    for language in preferred:
        for name in names:
            if name.get("lang") == language and name.get("text"):
                return name["text"].strip()
    return next((name["text"].strip() for name in names if name.get("text")), "")


def parquet_row_to_off_product(row: dict) -> dict:
    nutriments = {}
    for nutrient in row.get("nutriments") or []:
        name = nutrient.get("name")
        if not name:
            continue
        nutriments[f"{name}_100g"] = nutrient.get("100g")
        nutriments[f"{name}_unit"] = nutrient.get("unit")

    return {
        "code": row.get("code") or "",
        "product_name": _product_name(row.get("product_name")),
        "brands": row.get("brands"),
        "serving_quantity": row.get("serving_quantity"),
        "serving_size": row.get("serving_size"),
        "nutriments": nutriments,
    }


def import_off_parquet(
    file_path: str, db_path: str | None = None, country: str | None = None
) -> None:
    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError(
            "Parquet imports require the data-import extra: pip install -e '.[data-import]'"
        ) from error

    conn = get_connection(Path(db_path) if db_path else None)
    init_schema(conn)
    repo = FoodRepository(conn)
    repo.ensure_fts()

    imported = 0
    skipped = 0
    parquet_file = pq.ParquetFile(file_path)
    for batch in parquet_file.iter_batches(batch_size=10_000, columns=PARQUET_COLUMNS):
        for row in batch.to_pylist():
            if country and country not in (row.get("countries_tags") or []):
                skipped += 1
                continue
            raw = parquet_row_to_off_product(row)
            if not raw["product_name"]:
                skipped += 1
                continue
            repo.create_no_commit(**normalize_off_food(raw))
            imported += 1
            if imported % 5_000 == 0:
                conn.commit()
                print(f"  Imported {imported} foods (skipped {skipped})...")
    conn.commit()
    conn.close()
    print(f"Done. Imported {imported} Open Food Facts foods (skipped {skipped}).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet_path")
    parser.add_argument("db_path", nargs="?")
    parser.add_argument("--country")
    args = parser.parse_args()
    import_off_parquet(args.parquet_path, args.db_path, args.country)


if __name__ == "__main__":
    main()
