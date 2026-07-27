import json

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

    from app.database import get_connection

    conn = get_connection(db_path)
    food = conn.execute("SELECT name FROM foods WHERE source_code = '123'").fetchone()
    conn.close()
    assert food["name"] == "Test Food"
