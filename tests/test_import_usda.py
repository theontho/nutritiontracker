import json

import pytest

from app.database import get_connection
from scripts.import_usda import import_usda


def test_import_usda_skips_invalid_records(tmp_path):
    source_path = tmp_path / "foundation.json"
    db_path = tmp_path / "nutrition.db"
    source_path.write_text(
        json.dumps(
            {
                "FoundationFoods": [
                    None,
                    {"fdcId": 123, "description": "Test Food", "foodNutrients": []},
                ]
            }
        )
    )

    import_usda(str(source_path), str(db_path))

    conn = get_connection(db_path)
    food = conn.execute("SELECT name FROM foods WHERE source_code = '123'").fetchone()
    conn.close()
    assert food["name"] == "Test Food"


def test_import_usda_adds_missing_foods_from_csv(tmp_path):
    source_path = tmp_path / "foundation.json"
    csv_dir = tmp_path / "csv"
    db_path = tmp_path / "nutrition.db"
    csv_dir.mkdir()
    source_path.write_text(
        json.dumps(
            {
                "FoundationFoods": [
                    {"fdcId": 123, "description": "JSON Food", "foodNutrients": []},
                    None,
                ]
            }
        )
    )
    (csv_dir / "foundation_food.csv").write_text("fdc_id\n123\n456\n")
    (csv_dir / "food.csv").write_text(
        "fdc_id,data_type,description,food_category_id,publication_date\n"
        "123,foundation_food,JSON Food,,2026-04-30\n"
        "456,foundation_food,CSV Fallback Food,,2026-04-30\n"
    )
    (csv_dir / "food_nutrient.csv").write_text(
        "id,fdc_id,nutrient_id,amount\n1,456,2047,42.5\n2,456,1003,2.25\n"
    )

    import_usda(str(source_path), str(db_path), str(csv_dir))

    conn = get_connection(db_path)
    foods = conn.execute(
        "SELECT source_code, name, calories_kcal, protein_g "
        "FROM foods ORDER BY source_code"
    ).fetchall()
    conn.close()
    assert [tuple(food) for food in foods] == [
        ("123", "JSON Food", 0.0, 0.0),
        ("456", "CSV Fallback Food", 42.5, 2.25),
    ]


def test_import_usda_requires_complete_csv_export(tmp_path):
    source_path = tmp_path / "foundation.json"
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    source_path.write_text(json.dumps({"FoundationFoods": []}))

    with pytest.raises(FileNotFoundError, match="foundation_food.csv"):
        import_usda(str(source_path), str(tmp_path / "nutrition.db"), str(csv_dir))
