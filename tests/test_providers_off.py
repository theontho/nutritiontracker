from app.providers.open_food_facts import normalize_off_food


def test_normalize_off_food():
    raw = {
        "code": "3017620422003",
        "product_name": "Nutella",
        "brands": "Ferrero",
        "image_url": "https://example.com/nutella.jpg",
        "serving_quantity": "15",
        "serving_size": "15 g",
        "nutriments": {
            "energy-kcal_100g": 539,
            "proteins_100g": 6.3,
            "carbohydrates_100g": 57.5,
            "fat_100g": 30.9,
            "sugars_100g": 56.3,
            "saturated-fat_100g": 10.6,
            "fiber_100g": 3.4,
            "sodium_100g": 0.041,
        },
    }
    food = normalize_off_food(raw)
    assert food["name"] == "Nutella"
    assert food["brand"] == "Ferrero"
    assert food["source"] == "open_food_facts"
    assert food["barcode"] == "3017620422003"
    assert food["calories_kcal"] == 539
    assert food["protein_g"] == 6.3
    assert food["sodium_mg"] == 41  # 0.041g * 1000


def test_normalize_handles_missing_fields():
    raw = {
        "code": "000",
        "product_name": "Blank",
        "nutriments": {},
    }
    food = normalize_off_food(raw)
    assert food["calories_kcal"] == 0
