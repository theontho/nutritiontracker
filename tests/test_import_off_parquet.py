import pyarrow as pa
import pyarrow.parquet as pq

from app.database import get_connection
from scripts.import_off_parquet import import_off_parquet, parquet_row_to_off_product


def test_parquet_row_converts_nested_names_and_nutrients():
    product = parquet_row_to_off_product(
        {
            "code": "0889392000863",
            "product_name": [{"lang": "de", "text": "Celsius"}, {"lang": "en", "text": "Celsius Energy"}],
            "brands": "Celsius",
            "allergens_tags": ["en:milk"],
            "ingredients_analysis_tags": ["en:vegan"],
            "categories_tags": ["en:energy-drinks"],
            "labels_tags": ["en:gluten-free"],
            "countries_tags": ["en:united-states"],
            "ingredients_text": [{"lang": "en", "text": "Water, caffeine"}],
            "nutriscore_grade": "c",
            "nova_group": 4,
            "product_quantity": "355",
            "product_quantity_unit": "ml",
            "nutriments": [
                {"name": "caffeine", "100g": 0.056338, "unit": "g"},
                {"name": "vitamin-pp", "100g": 5.6338, "unit": "mg"},
            ],
        }
    )

    assert product["product_name"] == "Celsius Energy"
    assert product["nutriments"]["caffeine_100g"] == 0.056338
    assert product["nutriments"]["vitamin-pp_unit"] == "mg"
    assert product["allergens_tags"] == ["en:milk"]
    assert product["ingredients_text"] == "Water, caffeine"


def test_import_filters_country_and_normalizes_nutrients(tmp_path):
    source_path = tmp_path / "food.parquet"
    database_path = tmp_path / "nutrition.db"
    rows = [
        {
            "code": "0889392000863",
            "product_name": [{"lang": "en", "text": "Celsius Energy"}],
            "brands": "Celsius",
            "allergens_tags": ["en:milk"],
            "ingredients_analysis_tags": ["en:vegan"],
            "categories_tags": ["en:energy-drinks"],
            "labels_tags": ["en:gluten-free"],
            "countries_tags": ["en:united-states"],
            "ingredients_text": [{"lang": "en", "text": "Water, caffeine"}],
            "nutriscore_grade": "c",
            "nova_group": 4,
            "product_quantity": "355",
            "product_quantity_unit": "ml",
            "serving_quantity": "355",
            "serving_size": "355 ml",
            "nutriments": [
                {
                    "name": "caffeine",
                    "value": None,
                    "100g": 0.056338,
                    "serving": None,
                    "unit": "g",
                    "prepared_value": None,
                    "prepared_100g": None,
                    "prepared_serving": None,
                    "prepared_unit": None,
                },
                {
                    "name": "vitamin-pp",
                    "value": None,
                    "100g": 5.6338,
                    "serving": None,
                    "unit": "mg",
                    "prepared_value": None,
                    "prepared_100g": None,
                    "prepared_serving": None,
                    "prepared_unit": None,
                },
            ],
        },
        {
            "code": "0000000000000",
            "product_name": [{"lang": "en", "text": "German product"}],
            "brands": "Example",
            "allergens_tags": [],
            "ingredients_analysis_tags": [],
            "categories_tags": [],
            "labels_tags": [],
            "countries_tags": ["en:germany"],
            "ingredients_text": [],
            "nutriscore_grade": None,
            "nova_group": None,
            "product_quantity": None,
            "product_quantity_unit": None,
            "serving_quantity": None,
            "serving_size": None,
            "nutriments": [],
        },
    ]
    pq.write_table(pa.Table.from_pylist(rows), source_path)

    import_off_parquet(
        str(source_path), str(database_path), country="en:united-states"
    )

    conn = get_connection(database_path)
    foods = conn.execute(
        """SELECT name, caffeine_mg, niacin_mg, ingredients_text, allergens_tags,
                  dietary_tags, nutriscore_grade, nova_group, product_quantity
           FROM foods ORDER BY id"""
    ).fetchall()
    conn.close()
    assert [tuple(food) for food in foods] == [
        (
            "Celsius Energy", 56.338, 5.6338, "Water, caffeine", '["en:milk"]',
            '["en:vegan"]', "c", 4, 355.0,
        )
    ]
